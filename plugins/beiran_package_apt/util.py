import os
import re
from io import StringIO
import requests
import gzip
import platform
import tarfile
import shutil
from beiran.lib import async_req
from beirand.lib import run_command

SOURCE_LIST_PATHS = os.getenv(
    'SOURCE_LIST_PATHS', [
        '/etc/apt/sources.list',
        '/etc/apt/sources.d/*'
    ]
)
DEB_CACHE_DIR = "/var/lib/beiran/apt"

class AptUtil:
    """
    Some useful apt related methods which download, parse and process
    apt files and deb packages.
    """

    @staticmethod
    def find_source_files():
        """
        Walks through SOURCE_LIST_PATHS and gathers sources files.

        Returns:
            list: of found source files in SOURCE_LIST_PATHS

        """
        files = []
        for path in SOURCE_LIST_PATHS:
            if os.path.isdir(path):
                for file_path in os.listdir(path):
                    files.append(file_path)
                    continue
            if os.path.isfile(path):
                files.append(path)

        return files

    @staticmethod
    def read_source_list_file(filepath):
        """
        Read source list entries.

        Args:
            filepath (str): file path of source list file

        Returns:
            list: list of entries from source list file

        """
        sources = []
        with open(filepath, 'r') as file_handler:
            for line in file_handler:
                line = line.strip()
                if line and not line.startswith("#"):  # skip blank and documentation lines
                    line = line.split("#")[0]  # get rid of possible documentation at the end of line
                    # replace all multi whitespaces with single space
                    sources.append(re.sub("\s+", " ", line))
        return sources

    @staticmethod
    def parse_source_list_entry(source_entry):
        """
        Parse a source list entry.

        Args:
            source_entry (str): a source entry string
                'deb http://deb.debian.org/debian stretch main'


        Returns:
            tuple: integral parts of a source entry
                ('bin', 'http://de.debian.org/debian', 'jessie',  [main, contrib])

        Examples:

            Source entries such below::

                    'deb http://deb.debian.org/debian stretch main',
                    'deb-src http://deb.debian.org/debian stretch main',
                    'deb http://security.debian.org/debian-security stretch/updates main',
                    'deb-src http://security.debian.org/debian-security stretch/updates main',

            returns the tuples respectively as belows::

                    ('bin', 'http://deb.debian.org/debian', ['stretch', 'main'])
                    ('src', 'http://deb.debian.org/debian', ['stretch', 'main'])
                    ('bin', 'http://security.debian.org/debian-security', ['stretch/updates', 'main'])
                    ('src', 'http://security.debian.org/debian-security', ['stretch/updates', 'main'])

        """

        parsed_sources = []

        entry = re.sub("\s+", " ", source_entry.strip())
        parts = entry.split(" ")

        return (
            'bin' if parts[0] == "deb" else 'src',
            parts[1],
            parts[2],
            parts[3:]
        )

    @staticmethod
    def get_release_file(repo_url, dist):
        """
        Downloads Release file for distribution from specified repo url.

        Args:
            repo_url (str): apt repository base url, (http://ftp.debian.org/debian)
            dist (str): distribution (lenny, squeeze)

        Returns:
            file: file like object with content of response text of http request.

        """
        release_file_url = "{}/dists/{}/Release".format(repo_url, dist)
        response = requests.get(release_file_url)
        if response.status_code == 200:
            release_file = StringIO()
            release_file.write(response.text)
            return release_file
        else:
            raise ConnectionError()

    @staticmethod
    def parse_release_file(repo_url, dist, components, release_file):
        """
        Parses a Release file and extracts Packages.gz urls for a component.

        Args:
            repo_url (str): apt repository base url, (http://ftp.debian.org/debian)
            dist (str): distribution (lenny, squeeze)
            components (list): of components (main, contrib)
            release_file (file): file like object

        Returns:
            set: of Packages.gz files, it is set rather than list, because of not to have
            duplicate links.

        """
        packages_gz_paths = set()
        release_file.seek(0)

        component_arch_packages_path = r"({})/binary-{}/Packages.gz".format(
            "|".join(components),
            AptUtil.deb_architecture()
        )

        for line in release_file.readlines():
            line = line.strip()
            if re.search(component_arch_packages_path, line):
                packages_gz_paths.add(
                    "{}/dists/{}/{}".format(repo_url, dist, line.split(" ")[-1])
                )

        return packages_gz_paths

    @staticmethod
    def parse_packages_gz(packages_gz_path):
        """
        Download and parse a Packages.gz file, and returns package list.

        Args:
            repo_url (str): apt repository base url, (http://ftp.debian.org/debian)
            dist (str): distribution (lenny, squeeze)
            packages_gz_path:

        Returns:
            generator: of Packages

        """
        resp = requests.get(packages_gz_path)
        for package in gzip.decompress(resp.content).decode().split('\n\n'):
            if package:
                yield package

    @staticmethod
    def package_data_to_dict(package_data):
        """
        Create a python dict object from package data extracted from Packages.gz file.

        Args:
            package_data (str): multiline key value string.

        Returns:
            dict: stripped and lowered keys with corresponding string values.

        """
        package = dict()
        lines = package_data.split("\n")
        for line in lines:
            if line:
                [key, *val] = line.split(":")
                key = key.strip().lower()
                if key in ['package', 'version', 'filename', 'size', 'md5sum', 'sha256']:
                    package.update({key: ":".join(val).strip()})

        if "" in package and package[""] == "":
            return None

        return package

    @staticmethod
    def deb_architecture():
        machine = platform.machine()

        if machine == "x86_64":
            return "amd64"

        if re.match(r'^i[2-6]86$', machine):
            return "i386"

        raise NotImplementedError(
            """Your architecture %s, isn't one of those that 
            Beiran already supports: x86_64 and i386.
            
            You should consider disable apt plugin on this node.""", machine
        )



    @staticmethod
    def extract_deb_file(file_path):
        """

        Args:
            file_path (str): deb file path

        Returns:
            str: extracted directory path

        """

        extract_dir_path = "{}_extract".format(file_path)
        os.mkdir(extract_dir_path)
        _ = run_command(command = ["ar", "-x", file_path], cwd=extract_dir_path)
        return extract_dir_path

    @staticmethod
    async def download_deb_file(remote_uri):

        """
        Get deb file which does not exist locally, from `remote_url`.

        Args:
            remote_uri (str): remote address of deb file

        Returns:
            str: downloaded file path

        """

        file_name = remote_uri.split('/')[-1]
        file_path = "{}/{}".format(DEB_CACHE_DIR, file_name)

        resp, file_path = await async_req(url=remote_uri, file_path=file_path)
        if resp.status == 200:
            return file_path
        else:
            return None


    @staticmethod
    def get_data_from_deb_file(file_path):
        """
        Extracts and grabs package data from deb archive, and cleans remaining.

        Args:
            file_path:

        Returns:
            tuple(str, dict): deb file path, and dict of package data

        """

        extract_dir = AptUtil.extract_deb_file(file_path)
        control_tar_file_path = "{}/{}".format(extract_dir, "control.tar.gz")
        control_arhive = tarfile.TarFile(control_tar_file_path)
        control = control_arhive.extractfile('control')
        package_data = AptUtil.package_data_to_dict(control.read())
        shutil.rmtree(extract_dir, ignore_errors=True)  # clean extracted deb files
        return file_path, package_data

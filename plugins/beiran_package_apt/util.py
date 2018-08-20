import os
import re
from io import StringIO
import requests
import gzip
import platform
import tarfile
import uuid
from beirand.lib import run_command

SOURCE_LIST_PATHS = os.getenv(
    'SOURCE_LIST_PATHS', [
        '/etc/apt/sources.list',
        '/etc/apt/sources.d/*'
    ]
)

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

        arch_packages_path = "binary-{}/Packages.gz".format(AptUtil.deb_architecture())

        for line in release_file.readlines():
            if line.strip().endswith(arch_packages_path):
                packages_path = line.strip().split(" ")[-1]
                if packages_path.startswith(tuple(components)):
                    packages_gz_paths.add("{}/dists/{}/{}".format(repo_url, dist, packages_path))

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


#
#     @staticmethod
#     def extract_deb_file(file_path):
#         """
#
#         Args:
#             file_path (str):
#
#         Returns:
#
#         """
#
#         try:
#             dir_path = os.path.dirname(file_path)
#             uuid.uuid4().hex
#             _ = run_command(["ar", "-x", file_path])
#             control_tar_file = tarfile.TarFile("/".join([dir_path, 'control.tar.gz']))
#             control_file = control_tar_file.extractfile('control')
#             for line in control_file.readlines():
#                 if line:
#
#
#         except:
#             return None
#
#
#
# z = zipfile.ZipFile('a.deb')
#
# print(z.infolist())

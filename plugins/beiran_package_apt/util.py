import os
import re
from io import StringIO
import requests
import gzip

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
            list: of Packages.gz files

        """
        packages_gz_paths = list()
        release_file.seek(0)
        for line in release_file.readlines():
            if line.strip().endswith('Packages.gz'):
                packages_path = line.strip().split(" ")[-1]
                if packages_path.startswith(tuple(components)):
                    packages_gz_paths.append("{}/dists/{}/{}".format(repo_url, dist, packages_path))

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
                package.update({key.strip().lower(): ":".join(val).strip()})

        if "" in package and package[""] == "":
            return None

        return package

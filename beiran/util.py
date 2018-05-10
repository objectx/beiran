"""
Utilities for beiran project
"""

import sys
import tarfile


class Unbuffered(object):
    """
    Unbuffered stream write class
    """
    def __init__(self, stream):
        """
        Initialization unbuffered with stream.
        Args:
            stream: any stream to write unbuffered
        """
        self.stream = stream

    def write(self, data):
        """
        Write data to stream and flush
        Args:
            data: data to write
        """
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, lines):
        """ Write as lines

        Args:
            lines (Array): array of data

        """
        self.stream.writelines(lines)
        self.stream.flush()

    def __getattr__(self, attr):
        """
        Get a named attribute from an object
        Returns:
            value:
        """
        return getattr(self.stream, attr)


def eprint(*args, **kwargs):
    """
    Printing errors
    Args:
        *args:
        **kwargs:
    """
    print(*args, file=sys.stderr, **kwargs)


def exit_print(exit_code, *args, **kwargs):
    """
    Printing exit code
    Args:
        exit_code:
        *args:
        **kwargs:
    """
    print(*args, file=sys.stderr, **kwargs)
    sys.exit(exit_code)


def create_tar_archive(dir_path, output_file_path):
    """
    create a tar archive from given path

    Args:
        output_file_path: directory path to be saved!
        dir_path (string): directory path to be tarred!

    Returns:


    """
    with tarfile.open(output_file_path, "w") as tar:
        tar.add(dir_path, arcname='.')



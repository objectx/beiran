#!/bin/env python
"""command line client for managing beiran daemon"""

import os
import sys
import logging
import click

from beiran.util import Unbuffered
from beiran.version import get_version
from beiran.log import build_logger
from beiran.cli import pass_context

from .util import AptUtil as util
from .models import AptPackage

LOG_LEVEL = logging.getLevelName(os.getenv('LOG_LEVEL', 'WARNING'))
logger = build_logger(None, LOG_LEVEL) # pylint: disable=invalid-name

VERSION = get_version('short', 'library')

sys.stdout = Unbuffered(sys.stdout)

@click.group()
def cli():
    """cli command set of node itself."""
    pass


@cli.command("clean")
@click.pass_obj
@click.argument('uuid', required=False)
@pass_context
def clean(ctx):
    ...


@cli.command("update")
@click.pass_obj
@click.argument('uuid', required=False)
@pass_context
def update(ctx):
    """Update local package database

    Reads sources files and downloads Packages files and update local database by parsing them.

    """
    sources_entries = []
    source_files = util.find_source_files()
    for s_file in source_files:
        sources_entries.extend(util.read_source_list_file(s_file))

    for entry in sources_entries:
        print("Processing: %s", entry)
        bin, url, dist, components = util.parse_source_list_entry(entry)
        if bin == 'src':
            continue

        release_file = util.get_release_file(url, dist)
        packages_gzs = util.parse_release_file(url, dist, components, release_file)
        for packages_gz in packages_gzs:
            for package in util.parse_packages_gz(packages_gz):
                p_dict = util.package_data_to_dict(package)
                pkg = AptPackage.from_dict(p_dict)
                AptPackage.add_or_update(pkg)

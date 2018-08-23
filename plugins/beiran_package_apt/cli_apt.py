#!/bin/env python
"""command line client for managing beiran daemon"""

import os
import sys
import logging
import click
from peewee import Proxy
from peewee import SqliteDatabase

from beiran.util import Unbuffered
from beiran.version import get_version
from beiran.log import build_logger
from beiran.cli import pass_context
from beiran import defaults

from .util import AptUtil as util
from .models import AptPackage, PackageLocation

LOG_LEVEL = logging.getLevelName(os.getenv('LOG_LEVEL', 'WARNING'))
logger = build_logger(None, LOG_LEVEL) # pylint: disable=invalid-name

peewee_loggler = logging.getLogger('peewee')
peewee_loggler.setLevel("ERROR")  # suppress peewee query logs.

VERSION = get_version('short', 'library')

sys.stdout = Unbuffered(sys.stdout)

DATA_FOLDER = os.getenv("DATA_FOLDER_PATH", defaults.DATA_FOLDER)
beiran_db_path = os.getenv("BEIRAN_DB_PATH", '{}/beiran.db'.format(DATA_FOLDER))
db_file_exists = os.path.exists(beiran_db_path)
DB_PROXY = Proxy()
# init database object
database = SqliteDatabase(beiran_db_path)
DB_PROXY.initialize(database)

# bind database to model
AptPackage.bind(database)
PackageLocation.bind(database)

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
        print("Processing: %s. It may take too long...", entry)
        bin, url, dist, components = util.parse_source_list_entry(entry)
        if bin == 'src':
            continue

        release_file = util.get_release_file(url, dist)
        packages_gzs = util.parse_release_file(url, dist, components, release_file)

        for packages_gz in packages_gzs:
            # we should use bulk insert here to speed up process
            #
            # with database.atomic():
            #     AptPackage.bulk_create(packages, 500)
            #
            # http://docs.peewee-orm.com/en/latest/peewee/querying.html#alternatives
            #

            for package in util.parse_packages_gz(packages_gz):
                p_dict = util.package_data_to_dict(package)
                pkg = AptPackage.from_dict(p_dict)
                AptPackage.add_or_update(pkg)
                try:
                    PackageLocation(
                        sha256=p_dict['sha256'],
                        location="{}/{}".format(url, p_dict['filename'])
                    ).save()
                except:  # todo: be more explicit, expect index / integrity error
                    pass

                # todo: show progress


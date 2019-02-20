# Beiran P2P Package Distribution Layer
# Copyright (C) 2019  Rainlab Inc & Creationline, Inc & Beiran Contributors
#
# Rainlab Inc. https://rainlab.co.jp
# Creationline, Inc. https://creationline.com">
# Beiran Contributors https://docs.beiran.io/contributors.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#!/bin/env python
"""command line client for managing beiran daemon"""

import sys
import logging
import importlib
from typing import List

import click

from beiran.models import PeerAddress
from beiran.util import Unbuffered
from beiran.sync_client import Client
from beiran.log import build_logger
from beiran.client import Client as AsyncClient
from beiran.config import config

# pylint: disable=invalid-name
logger = build_logger()  # type: ignore


sys.stdout = Unbuffered(sys.stdout) # type: ignore


class BeiranContext:
    """Context object for Beiran Commands which keeps clients and other common objects"""

    def __init__(self) -> None:
        daemon_url = config.url if config.url != '' else \
                     "http+unix://" + config.socket_file

        peer_address = PeerAddress(address=daemon_url)
        self.beiran_url = peer_address.location

        self.beiran_client = Client(peer_address=peer_address)
        self.async_beiran_client = AsyncClient(peer_address=peer_address)
        self.config = config


# pylint: disable=invalid-name
pass_context = click.make_pass_decorator(BeiranContext, ensure=True)


class BeiranCLI(click.MultiCommand):
    """BeiranCLI loads dynamically commands from installed plugins
    and appends commands of `beiran` itself as `node` group"""


    def list_commands(self, ctx) -> List[str]:  # type: ignore
        """
        Lists of subcommand names

        Args:
            ctx (BeiranContext): context object

        Returns:
            list: list of subcommand names

        """
        commands = list()
        for plugin in config.enabled_plugins:
            cli_module_path = "{}.cli_{}".format(
                plugin['package'],
                plugin['name']
            )
            try:
                importlib.import_module(cli_module_path)
                commands.append(plugin['name'])
            except(ModuleNotFoundError, ImportError):
                logger.debug("This plugin has no cli, skipping..: %s",
                             plugin['package'])

        commands.append("node")
        commands.sort()
        return commands

    def __call__(self, *args, **kwargs):
        """
        TODO: Temporary workaround. We should find more proper way!
        """
        try:
            return self.main(*args, **kwargs)
        except Exception as err:  # pylint: disable=broad-except

            def fix_bytes(mes):
                if isinstance(mes, bytes):
                    return mes.decode()
                return mes

            if hasattr(err, 'code'):
                if err.code == 500:  # pylint: disable=no-member
                    click.echo('\nInternal Error!. '
                               'See execution info below:\n{}\n\n'.format(str(err)))
                    raise err

            message = None

            if hasattr(err, 'message'):
                message = fix_bytes(err.message)  # pylint: disable=no-member

            if hasattr(err, 'response'):
                if err.response.body:  # pylint: disable=no-member
                    message = fix_bytes(err.response.body)  # pylint: disable=no-member

            click.echo('\nError! Details are below,'
                       ' check your command again: \n\n{}\n'.format(message or str(err)))

    def get_command(self, ctx: BeiranContext, cmd_name: str) -> click.group:  # type: ignore
        """
        Load command object

        Args:
            ctx (BeiranContext): context object
            cmd_name (str): subcommand name

        Returns:
            click.group: subcommand group object

        """
        if cmd_name == "node":
            cli_module = '{}.cli_{}'.format("beiran", cmd_name)
            module = importlib.import_module(cli_module)
            return module.cli  # type: ignore

        for plugin in config.enabled_plugins:
            if plugin['name'] != cmd_name:
                continue
            try:
                cli_module = '{}.cli_{}'.format(plugin['package'], plugin['name'])
                module = importlib.import_module(cli_module)
                return module.cli  # type: ignore
            except ModuleNotFoundError as error:
                logger.debug("This plugin has no cli, skipping..: %s \n\n %s",
                             plugin, error)


@click.group(cls=BeiranCLI, chain=False, invoke_without_command=True, no_args_is_help=True)
@click.option('--debug', is_flag=True, default=False, help='Enable debug logs.')
@click.option('--config', "config_file", default=None, required=False,
              help="Path to a Beiran config file. It must be a TOML file."
              )
def main(debug: bool = False, config_file: str = None):
    """Manage Beiran Daemon and Beiran Cluster

    Please use --help option with commands and sub-commands
    to get their detailed usage.

    beiran [COMMAND] [SUB-COMMAND...] --help

    \b
    beiran --help
    beiran node --help
    beiran node probe --help
    beiran docker image list --help

    If you need, specify --config before everything:

    beiran --config /path/to/config.toml sub-command sub-command args options

    """
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.info("set debug level")
    if config_file:
        # already handled see below where main is called.
        # config(config_file=config_file)
        pass


if __name__ == '__main__':

    # workaround for click's chained commands weird bug.
    # somehow chain is broken after 3rd parameter, such as:
    # although `beiran docker image --help ` works, on the other hand
    # `beiran docker image list --help` doesn't.
    # for now make main method accept general parameters,
    # such as config, debug, etc
    # and handle them here..
    try:
        index = sys.argv.index('--config')
        if index:
            _ = sys.argv.pop(index)  # pop --config
            cfile = sys.argv.pop(index)  # now pop the next value, e.g. config.toml
            config(config_file=cfile)
            logger.debug(config.enabled_plugins)
    except ValueError:
        logger.debug("No config file specified, default config in use")
    main()

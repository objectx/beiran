#!/bin/env python
"""command line client for managing beiran daemon"""

import os
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
        if 'BEIRAN_SOCK' in os.environ:
            daemon_url = "http+unix://" + os.environ['BEIRAN_SOCK']
        elif 'BEIRAN_URL' in os.environ:
            daemon_url = os.environ['BEIRAN_URL']
        else:
            daemon_url = "http+unix://{}/beirand.sock".format(config.run_dir)

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
            except ModuleNotFoundError or ImportError:
                logger.info("This plugin has no cli, skipping..: %s",
                            plugin['package'])

        commands.append("node")
        commands.sort()
        return commands

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
            try:
                cli_module = '{}.cli_{}'.format(plugin['package'], cmd_name)
                module = importlib.import_module(cli_module)
                return module.cli  # type: ignore
            except ModuleNotFoundError as error:
                logger.info("This plugin has no cli, skipping..: %s \n\n %s",
                            plugin, error)


@click.command(cls=BeiranCLI)
@click.option('--debug', is_flag=True, default=False, help='Debug log enable')
def main(debug=False):
    """Main entrypoint."""
    if debug:
        logger.setLevel(logging.DEBUG)


if __name__ == '__main__':
    main()

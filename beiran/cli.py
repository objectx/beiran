#!/bin/env python
"""command line client for managing beiran daemon"""

import os
import sys
import logging
import click
import importlib
import pkgutil

from beiran.util import Unbuffered
from beiran.sync_client import Client
from beiran.log import build_logger
from beiran.client import Client as AsyncClient
from beiran.plugin import get_installed_plugins

LOG_LEVEL = logging.getLevelName(os.getenv('LOG_LEVEL', 'WARNING'))
logger = build_logger(None, LOG_LEVEL) # pylint: disable=invalid-name


sys.stdout = Unbuffered(sys.stdout)

CONTEXT_SETTINGS = dict(auto_envvar_prefix='COMPLEX')


class BeiranContext(object):
    """Context object for Beiran Commands which keeps clients and other common objects"""

    def __init__(self):
        self.beiran_url = os.getenv('BEIRAN_SOCK', None) or \
                     os.getenv('BEIRAN_URL', None) or \
                     "http+unix:///var/run/beirand.sock"

        self.beiran_client = Client(self.beiran_url)
        self.async_beiran_client = AsyncClient(self.beiran_url)


pass_context = click.make_pass_decorator(BeiranContext, ensure=True)


class BeiranCLI(click.MultiCommand):
    """BeiranCLI loads dynamically commands from installed plugins
    and appends commands of `beiran` itself as `node` group"""

    installed_plugins = get_installed_plugins()

    def list_commands(self, ctx):
        """
        Lists of subcommand names

        Args:
            ctx (BeiranContext): context object

        Returns:
            list: list of subcommand names

        """
        commands = list()
        for beiran_plugin in self.installed_plugins:
            module = importlib.import_module(beiran_plugin)
            for _, modname, _ in pkgutil.iter_modules(module.__path__):
                if modname.startswith('cli_'):
                    commands.append(modname.split('_')[1])

        commands.append("node")
        commands.sort()
        return commands

    def get_command(self, ctx, name):
        """
        Load command object

        Args:
            ctx (BeiranContext): context object
            name (str): subcommand name

        Returns:
            click.group: subcommand group object

        """
        if name == "node":
            cli_module = '{}.cli_{}'.format("beiran", name)
            module = importlib.import_module(cli_module)
            return module.cli

        for plugin in self.installed_plugins:
            try:
                cli_module = '{}.cli_{}'.format(plugin, name)
                module = importlib.import_module(cli_module)
                return module.cli
            except ModuleNotFoundError:
                pass


@click.command(cls=BeiranCLI)
@click.option('--debug', is_flag=True, default=False, help='Debug log enable')
@pass_context
def main(ctx, debug=False):
    """Main entrypoint."""
    if debug:
        logger.setLevel(logging.DEBUG)


if __name__ == '__main__':
    main()

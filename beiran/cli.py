#!/bin/env python
"""command line client for managing beiran daemon"""

import os
import sys
import logging
import importlib
import pkgutil
from typing import List

import click

from beiran.models import PeerAddress
from beiran.util import Unbuffered
from beiran.sync_client import Client
from beiran.log import build_logger
from beiran.client import Client as AsyncClient
from beiran.plugin import get_installed_plugins
from beiran.config import config

LOG_LEVEL = logging.getLevelName(config.log_level) # type: ignore

# pylint: disable=invalid-name
logger = build_logger(None, LOG_LEVEL)  # type: ignore


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

        # TODO: These key files should be generated by beirand, and chowned as `root:beiran`
        #       so, only users in beiran group can access the socket and communicate with it
        #       the daemon might allow other connections, but would not authorize them.
        # self.client_key = "/etc/beiran/client.key"
        # self.client_cert = "/etc/beiran/client.crt"

        # self.beiran_client = beiran.Client(self.beiran_url,
        #     client_key = client_key, client_cert = client_cert)
        self.beiran_client = Client(peer_address=peer_address)
        self.async_beiran_client = AsyncClient(peer_address=peer_address)


# pylint: disable=invalid-name
pass_context = click.make_pass_decorator(BeiranContext, ensure=True)


class BeiranCLI(click.MultiCommand):
    """BeiranCLI loads dynamically commands from installed plugins
    and appends commands of `beiran` itself as `node` group"""

    installed_plugins = get_installed_plugins()

    def list_commands(self, ctx) -> List[str]:  # type: ignore
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
            for _, modname, _ in pkgutil.iter_modules(module.__path__):  # type: ignore
                if modname.startswith('cli_'):
                    commands.append(modname.split('_')[1])

        commands.append("node")
        commands.sort()
        return commands

    def __call__(self, *args, **kwargs):
        """
        TODO: Temporary workaround. We should find more proper way!
        """
        try:
            return self.main(*args, **kwargs)
        except Exception as err:

            def fix_bytes(mes):
                if isinstance(mes, bytes):
                    return mes.decode()
                else:
                    return mes

            if hasattr(err, 'code'):
                if err.code == 500:
                    click.echo('\nInternal Error!. See execution info below:\n{}\n\n'.format(str(err)))
                    raise err

            message = None

            if hasattr(err, 'message'):
                message = fix_bytes(err.message)

            if hasattr(err, 'response'):
                if err.response.body:
                    message = fix_bytes(err.response.body)

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

        for plugin in self.installed_plugins:
            try:
                cli_module = '{}.cli_{}'.format(plugin, cmd_name)
                module = importlib.import_module(cli_module)
                return module.cli  # type: ignore
            except ModuleNotFoundError:
                pass


@click.command(cls=BeiranCLI)
@click.option('--debug', is_flag=True, default=False, help='Debug log enable')
def main(debug=False):
    """Main entrypoint."""
    if debug:
        logger.setLevel(logging.DEBUG)


if __name__ == '__main__':
    main()

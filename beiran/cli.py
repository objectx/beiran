#!/bin/env python
"""command line client for managing beiran daemon"""

import os
import sys
import logging
import click
from tabulate import tabulate

from beiran.util import Unbuffered, exit_print
from beiran.version import get_version
from beiran.sync_client import Client
from beiran.log import build_logger
from beiran.client import Client as AsyncClient
from beiran.models import Node
from beiran.plugin import get_installed_plugins
import importlib

LOG_LEVEL = logging.getLevelName(os.getenv('LOG_LEVEL', 'WARNING'))
logger = build_logger(None, LOG_LEVEL) # pylint: disable=invalid-name

VERSION = get_version('short', 'library')

sys.stdout = Unbuffered(sys.stdout)


class CLIClient:
    ctx = None  # todo: remove
    singleton = None  # todo: remove

    def __init__(self):
        CLIClient.singleton = self  # todo: remove
        self.beiran_url = "http+unix:///var/run/beirand.sock"
        if 'BEIRAN_URL' in os.environ:
            self.beiran_url = os.environ['BEIRAN_URL']
        elif 'BEIRAN_SOCK' in os.environ:
            self.beiran_url = "http+unix://" + os.environ['BEIRAN_SOCK']

        self.beiran_client = Client(self.beiran_url)
        self.async_beiran_client = AsyncClient(self.beiran_url)


class BeiranCLI(click.MultiCommand, CLIClient):

    def list_commands(self, ctx):
        rv = get_installed_plugins()
        rv.append("beiran")
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        try:
            module = importlib.import_module('{}.cli'.format(name))
            return module.cli
        except ModuleNotFoundError:
            pass


@click.group("node")
def cli():
    """cli command set of node itself."""
    pass


@cli.command("version")
@click.pass_obj
def version(self):
    """prints the versions of each component"""
    print("CLI Version: " + VERSION)
    print("Library Version: " + get_version('short', 'library'))
    print("Server Socket: " + self.beiran_url)
    try:
        print("Daemon Version: " + self.beiran_client.get_server_version())
    except (ConnectionRefusedError, FileNotFoundError):
        exit_print(1, "Cannot connect to server")


@cli.command('list')
@click.option('--all', 'all_nodes', default=False, is_flag=True,
              help='List all known nodes (including offline ones)')
@click.pass_obj
def node_list(self, all_nodes):
    """List known beiran nodes"""
    nodes = self.beiran_client.get_nodes(all_nodes=all_nodes)
    table = []
    for node_ in nodes:
        if 'docker' in node_ and node_['docker']:
            docker_version = node_['docker']['ServerVersion']
        else:
            docker_version = 'N/A'
        table.append([
            node_['uuid'],
            node_['ip_address'] + ':' + str(node_['port']),
            node_['version'],
            docker_version,
            node_['status'] if 'status' in node_ else Node.STATUS_UNKNOWN
        ])
    print(tabulate(table, headers=["UUID", "IP:Port", "Version", "Docker Ver.", "Status?"]))


@cli.command('info')
@click.argument('uuid', required=False)
@click.pass_obj
def node_info(self, uuid):
    """Show information about node"""
    info = self.beiran_client.get_node_info(uuid)
    table = []
    for key, value in info.items():
        if key == 'docker':
            table.append([key, value['ServerVersion'] if value else 'N/A'])
            continue
        table.append([key, value])
    print(tabulate(table, headers=["Item", "Value"]))


@cli.command('probe')
@click.argument('address', required=False)
@click.pass_obj
def node_probe(self, address):
    """Probe a non-discovered node"""
    info = self.beiran_client.probe_node(address)
    print(info)


@click.command(cls=BeiranCLI)  # todo: check whether group is possible instead of command
@click.option('--debug', is_flag=True, default=False, help='Debug log enable')
@click.pass_context
def main(ctx=None, debug=False):
    """Main entrypoint."""
    if debug:
        logger.setLevel(logging.DEBUG)
    ctx.obj = CLIClient.singleton  # todo: remove


if __name__ == '__main__':
    main()

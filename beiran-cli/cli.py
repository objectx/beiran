#!/bin/env python
"""command line client for managing beiran daemon"""

import os
import sys
import logging
import click
from tabulate import tabulate
from beiran.util import exit_print
from beiran.util import Unbuffered
from beiran.version import get_version
from beiran.client import Client
from beiran.log import build_logger

LOG_LEVEL = logging.getLevelName(os.getenv('LOG_LEVEL', 'WARNING'))
# LOG_FILE = os.getenv('LOG_FILE', '/var/log/beirand.log')
logger = build_logger(None, LOG_LEVEL) # pylint: disable=invalid-name

VERSION = get_version('short', 'cli')

sys.stdout = Unbuffered(sys.stdout)

@click.group()
@click.option('--debug', is_flag=True, default=False, help='Debug log enable')
@click.pass_context
def main(ctx=None, debug=False):
    """main method for click(lib) entry, injects the singleton
    instance of Cli class into click context"""
    if debug:
        logger.setLevel(logging.DEBUG)
    ctx.obj = Cli.singleton

class Cli:
    """beiran cli methods for click(lib)"""
    ctx = None
    singleton = None

    def __init__(self):
        Cli.singleton = self
        self.beiran_url = "http+unix:///var/run/beirand.sock"
        if 'BEIRAN_SOCK' in os.environ:
            self.beiran_url = "http+unix://" + os.environ['BEIRAN_SOCK']
        elif 'BEIRAN_URL' in os.environ:
            self.beiran_url = os.environ['BEIRAN_URL']

        # TODO: These key files should be generated by beirand, and chowned as `root:beiran`
        #       so, only users in beiran group can access the socket and communicate with it
        #       the daemon might allow other connections, but would not authorize them.
        # self.client_key = "/etc/beiran/client.key"
        # self.client_cert = "/etc/beiran/client.crt"

        # self.beiran_client = beiran.Client(self.beiran_url,
        #     client_key = client_key, client_cert = client_cert)
        self.beiran_client = Client(self.beiran_url)

    @click.command('version')
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

    main.add_command(version)

    # ##########  Node management commands

    @click.group()
    @click.pass_obj
    def node(self):
        """group command for node management"""
        pass

    main.add_command(node)

    @click.command('list')
    @click.option('--all', default=False, is_flag=True,
                  help='List all known nodes (including offline ones)')
    @click.pass_obj
    def node_list(self, all_nodes):
        """List known beiran nodes"""
        nodes = self.beiran_client.get_nodes(all_nodes=all_nodes)
        table = [[n['uuid'], n['ip_address'] + ':8888', 'N/A', 'OK'] for n in nodes]
        print(tabulate(table, headers=["UUID", "IP:Port", "Docker Ver.", "Status?"]))

    node.add_command(node_list)

    # ##########  Image management commands

    @click.group()
    @click.pass_obj
    def image(self):
        """group command for image management"""
        pass

    main.add_command(image)

    @click.command('pull')
    @click.argument('imagename')
    @click.pass_obj
    def image_pull(self, imagename):
        """Pull a container image from cluster or repository"""
        click.echo('Pulling image %s!' % imagename)

    image.add_command(image_pull)

    @click.command('list')
    @click.pass_obj
    def image_list(self):
        """List container images across the cluster"""
        click.echo('Listing images!')

    image.add_command(image_list)


if __name__ == '__main__':
    Cli()
    main()

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


def sizeof_fmt(num, suffix='B'):
    """Human readable format for sizes
    source: https://stackoverflow.com/a/1094933
    """
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


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
        if 'BEIRAN_URL' in os.environ:
            self.beiran_url = os.environ['BEIRAN_URL']
        elif 'BEIRAN_SOCK' in os.environ:
            self.beiran_url = "http+unix://" + os.environ['BEIRAN_SOCK']

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
                docker_version,
                'OK'
            ])
        print(tabulate(table, headers=["UUID", "IP:Port", "Docker Ver.", "Status?"]))

    node.add_command(node_list)

    @click.command('info')
    @click.argument('uuid', required=False)
    @click.pass_obj
    def node_info(self, uuid):
        """Sof information about node"""
        info = self.beiran_client.get_node_info(uuid)
        table = []
        for key, value in info.items():
            if key == 'docker':
                table.append([key, value['ServerVersion'] if value else 'N/A'])
                continue
            table.append([key, value])
        print(tabulate(table, headers=["Item", "Value"]))

    node.add_command(node_info)

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
    @click.option('--all', 'all_nodes', default=False, is_flag=True,
                  help='List images from all known nodes')
    @click.option('--node', default=None,
                  help='List images from specific node')
    @click.pass_obj
    def image_list(self, all_nodes, node):
        """List container images across the cluster"""
        images = self.beiran_client.get_images(all_nodes=all_nodes, node_uuid=node)

        table = [
            [",\n".join(i['tags']), sizeof_fmt(i['size']), str(len(i['available_at'])) + ' node(s)']
            for i in images
        ]
        click.echo(tabulate(table, headers=["Tags", "Size", "Availability"]))

    image.add_command(image_list)

    # ##########  Layer management commands

    @click.group()
    @click.pass_obj
    def layer(self):
        """group command for layer management"""
        pass

    main.add_command(layer)

    @click.command('list')
    @click.option('--all', 'all_nodes', default=False, is_flag=True,
                  help='List layers from all known nodes')
    @click.option('--node', default=None,
                  help='List layers from specific node')
    @click.pass_obj
    def layer_list(self, all_nodes, node):
        """List container layers across the cluster"""
        layers = self.beiran_client.get_layers(all_nodes=all_nodes, node_uuid=node)
        table = [
            [i['digest'], sizeof_fmt(i['size']), str(len(i['available_at'])) + ' node(s)']
            for i in layers
        ]
        print(tabulate(table, headers=["Digest", "Size", "Availability"]))

    layer.add_command(layer_list)


Cli()

if __name__ == '__main__':
    main()

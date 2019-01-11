#!/bin/env python
"""command line client for managing beiran daemon"""

import sys
import click
from tabulate import tabulate

from beiran.util import Unbuffered, exit_print
from beiran.version import get_version
from beiran.models import Node
from beiran.cli import pass_context

VERSION = get_version('short', 'library')

sys.stdout = Unbuffered(sys.stdout)  #type: ignore


@click.group()
def cli():
    """Node operations.

    List nodes in cluster, learn information about them.

    Please see sub-commands help.
    """
    pass


@cli.command("version")
@click.pass_obj
@pass_context
def version(ctx):
    """Prints the versions of components of current node."""
    print("CLI Version: " + VERSION)
    print("Library Version: " + get_version('short', 'library'))
    print("Server Socket: " + ctx.beiran_url)
    try:
        print("Daemon Version: " + ctx.beiran_client.get_server_version())
    except (ConnectionRefusedError, FileNotFoundError):
        exit_print(1, "Cannot connect to server")


@cli.command('list', short_help="List cluster nodes")
@click.option('--all', 'all_nodes', default=False, is_flag=True,
              help='List all known nodes (including offline ones)')
@click.pass_obj
@pass_context
def node_list(ctx, all_nodes: bool):
    """List known beiran nodes.

    Use `--all` options to include offline ones.
    """

    nodes = ctx.beiran_client.get_nodes(all_nodes=all_nodes)
    table = []
    for node_ in nodes:
        table.append([
            node_['uuid'],
            node_['ip_address'] + ':' + str(node_['port']),
            node_['version'],
            node_['status'] if 'status' in node_ else Node.STATUS_UNKNOWN
        ])
    print(tabulate(table, headers=["UUID", "IP:Port", "Version", "Status?"]))


@cli.command('info', short_help="Print node details")
@click.argument('uuid', required=False)
@click.pass_obj
@pass_context
def node_info(ctx, uuid: str):
    """Prints detailed information of specified node,
    the current node, if no one is specified.

    Specify node by providing node's UUID:

    beiran node info <UUID>
    """

    info = ctx.beiran_client.get_node_info(uuid)
    table = []
    for key, value in info.items():
        if key == 'docker':
            table.append([key, value['ServerVersion'] if value else 'N/A'])
            continue
        table.append([key, value])
    print(tabulate(table, headers=["Item", "Value"]))


@cli.command('probe', short_help="Probe a non-discovered node")
@click.argument('address', required=True)
@click.pass_obj
@pass_context
def node_probe(ctx, address: str):
    """Probe a non-discovered node.

    Probing node is useful when you need a manual discovery.

    'address' is required argument and it is the beiran url of the node which will be probed.
    All the following formats are supported.

    \b
    node probe http://10.0.1.108:8888
    node probe beiran+http://10.0.1.108:8888
    node probe http://10.0.1.108          # default port is used
    node probe beiran+http://10.0.1.108   # default port is used

    """
    info = ctx.beiran_client.probe_node(address)
    print(info)


@cli.command("start")
def start_daemon():
    """Starts the beiran daemon on current node.

    If you need, please specify --config as below:

    beiran --config /path/to/config.toml node start_daemon

    """
    from beiran.daemon.main import BeiranDaemon
    from beiran.daemon.common import Services

    Services.daemon = BeiranDaemon()  # type: ignore
    Services.daemon.run()  # type: ignore

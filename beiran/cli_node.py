#!/bin/env python
"""command line client for managing beiran daemon"""

import os
import sys
import logging
import click
from tabulate import tabulate

from beiran.util import Unbuffered, exit_print
from beiran.version import get_version
from beiran.log import build_logger
from beiran.models import Node
from beiran.cli import pass_context

VERSION = get_version('short', 'library')

sys.stdout = Unbuffered(sys.stdout)  #type: ignore

@click.group()
def cli():
    """cli command set of node itself."""
    pass


@cli.command("version")
@click.pass_obj
@pass_context
def version(ctx):
    """prints the versions of each component"""
    print("CLI Version: " + VERSION)
    print("Library Version: " + get_version('short', 'library'))
    print("Server Socket: " + ctx.beiran_url)
    try:
        print("Daemon Version: " + ctx.beiran_client.get_server_version())
    except (ConnectionRefusedError, FileNotFoundError):
        exit_print(1, "Cannot connect to server")


@cli.command('list')
@click.option('--all', 'all_nodes', default=False, is_flag=True,
              help='List all known nodes (including offline ones)')
@click.pass_obj
@pass_context
def node_list(ctx, all_nodes: bool):
    """List known beiran nodes"""
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


@cli.command('info')
@click.argument('uuid', required=False)
@click.pass_obj
@pass_context
def node_info(ctx, uuid: str):
    """Show information about node"""
    info = ctx.beiran_client.get_node_info(uuid)
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
@pass_context
def node_probe(ctx, address: str):
    """Probe a non-discovered node"""
    info = ctx.beiran_client.probe_node(address)
    print(info)

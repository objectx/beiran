"""
    Beiran daemon execution script to create server and schedule
    tasks by observing nodes and communication each other.
"""
import os
import sys
import asyncio
import importlib
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.options import options, define
from tornado.netutil import bind_unix_socket
from tornado import httpserver
from peewee import SqliteDatabase
from playhouse.shortcuts import model_to_dict

from beirand.nodes import Nodes

from beirand.common import NODES

from beiran.models import Node
from beiran.models.base import DB_PROXY

from beirand.common import logger
from beirand.http_ws import APP

from beirand.lib import collect_node_info

AsyncIOMainLoop().install()


async def new_node(node):
    """
    Discovered new node on beiran network
    Args:
        node: Node object
    """
    logger.info('new node has reached %s', str(node))


async def removed_node(node):
    """
    Node on beiran network is down
    Args:
        node: Node object
    """
    logger.info('node has been removed %s', str(node))

def db_init():
    # check database file exists
    beiran_db_path = os.getenv("BEIRAN_DB_PATH", '/var/lib/beiran/beiran.db')
    db_file_exists = os.path.exists(beiran_db_path)

    if not db_file_exists:
        logger.info("sqlite file does not exist, creating file %s!..", beiran_db_path)
        open(beiran_db_path, 'a').close()

    # init database object
    database = SqliteDatabase(beiran_db_path)
    DB_PROXY.initialize(database)

    if not db_file_exists:
        logger.info("db hasn't initialized yet, creating tables!..")
        from beiran.models import create_tables

        create_tables(database)


def main():
    """ Main function wrapper """

    # init db first
    db_init()

    logger.info("Starting Daemon HTTP Server...")
    # Listen on Unix Socket
    server = httpserver.HTTPServer(APP)
    logger.info("Listening on unix socket: %s", options.unix_socket)
    socket = bind_unix_socket(options.unix_socket)
    server.add_socket(socket)

    # Also Listen on TCP
    APP.listen(options.listen_port, address=options.listen_address)
    logger.info("Listening on tcp socket: " +
                options.listen_address + ":" +
                str(options.listen_port))

    # collect node info and create node object
    node_info = collect_node_info()
    node = Node(**node_info)
    logger.info("local node created: %s", model_to_dict(node))

    global NODES
    NODES = Nodes()
    NODES.add_new(node)
    logger.info("local node added, known nodes are: %s", NODES.all_nodes)

    loop = asyncio.get_event_loop()
    discovery_mode = os.getenv('DISCOVERY_METHOD') or 'zeroconf'

    try:
        module = importlib.import_module("beirand.discovery." + discovery_mode)
        discovery_class = getattr(module, discovery_mode.title() + "Discovery")
    except ModuleNotFoundError as error:
        logger.error(error)
        logger.error("Unsupported discovery mode: %s", discovery_mode)
        sys.exit(1)

    discovery = discovery_class(loop)
    discovery.on('discovered', new_node)
    discovery.on('undiscovered', removed_node)
    discovery.start()
    loop.set_debug(True)
    loop.run_forever()


if __name__ == '__main__':
    main()

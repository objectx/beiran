"""
    Beiran daemon execution script to create server and schedule
    tasks by observing nodes and communication each other.
"""
import os
import sys
import asyncio
import importlib

from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.options import options
from tornado.netutil import bind_unix_socket
from tornado import httpserver

from beirand.common import logger
from beirand.common import NODES
from beirand.common import EVENTS
from beirand.common import AIO_DOCKER_CLIENT

from beirand.http_ws import APP
from beirand.lib import collect_node_info, update_docker_info
from beirand.lib import get_listen_port

from beiran.models import Node

AsyncIOMainLoop().install()


async def new_node(ip_address, service_port=None):
    """
    Discovered new node on beiran network
    Args:
        ip_address (str): ip_address of new node
        service_port (str): service port of new node
    """
    service_port = service_port or get_listen_port()

    logger.info('New node has reached ip: %s / port: %s', ip_address, service_port)

    timeout = 10
    while timeout:
        node = NODES.get_node_by_ip(ip_address)
        if node:
            logger.info(
                'New node will be published has reached ip: %s / port: %s',
                ip_address, service_port)
            EVENTS.emit('node.added', ip_address, service_port)
            return node
        else:
            logger.info(
                'New node is not accesible, trying again: %s / port: %s', ip_address, service_port)
            await asyncio.sleep(3)  # no need to rush, take your time!
            node = await NODES.add_or_update_new_remote_node(ip_address, service_port)
            timeout -= 1

async def removed_node(node):
    """
    Node on beiran network is down
    Args:
        node: Node object
    """
    logger.info('Node is about to be removed %s', str(node))
    if isinstance(node, str):
        node = NODES.get_node_by_ip(node)
        logger.debug('Pointed the node by ip address: %s', node.uuid)
    removed = NODES.remove_node(node)
    logger.debug('Removed? %s', removed)

    if removed:
        EVENTS.emit('node.removed', node)

async def on_node_removed(node):
    """Placeholder for event on node removed"""
    logger.info("new event: an existing node removed %s", node.uuid)

async def on_new_node_added(ip_address, service_port):
    """Placeholder for event on node removed"""
    logger.info("new event: new node added on %s at port %s", ip_address, service_port)

def db_init():
    """Initialize database"""
    from peewee import SqliteDatabase
    from beiran.models.base import DB_PROXY

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

    # set database
    logger.info("Initializing database...")
    db_init()

    loop = asyncio.get_event_loop()

    # collect node info and create node object
    NODES.local_node = Node.from_dict(collect_node_info())

    # this is async but we will let it run in background, we have no rush
    # TODO: Check if this needs to be here
    loop.run_until_complete(update_docker_info(NODES.local_node, AIO_DOCKER_CLIENT))
    # NODES.local_node.docker = .info()


    NODES.add_or_update(NODES.local_node)
    logger.info("local node added, known nodes are: %s", NODES.all_nodes)

    # HTTP Daemon. Listen on Unix Socket
    logger.info("Starting Daemon HTTP Server...")
    server = httpserver.HTTPServer(APP)
    logger.info("Listening on unix socket: %s", options.unix_socket)
    socket = bind_unix_socket(options.unix_socket)
    server.add_socket(socket)

    # Also Listen on TCP
<<<<<<< HEAD
    server.listen(options.listen_port, address=options.listen_address)
=======
>>>>>>> dev-201803
    logger.info("Listening on tcp socket: %s:%s", options.listen_address, options.listen_port)
    APP.listen(options.listen_port, address=options.listen_address)

    # Register daemon events
    EVENTS.on('node.added', on_new_node_added)
    EVENTS.on('node.removed', on_node_removed)

    # peer discovery starts
    discovery_mode = os.getenv('DISCOVERY_METHOD') or 'zeroconf'
    logger.debug("Discovery method is %s", discovery_mode)

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
    # peer discovery

    loop.set_debug(True)
    loop.run_forever()

if __name__ == '__main__':
    main()

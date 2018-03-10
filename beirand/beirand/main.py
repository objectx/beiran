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
from beirand.http_ws import APP
from beirand.lib import collect_node_info, fetch_docker_info
from beirand.lib import get_listen_port

AsyncIOMainLoop().install()


async def new_node(ip_address, service_port=None):
    """
    Discovered new node on beiran network
    Args:
        ip_address (str): ip_address of new node
        service_port (str): service port of new node
    """
    service_port = service_port or get_listen_port()

    logger.info('new node has reached ip: %s / port: %s', ip_address, service_port)
    NODES.add_or_update_new_remote_node(ip_address, service_port)
    logger.info(
        'new node will be published has reached ip: %s / port: %s', ip_address, service_port)
    EVENTS.emit('node.added', ip_address, service_port)


async def removed_node(node):
    """
    Node on beiran network is down
    Args:
        node: Node object
    """
    logger.info('node has been removed %s', str(node))
    removed = NODES.remove_node(node)
    if removed:
        EVENTS.emit('node.removed', node)


async def on_node_removed(node):
    """Placeholder for event on node removed"""
    logger.info("new event: an existing node removed %s", node.uuid)


async def on_new_node_added(ip_address, service_port):
    """Placeholder for event on node removed"""
    logger.info("new event: new node added on %s at port %s", ip_address, service_port)


def main():
    """ Main function wrapper """

    logger.info("Starting Daemon HTTP Server...")
    # Listen on Unix Socket
    server = httpserver.HTTPServer(APP)
    logger.info("Listening on unix socket: %s", options.unix_socket)
    socket = bind_unix_socket(options.unix_socket)
    server.add_socket(socket)

    # Also Listen on TCP
    server.listen(options.listen_port, address=options.listen_address)
    logger.info("Listening on tcp socket: %s:%s", options.listen_address, options.listen_port)

    # collect node info and create node object
    node_info = collect_node_info()
    node_info.update(
        {
            'docker': fetch_docker_info()
        }
    )

    NODES.add_or_update(node_info)
    logger.info("local node added, known nodes are: %s", NODES.all_nodes)

    loop = asyncio.get_event_loop()
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

    EVENTS.on('node.added', on_new_node_added)
    EVENTS.on('node.removed', on_node_removed)

    loop.set_debug(True)
    loop.run_forever()


if __name__ == '__main__':
    main()

"""
    Beiran daemon execution script to create server and schedule
    tasks by observing nodes and communication each other.
"""
import os
import sys
import asyncio
import logging
import importlib
import signal

from tornado import websocket, web
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.options import options
from tornado.netutil import bind_unix_socket
from tornado import httpserver

from pyee import EventEmitter

from beirand.common import VERSION
from beirand.common import logger
from beirand.common import NODES
from beirand.common import EVENTS
from beirand.common import PLUGINS

from beirand.lib import collect_node_info
from beirand.lib import get_listen_port, get_advertise_address
from beirand.peer import Peer
from beirand.http_ws import ROUTES

from beiran.models import Node
from beiran.log import build_logger

AsyncIOMainLoop().install()


class BeiranDaemon(EventEmitter):
    """Beiran Daemon"""

    def __init__(self, loop=None):
        super().__init__()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.available_plugins = []
        self.search_plugins()

    async def new_node(self, ip_address, service_port=None, **kwargs):  # pylint: disable=unused-argument
        """
        Discovered new node on beiran network
        Args:
            ip_address (str): ip_address of new node
            service_port (str): service port of new node
        """
        service_port = service_port or get_listen_port()

        logger.info('New node detected, reached: %s:%s, waiting info', ip_address, service_port)

        retries_left = 10

        # check if we had prior communication with this node
        node = NODES.get_node_by_ip_and_port(ip_address, service_port)
        # FIXME! NO! fetch that node's info, get it's uuid. and match db using that
        if node:
            # fetch up-to-date information and mark the node as online
            node = await NODES.add_or_update_new_remote_node(ip_address, service_port)

        # first time we met with this node, wait for information to be fetched
        # or we couldn't fetch node information at first try
        while retries_left and not node:
            logger.info(
                'Detected not is not accesible, trying again: %s:%s', ip_address, service_port)
            await asyncio.sleep(3)  # no need to rush, take your time!
            node = await NODES.add_or_update_new_remote_node(ip_address, service_port)
            retries_left -= 1

        if not node:
            logger.warning('Cannot fetch node information, %s:%s', ip_address, service_port)
            EVENTS.emit('node.error', ip_address, service_port)
            return

        node.status = 'connecting'
        node.save()

        logger.info(
            'Detected node became online, uuid: %s, %s:%s',
            node.uuid.hex, ip_address, service_port)
        EVENTS.emit('node.added', node)

    async def removed_node(self, ip_address, service_port=None):
        """
        Node on beiran network is down
        Args:
            ip_address (str): ip_address of new node
            service_port (str): service port of new node
        """
        node = NODES.get_node_by_ip_and_port(ip_address, service_port)
        logger.info('Node is about to be removed %s', str(node))
        removed = NODES.remove_node(node)
        logger.debug('Removed? %s', removed)

        if removed:
            EVENTS.emit('node.removed', node)

    async def on_node_removed(self, node):
        """Placeholder for event on node removed"""
        logger.info("new event: an existing node removed %s", node.uuid)

    async def on_new_node_added(self, node):
        """Placeholder for event on node removed"""
        Peer(node)

    async def get_plugin(self, plugin_type, plugin_name, config):
        try:
            config['logger'] = build_logger('plugin:' + plugin_name)
            config['node'] = NODES.local_node
            module = importlib.import_module('beiran_%s_%s' % (plugin_type, plugin_name))
            logger.debug("initializing plugin: " + plugin_name)
            instance = module.Plugin(config)
            await instance.init()
            logger.info("plugin initialisation done: " + plugin_name)
            return instance
        except ModuleNotFoundError as error:
            logger.error(error)
            logger.error("Cannot find plugin : %s", plugin_name)
            sys.exit(1)

    def search_plugins(self):
        """Temporary function for testing python plugin distribution methods"""
        import pkgutil

        self.available_plugins = [
            name
            for finder, name, ispkg
            in pkgutil.iter_modules()
            if name.startswith('beiran_')
        ]
        print("Found plugins;", self.available_plugins)

    async def db_init(self):
        """Initialize database"""
        from peewee import SqliteDatabase, OperationalError
        from beiran.models.base import DB_PROXY
        from beiran.models import MODEL_LIST

        # check database file exists
        beiran_db_path = os.getenv("BEIRAN_DB_PATH", '/var/lib/beiran/beiran.db')
        db_file_exists = os.path.exists(beiran_db_path)

        if not db_file_exists:
            logger.info("sqlite file does not exist, creating file %s!..", beiran_db_path)
            open(beiran_db_path, 'a').close()

        # init database object
        database = SqliteDatabase(beiran_db_path)
        DB_PROXY.initialize(database)

        logger.debug("Checking tables")
        for model in list(MODEL_LIST):
            logger.debug("Checking a model")
            try:
                model.select().limit(0).get()
            except OperationalError as err:
                logger.info("Database schema is not up-to-date, destroying")
                # database is somewhat broken (old)
                # purge it so it can be created again
                database.close()
                os.remove(beiran_db_path)
                open(beiran_db_path, 'a').close()
                database = SqliteDatabase(beiran_db_path)
                DB_PROXY.initialize(database)
                db_file_exists = False
            except model.DoesNotExist as err:  # pylint: disable=unused-variable
                # not a problem
                continue
            except Exception as err:  # pylint: disable=broad-except
                logger.error("Checking a table failed")
                print(err)
        logger.debug("Checking tables done")

        if not db_file_exists:
            logger.info("db hasn't initialized yet, creating tables!..")
            from beiran.models import create_tables

            create_tables(database)

    async def main(self):
        """ Main function """

        # set database
        logger.info("Initializing database...")
        await self.db_init()

        # collect node info and create node object
        NODES.local_node = Node.from_dict(collect_node_info())
        NODES.add_or_update(NODES.local_node)
        self.set_status('init')
        logger.info("local node added, known nodes are: %s", NODES.all_nodes)

        # PREPARE ROUTES
        api_app = web.Application(ROUTES)

        # HTTP Daemon. Listen on Unix Socket
        logger.info("Starting Daemon HTTP Server...")
        server = httpserver.HTTPServer(api_app)
        logger.info("Listening on unix socket: %s", options.unix_socket)
        socket = bind_unix_socket(options.unix_socket)
        server.add_socket(socket)

        # Also Listen on TCP
        logger.info("Listening on tcp socket: %s:%s", options.listen_address, options.listen_port)
        server.listen(options.listen_port, address=options.listen_address)

        # Register daemon events
        EVENTS.on('node.added', self.on_new_node_added)
        EVENTS.on('node.removed', self.on_node_removed)

        EVENTS.on('probe', self.new_node) # TEMP

        # Initialize discovery
        discovery_mode = os.getenv('DISCOVERY_METHOD') or 'zeroconf'
        logger.debug("Discovery method is %s", discovery_mode)
        discovery = await self.get_plugin('discovery', discovery_mode, {
            "address": get_advertise_address(),
            "port": get_listen_port(),
            "version": VERSION,
            "events": EVENTS
        })

        discovery.on('discovered', self.new_node)
        discovery.on('undiscovered', self.removed_node)

        # Only one discovery plugin at a time is supported
        PLUGINS['discovery'] = discovery

        # Initialize package plugins
        package_plugins_enabled = ['docker']

        for _plugin in package_plugins_enabled:
            _plugin_obj = await self.get_plugin('package', _plugin, {
                "storage": "/var/lib/docker",
                "url": None, # default
                "events": EVENTS
            })
            PLUGINS['package:' + _plugin] = _plugin_obj
            await _plugin_obj.start()
            if _plugin_obj.api_routes:
                logger.info("insert {plugin} routes {plugin} namespace".format(plugin=_plugin))
                api_app.add_handlers(r".*", _plugin_obj.api_routes)

        await discovery.start()
        self.set_status('ready')

    def set_status(self, new_status):
        NODES.local_node.status = new_status
        NODES.local_node.save()
        EVENTS.emit('node.status', NODES.local_node, new_status)

    async def shutdown(self):
        """Graceful shutdown"""
        self.set_status('closing')

        logger.info("stopping discovery")
        await PLUGINS['discovery'].stop()
        del PLUGINS['discovery']

        for name, plugin in PLUGINS.items():
            logger.info("stopping %s", name)
            await plugin.stop()

        logger.info("exiting")
        sys.exit(0)

    def schedule_shutdown(self, signum, frame): # pylint: disable=unused-argument
        """Signal Handler"""
        print("Shutting down")
        self.loop.stop()

    def run(self):
        """
        Main function wrapper, creates the main loop and
        schedules the main function in there
        """
        signal.signal(signal.SIGTERM, self.schedule_shutdown)

        self.loop.create_task(self.main())
        self.loop.set_debug(True)
        try:
            self.loop.run_forever()
        except KeyboardInterrupt as e:
            logger.info("Received interrupt, shutting down gracefully")

        try:
            self.loop.run_until_complete(self.shutdown())
        except KeyboardInterrupt as e:
            logger.warning("Received interrupt while shutting down, exiting")
            sys.exit(1)

        self.loop.close()

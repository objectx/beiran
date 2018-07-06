"""
    Beiran daemon execution script to create server and schedule
    tasks by observing nodes and communication each other.
"""
import os
import sys
import asyncio
import asyncio.unix_events as unix_events
import importlib
import signal
import logging
from functools import partial

from typing import Any

import aiohttp

from tornado import web
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.options import options
from tornado.netutil import bind_unix_socket
from tornado import httpserver

from pyee import EventEmitter

from beirand.common import VERSION
from beirand.common import EVENTS
from beirand.common import Services
from beirand.common import DATA_FOLDER

from beirand.nodes import Nodes
from beirand.lib import collect_node_info
from beirand.lib import get_listen_port, get_advertise_address
from beirand.lib import update_sync_version_file
from beirand.http_ws import ROUTES
from beirand.version import __version__

from beiran.models import Node
from beiran.log import build_logger

AsyncIOMainLoop().install()


class BeiranDaemon(EventEmitter):
    """Beiran Daemon"""
    version = __version__

    def __init__(self, loop: unix_events._UnixSelectorEventLoop = None) -> None: # pylint: disable=W0212
        super().__init__()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.nodes = Nodes()
        self.available_plugins = [] # type: list
        self.search_plugins()
        self.sync_state_version = 0

    async def new_node(self, ip_address: str, service_port: int = None, **kwargs):  # pylint: disable=unused-argument
        """
        Discovered new node on beiran network
        Args:
            ip_address (str): ip_address of new node
            service_port (int): service port of new node
        """
        service_port = service_port or get_listen_port()

        Services.logger.info('New node detected, reached: %s:%s, waiting info',
                             ip_address, service_port)
        url = "beiran://{}:{}".format(ip_address, service_port)
        node = await self.nodes.probe_node(url=url)

        if not node:
            EVENTS.emit('node.error', ip_address, service_port)
            return

        EVENTS.emit('node.added', node)

    async def removed_node(self, ip_address: str, service_port: int = None):
        """
        Node on beiran network is down
        Args:
            ip_address (str): ip_address of new node
            service_port (int): service port of new node
        """

        service_port = service_port or get_listen_port()
        try:
            node = await self.nodes.get_node_by_ip_and_port(ip_address, service_port)
        except Node.DoesNotExist:
            Services.logger.warning('Cannot find node at %s:%d for removing',
                                    ip_address, service_port)
            return

        Services.logger.info('Node is about to be removed %s', str(node))
        self.nodes.remove_node(node)

        EVENTS.emit('node.removed', node)

    async def probe_specific_node(self, url: str, sleep_time: int) -> Node:
        """Repeat probing peers"""

        while True:
            status = None
            try:
                node = await self.nodes.get_node_by_url(url)
                if node.uuid.hex in self.nodes.connections: # type: ignore
                    # TODO: What to do if status == "lost"
                    return node
                status = node.status
            except Node.DoesNotExist:
                pass

            if status:
                Services.logger.debug("Node %s is %s", url, status)

            try:
                await self.nodes.probe_node(url=url)
            except ConnectionRefusedError:
                Services.logger.debug("Node not found: %s", url)
            except aiohttp.client_exceptions.ClientConnectorError:
                Services.logger.debug("Node not found: %s", url)

            await asyncio.sleep(sleep_time)


    async def on_node_removed(self, node: Node):
        """Placeholder for event on node removed"""
        Services.logger.info("new event: an existing node removed %s", node.uuid)

    async def on_new_node_added(self, node: Node):
        """Placeholder for event on node removed"""
        pass

    async def on_plugin_state_update(self, plugin: Any, update: dict):
        """
        Track updates on (syncable) plugin states

        This will be used for checking if nodes are in sync or not
        """

        # TODO: Implement 1~3 seconds pull-back before updating
        # daemon sync version

        self.sync_state_version += 1
        await update_sync_version_file(self.sync_state_version)
        self.nodes.local_node.last_sync_version = self.sync_state_version
        self.nodes.local_node.save()

        # Services.logger.info("sync version up: %d", self.sync_state_version)
        Services.logger.info("sync version up: %d", self.nodes.local_node.last_sync_version)
        EVENTS.emit('state.update', update, plugin)

    async def get_plugin(self, plugin_type: str, plugin_name: str, config: dict) -> Any:
        """
        Load and initiate plugin
        Args:
            plugin_type (str): plugin type
            plugin_name (str): plugin name
            config (dict): config parameters

        Returns:

        """
        try:
            config['logger'] = build_logger('beiran.plugin.' + plugin_name)
            config['node'] = self.nodes.local_node
            config['daemon'] = self
            config['events'] = EVENTS
            module = importlib.import_module('beiran_%s_%s' % (plugin_type, plugin_name))
            Services.logger.debug("initializing plugin: %s", plugin_name)
            instance = module.Plugin(config) # type: ignore
            await instance.init()
            Services.logger.info("plugin initialisation done: %s", plugin_name)
        except ModuleNotFoundError as error:  # pylint: disable=undefined-variable
            Services.logger.error(error) # type: ignore
            Services.logger.error("Cannot find plugin : %s", plugin_name)
            sys.exit(1)

        # Subscribe to plugin state updates
        if instance.history:
            instance.history.on('update', partial(self.on_plugin_state_update, instance))

        return instance

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

    async def init_db(self, append_new: list = None):
        """Initialize database"""
        from peewee import SqliteDatabase, OperationalError
        from beiran.models.base import DB_PROXY
        from beiran.models import MODEL_LIST

        logger = logging.getLogger('peewee')
        logger.setLevel(logging.INFO)

        # check database file exists
        beiran_db_path = os.getenv("BEIRAN_DB_PATH", '{}/beiran.db'.format(DATA_FOLDER))
        db_file_exists = os.path.exists(beiran_db_path)

        if not db_file_exists:
            Services.logger.info("sqlite file does not exist, creating file %s!..", beiran_db_path)
            open(beiran_db_path, 'a').close()

        # init database object
        database = SqliteDatabase(beiran_db_path)
        DB_PROXY.initialize(database)

        if append_new:
            Services.logger.info("append new tables %s into existing database", append_new)
            from beiran.models import create_tables

            create_tables(database, model_list=append_new)
            return

        Services.logger.debug("Checking tables")
        for model in list(MODEL_LIST):
            Services.logger.debug("Checking a model")
            try:
                model.select().limit(0).get()
            except OperationalError as err:
                Services.logger.info("Database schema is not up-to-date, destroying")
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
                Services.logger.error("Checking a table failed")
                print(err)
        Services.logger.debug("Checking tables done")

        if not db_file_exists:
            Services.logger.info("db hasn't initialized yet, creating tables!..")
            from beiran.models import create_tables # type: ignore

            create_tables(database)

    async def init_plugins(self):
        """Initialize configured plugins"""

        # Initialize discovery
        discovery_mode = os.getenv('DISCOVERY_METHOD') or 'zeroconf'
        if discovery_mode != "none":
            Services.logger.debug("Discovery method is %s", discovery_mode)
            discovery = await self.get_plugin('discovery', discovery_mode, {
                "address": get_advertise_address(),
                "port": get_listen_port(),
                "version": VERSION
            })

            # Only one discovery plugin at a time is supported (for now)
            Services.plugins['discovery'] = discovery

        # Initialize package plugins
        package_plugins_enabled = ['docker']

        for _plugin in package_plugins_enabled:
            _plugin_obj = await self.get_plugin('package', _plugin, {
                "storage": "/var/lib/docker",
                "url": None # default
            })
            Services.plugins['package:' + _plugin] = _plugin_obj

    async def probe_without_discovery(self):
        """Bootstrapping peer without discovery"""
        # Probe Known Nodes
        known_nodes = os.getenv("KNOWN_NODES")
        known_urls = None

        known_urls = known_nodes.split(',') if known_nodes else []

        for known_url in known_urls:
            self.loop.create_task(self.probe_specific_node(known_url, 30))

        # Probe DB Nodes
        db_nodes = Services.daemon.nodes.list_of_nodes(
            from_db=True
        )
        local_node_url = self.nodes.local_node.url_without_uuid

        for db_node in db_nodes:
            db_node_url = db_node.url_without_uuid
            if db_node_url in known_urls:
                continue

            if db_node_url == local_node_url:
                continue

            self.loop.create_task(self.probe_specific_node(db_node_url, 60))

    async def main(self):
        """ Main function """

        # ensure the DATA_FOLDER exists
        Services.logger.info("Checking the data folder...")
        if not os.path.exists(DATA_FOLDER):
            Services.logger.debug("create the folder '%s'", DATA_FOLDER)
            os.makedirs(DATA_FOLDER)
        elif not os.path.isdir(DATA_FOLDER):
            raise RuntimeError("Unexpected file exists")

        # set database
        Services.logger.info("Initializing database...")
        await self.init_db()

        # Set 'offline' to all node status
        self.clean_database()

        # collect node info and create node object
        self.nodes.local_node = Node.from_dict(collect_node_info())
        self.nodes.add_or_update(self.nodes.local_node)
        self.set_status(Node.STATUS_INIT)
        Services.logger.info("local node added, known nodes are: %s", self.nodes.all_nodes)

        # initialize sync_state_version
        self.sync_state_version = self.nodes.local_node.last_sync_version

        # initialize plugins
        await self.init_plugins()

        # initialize plugin models
        for name, plugin in Services.plugins.items():
            if not plugin.model_list:
                continue
            await self.init_db(append_new=plugin.model_list)

        # PREPARE ROUTES
        api_app = web.Application(ROUTES)

        for name, plugin in Services.plugins.items():
            if not plugin.api_routes:
                continue
            Services.logger.info("inserting %s routes...", name)
            api_app.add_handlers(r".*", plugin.api_routes)

        # HTTP Daemon. Listen on Unix Socket
        Services.logger.info("Starting Daemon HTTP Server...")
        server = httpserver.HTTPServer(api_app)
        Services.logger.info("Listening on unix socket: %s", options.unix_socket)
        socket = bind_unix_socket(options.unix_socket)
        server.add_socket(socket)

        # Also Listen on TCP
        Services.logger.info("Listening on tcp socket: %s:%s",
                             options.listen_address, options.listen_port)
        server.listen(options.listen_port, address=options.listen_address)

        # Register daemon events
        EVENTS.on('node.added', self.on_new_node_added)
        EVENTS.on('node.removed', self.on_node_removed)

        # Ready
        self.set_status(Node.STATUS_READY)

        # Start discovery last
        if 'discovery' in Services.plugins:
            Services.plugins['discovery'].on('discovered', self.new_node)
            Services.plugins['discovery'].on('undiscovered', self.removed_node)

            await Services.plugins['discovery'].start()

        # Start plugins
        for name, plugin in Services.plugins.items():
            if 'discovery' in Services.plugins and plugin == Services.plugins['discovery']:
                continue
            Services.logger.info("starting plugin: %s", name)
            await plugin.start()

        # Bootstrapping peer without discovery
        await self.probe_without_discovery()

    def clean_database(self):
        """Set 'offline' to all node status
        """
        nodes = Services.daemon.nodes.list_of_nodes(
            from_db=True
        )
        for node in nodes:
            Services.daemon.nodes.set_offline(node)


    def set_status(self, new_status: str):
        """
        Set and emit node's new status
        Args:
            new_status (str): status

        """
        self.nodes.local_node.status = new_status
        self.nodes.local_node.save()
        EVENTS.emit('node.status', self.nodes.local_node, new_status)

    async def shutdown(self):
        """Graceful shutdown"""
        self.clean_database()
        self.set_status(Node.STATUS_CLOSING)

        if 'discovery' in Services.plugins:
            Services.logger.info("stopping discovery")
            await Services.plugins['discovery'].stop()
            del Services.plugins['discovery']

        for name, plugin in Services.plugins.items():
            Services.logger.info("stopping %s", name)
            await plugin.stop()

        self.nodes.connections = {}

        Services.logger.info("exiting")
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

        self.loop.run_until_complete(self.main())
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            Services.logger.info("Received interrupt, shutting down gracefully")

        try:
            self.loop.run_until_complete(self.shutdown())
        except KeyboardInterrupt:
            Services.logger.warning("Received interrupt while shutting down, exiting")
            sys.exit(1)

        self.loop.close()

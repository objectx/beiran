# Beiran P2P Package Distribution Layer
# Copyright (C) 2019  Rainlab Inc & Creationline, Inc & Beiran Contributors
#
# Rainlab Inc. https://rainlab.co.jp
# Creationline, Inc. https://creationline.com">
# Beiran Contributors https://docs.beiran.io/contributors.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
    Beiran daemon execution script to create server and schedule
    tasks by observing nodes and communication each other.
"""
import os
import sys
import asyncio
import importlib
import signal
import logging

from functools import partial
from typing import Any

from tornado import web
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.options import options
from tornado.netutil import bind_unix_socket
from tornado import httpserver

from pyee import EventEmitter

from beiran.daemon.common import VERSION
from beiran.daemon.common import EVENTS
from beiran.daemon.common import Services

from beiran.daemon.nodes import Nodes
from beiran.daemon.peer import Peer

from beiran.daemon.lib import collect_node_info
from beiran.daemon.lib import get_advertise_address
from beiran.daemon.lib import update_sync_version_file

from beiran.daemon.http_ws import ROUTES
from beiran.daemon.version import __version__

from beiran.config import config
from beiran.models import Node, PeerAddress
from beiran.log import build_logger
from beiran.util import run_in_loop, wait_event

AsyncIOMainLoop().install()


class BeiranDaemon(EventEmitter):
    """Beiran Daemon"""
    version = __version__

    # pylint: disable=W0212
    def __init__(self, loop: asyncio.events.AbstractEventLoop = None) -> None:
        super().__init__()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.nodes = Nodes()
        self.available_plugins: list = []
        self.search_plugins()
        self.sync_state_version = 0
        self.peer = None

    async def new_node(self, peer_address: PeerAddress, **kwargs):  # pylint: disable=unused-argument
        """
        Discovered new node on beiran network
        Args:
            ip_address (str): ip_address of new node
            service_port (int): service port of new node
        """
        Services.get_logger().info('New node detected, reached: %s, waiting info',
                                   peer_address.address)
        # url = "beiran://{}:{}".format(ip_address, service_port)
        node = await self.peer.probe_node(peer_address=peer_address)  # type: ignore

        if not node:
            EVENTS.emit('node.error', peer_address.address)
            return

        EVENTS.emit('node.added', node)

    async def removed_node(self, ip_address: str, service_port: int = None):
        """
        Node on beiran network is down
        Args:
            ip_address (str): ip_address of new node
            service_port (int): service port of new node
        """

        service_port = service_port or config.listen_port
        try:
            node = await self.nodes.get_node_by_ip_and_port(ip_address, service_port)
        except Node.DoesNotExist:
            Services.get_logger().warning('Cannot find node at %s:%d for removing',
                                          ip_address, service_port)
            return

        Services.get_logger().info('Node is about to be removed %s', str(node))
        self.nodes.remove_node(node)

        EVENTS.emit('node.removed', node)

    async def on_node_removed(self, node: Node):

        """Placeholder for event on node removed"""
        Services.get_logger().info("new event: an existing node removed %s", node.uuid)

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

        # Services.get_logger().info("sync version up: %d", self.sync_state_version)
        Services.get_logger().info("sync version up: %d", self.nodes.local_node.last_sync_version)
        EVENTS.emit('state.update', update, plugin)

    # pylint: disable=redefined-outer-name
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
            Services.get_logger().debug("initializing plugin: %s", plugin_name)
            instance = module.Plugin(config) # type: ignore
            await instance.init()
            Services.get_logger().info("plugin initialisation done: %s", plugin_name)
        except ModuleNotFoundError as error:  # pylint: disable=undefined-variable
            Services.get_logger().error(str(error))
            Services.get_logger().error("Cannot find plugin : %s", plugin_name)
            sys.exit(1)

        # Subscribe to plugin state updates
        if instance.history:
            instance.history.on('update', partial(self.on_plugin_state_update, instance))

        return instance

    def get_plugin_instance(self, plugin_name):
        """Return plugin instance"""
        return Services.plugins[plugin_name]

    def check_wait_plugin_status_ready(self, plugin_name, loop=None, timeout=None):
        """Check or wait uniil plugin status to be 'ready'"""
        plugin_instance = self.get_plugin_instance(plugin_name)

        if plugin_instance.status == 'ready':
            return

        run_in_loop(self.wait_plugin_status_ready(plugin_instance, timeout=timeout),
                    loop=loop, sync=True)

    async def wait_plugin_status_ready(self, plugin_instance, timeout=None):
        """Wait until plugin status to be 'ready'"""

        # FIXME! timeout parameter should apply to the whole execution of
        # this method. not just *each* execution of wait_event
        while True:
            await wait_event(plugin_instance, 'status', timeout=timeout)
            if plugin_instance.status == 'ready':
                return

    def search_plugins(self):
        """Temporary function for testing python plugin distribution methods"""

        self.available_plugins = config.enabled_plugins
        print("Found plugins;", self.available_plugins)

    async def init_db(self, append_new: list = None):
        """Initialize database"""
        from peewee import SqliteDatabase, OperationalError
        from beiran.models.base import DB_PROXY
        from beiran.models import MODEL_LIST

        logger = logging.getLogger('peewee')
        logger.setLevel(logging.INFO)

        # check database file exists
        beiran_db_path = config.db_file
        db_file_exists = os.path.exists(beiran_db_path)

        if not db_file_exists:
            Services.get_logger().info("sqlite file does not exist, creating file %s!..",
                                       beiran_db_path)
            open(beiran_db_path, 'a').close()

        # init database object
        database = SqliteDatabase(beiran_db_path)
        DB_PROXY.initialize(database)

        if append_new:
            Services.get_logger().info("append new tables %s into existing database", append_new)
            from beiran.models import create_tables

            create_tables(database, model_list=append_new)
            return

        Services.get_logger().debug("Checking tables")
        for model in list(MODEL_LIST):
            Services.get_logger().debug("Checking a model")
            try:
                model.select().limit(0).get()  # type: ignore
            except OperationalError as err:
                Services.get_logger().info("Database schema is not up-to-date, destroying")
                # database is somewhat broken (old)
                # purge it so it can be created again
                database.close()
                os.remove(beiran_db_path)
                open(beiran_db_path, 'a').close()
                database = SqliteDatabase(beiran_db_path)
                DB_PROXY.initialize(database)
                db_file_exists = False

            except model.DoesNotExist as err:  # type: ignore  # pylint: disable=unused-variable
                # not a problem
                continue
            except Exception as err:  # pylint: disable=broad-except
                Services.get_logger().error("Checking a table failed")
                print(err)
        Services.get_logger().debug("Checking tables done")

        if not db_file_exists:
            Services.get_logger().info("db hasn't initialized yet, creating tables!..")
            from beiran.models import create_tables # type: ignore

            create_tables(database)

    async def init_plugins(self):
        """Initialize configured plugins"""

        # Enable plugins
        shared_config_for_plugins = {
            "version": VERSION,
        }
        for plugin in config.enabled_plugins:
            type_specific_config = dict()
            if plugin['type'] == 'discovery':
                type_specific_config = {
                    "address": get_advertise_address(),
                    "port": config.listen_port
                }
            _plugin_obj = await self.get_plugin(plugin['type'], plugin['name'], {
                **shared_config_for_plugins,
                **type_specific_config,
                **config.get_plugin_config(plugin['type'], plugin['name'])
            })

            # Only one discovery plugin at a time is supported (for now)
            if plugin['type'] == 'discovery' and plugin['name'] == config.discovery_method:
                Services.plugins['discovery'] = _plugin_obj
            else:
                Services.plugins['%s:%s' % (plugin['type'], plugin['name'])] = _plugin_obj

        # resolve dependencies between plugins
        for plugin in Services.plugins.values():
            await plugin.load_depend_plugin_instances(Services.plugins)

    async def probe_without_discovery(self):
        """Bootstrapping peer without discovery"""

        # Probe DB Nodes
        probed_locations = set()
        db_nodes = Services.daemon.nodes.list_of_nodes(
            from_db=True
        )

        for db_node in db_nodes:
            if db_node.uuid.hex == self.nodes.local_node.uuid.hex: # pylint: disable=no-member
                continue
            probed_locations.update({conn.location for conn in db_node.get_connections()})
            self.loop.create_task(
                self.peer.probe_node(
                    peer_address=db_node.get_latest_connection(),
                    retries=60
                )
            )

        # Probe Known Nodes
        known_urls = config.known_nodes
        Services.get_logger().info("KNOWN_NODES are: %s", known_urls)

        for known_url in known_urls:
            peer_address = PeerAddress(address=known_url)
            Services.get_logger().info("trying to probe : %s", peer_address.address)
            if not peer_address.location in probed_locations:
                # try forever
                self.loop.create_task(self.peer.probe_node(peer_address=peer_address, retries=-1))
                # todo: does not iterate until the task above is not finished

    async def main(self):
        """ Main function """

        # ensure the config.data_dir exists
        Services.get_logger().info("Checking the data folder...")
        if not os.path.exists(config.data_dir):
            Services.get_logger().debug("create the folder '%s'", config.data_dir)
            os.makedirs(config.data_dir)
        elif not os.path.isdir(config.data_dir):
            raise RuntimeError("Unexpected file exists")

        # set database
        Services.get_logger().info("Initializing database...")
        await self.init_db()

        # Set 'offline' to all node status
        self.clean_database()

        # collect node info and create node object
        self.nodes.local_node = Node.from_dict(collect_node_info())
        self.nodes.add_or_update(self.nodes.local_node)
        self.set_status(Node.STATUS_INIT)
        Services.get_logger().info("local node added, known nodes are: %s", self.nodes.all_nodes)

        self.peer = Peer.find_or_create(
            node=self.nodes.local_node,
            nodes=self.nodes,
            loop=self.loop,
            local=True)
        self.peer.collect()

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
            Services.get_logger().info("inserting %s routes...", name)
            api_app.add_handlers(r".*", plugin.api_routes)

        # HTTP Daemon. Listen on Unix Socket
        Services.get_logger().info("Starting Daemon HTTP Server...")
        server = httpserver.HTTPServer(api_app)
        Services.get_logger().info("Listening on unix socket: %s", options.unix_socket)
        socket = bind_unix_socket(options.unix_socket)
        server.add_socket(socket)

        # Also Listen on TCP
        Services.get_logger().info("Listening on tcp socket: %s:%s",
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
            Services.get_logger().info("starting plugin: %s", name)
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
            Services.get_logger().info("stopping discovery")
            await Services.plugins['discovery'].stop()
            del Services.plugins['discovery']

        for name, plugin in Services.plugins.items():
            Services.get_logger().info("stopping %s", name)
            await plugin.stop()

        self.nodes.connections = {}

        Services.get_logger().info("exiting")
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
            Services.get_logger().info("Received interrupt, shutting down gracefully")

        try:
            self.loop.run_until_complete(self.shutdown())
        except KeyboardInterrupt:
            Services.get_logger().warning("Received interrupt while shutting down, exiting")
            sys.exit(1)

        self.loop.close()

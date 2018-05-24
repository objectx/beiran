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
from uuid import UUID

from tornado import web
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.options import options
from tornado.netutil import bind_unix_socket
from tornado import httpserver

from pyee import EventEmitter

from beirand.common import VERSION
from beirand.common import EVENTS
from beirand.common import Services
from beirand.common import CONFIG_FOLDER

from beirand.nodes import Nodes
from beirand.lib import collect_node_info
from beirand.lib import get_listen_port, get_advertise_address
from beirand.http_ws import ROUTES
from beirand.version import __version__

from beiran.models import Node
from beiran.log import build_logger
import beiran.defaults as defaults

AsyncIOMainLoop().install()


class BeiranDaemon(EventEmitter):
    """Beiran Daemon"""
    version = __version__

    def __init__(self, loop=None):
        super().__init__()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.nodes = Nodes()
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

        Services.logger.info('New node detected, reached: %s:%s, waiting info',
                             ip_address, service_port)
        url = "beiran://{}:{}".format(ip_address, service_port)
        node = await self.nodes.probe_node(url=url)

        if not node:
            EVENTS.emit('node.error', ip_address, service_port)
            return

        EVENTS.emit('node.added', node)

    async def removed_node(self, ip_address, service_port=None):
        """
        Node on beiran network is down
        Args:
            ip_address (str): ip_address of new node
            service_port (str): service port of new node
        """

        service_port = service_port or get_listen_port()
        node = await self.nodes.get_node_by_ip_and_port(ip_address, service_port)
        if not node:
            Services.logger.warning('Cannot find node at %s:%d for removing',
                                    ip_address, service_port)
            return

        Services.logger.info('Node is about to be removed %s', str(node))
        self.nodes.remove_node(node)

        EVENTS.emit('node.removed', node)

    async def on_node_removed(self, node):
        """Placeholder for event on node removed"""
        Services.logger.info("new event: an existing node removed %s", node.uuid)

    async def on_new_node_added(self, node):
        """Placeholder for event on node removed"""
        pass

    async def get_plugin(self, plugin_type, plugin_name, config):
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
            module = importlib.import_module('beiran_%s_%s' % (plugin_type, plugin_name))
            Services.logger.debug("initializing plugin: %s", plugin_name)
            instance = module.Plugin(config)
            await instance.init()
            Services.logger.info("plugin initialisation done: %s", plugin_name)
            return instance
        except ModuleNotFoundError as error:  # pylint: disable=undefined-variable
            Services.logger.error(error)
            Services.logger.error("Cannot find plugin : %s", plugin_name)
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

    async def init_db(self, append_new=False):
        """Initialize database"""
        from peewee import SqliteDatabase, OperationalError
        from beiran.models.base import DB_PROXY
        from beiran.models import MODEL_LIST

        logger = logging.getLogger('peewee')
        logger.setLevel(logging.INFO)

        # check database file exists
        beiran_db_path = os.getenv("BEIRAN_DB_PATH", '/var/lib/beiran/beiran.db')
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
            from beiran.models import create_tables

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
                "version": VERSION,
                "events": EVENTS
            })

            # Only one discovery plugin at a time is supported (for now)
            Services.plugins['discovery'] = discovery

        # Initialize package plugins
        package_plugins_enabled = ['docker']

        for _plugin in package_plugins_enabled:
            _plugin_obj = await self.get_plugin('package', _plugin, {
                "storage": "/var/lib/docker",
                "url": None, # default
                "events": EVENTS
            })
            Services.plugins['package:' + _plugin] = _plugin_obj

    async def init_keys(self):
        """"""
        cert_file_path   = "/".join([CONFIG_FOLDER, "beiran.crt"])
        key_file_path    = "/".join([CONFIG_FOLDER, "beiran.key"])
        pubkey_file_path = "/".join([CONFIG_FOLDER, "beiran.pub"])
        uuid_conf_path   = "/".join([CONFIG_FOLDER, 'uuid.conf'])

        def create_keys_and_cert():
            from OpenSSL import crypto, SSL
            from socket import gethostname
            from pprint import pprint
            from time import gmtime, mktime

            # create a key pair
            k = crypto.PKey()
            k.generate_key(crypto.TYPE_RSA, 4096)

            # create a self-signed cert
            cert = crypto.X509()
            cert.get_subject().C = "JP"
            cert.get_subject().ST = "Tokyo"
            cert.get_subject().L = "Tokyo"
            cert.get_subject().O = "Beiran Team"
            cert.get_subject().OU = "Package Distribution"
            cert.get_subject().CN = "beirand"
            cert.set_serial_number(1000)
            cert.gmtime_adj_notBefore(0)
            cert.gmtime_adj_notAfter(10*365*24*60*60)
            cert.set_issuer(cert.get_subject())
            cert.set_pubkey(k)
            cert.sign(k, 'sha1')

            with open(cert_file_path, "wt") as file:
                file.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("ascii"))
            with open(key_file_path, "wt") as file:
                file.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("ascii"))
            with open(pubkey_file_path, "wt") as file:
                file.write(crypto.dump_publickey(crypto.FILETYPE_PEM, k).decode("ascii"))

            sha1_fingerprint = cert.digest("sha1").decode("ascii")
            print("FP:", sha1_fingerprint)

            uuid_hex = sha1_fingerprint.replace(':', '').lower()[-32:]
            print("uuid:", uuid_hex)

            with open(uuid_conf_path, "wt") as file:
                file.write(uuid_hex)

            self.uuid = UUID(uuid_hex)

        # with open(key_file_path, 'rt').read() as key_file:
        #     self.private_key = c.load_privatekey(c.FILETYPE_PEM, key_file)

        try:
            print("reading uuid from:", uuid_conf_path)
            with open(uuid_conf_path) as uuid_file:
                uuid_hex = uuid_file.read()
            if len(uuid_hex) != 32:
                raise ValueError("32 bytes expected, found %d bytes" % len(uuid_hex))
            self.uuid = UUID(uuid_hex)
        except (FileNotFoundError, ValueError):
            Services.logger.info("Generating private key and uuid")
            create_keys_and_cert()

    async def main(self):
        """ Main function """

        # set database
        Services.logger.info("Initializing database...")
        await self.init_db()
        await self.init_keys()

        # collect node info and create node object
        self.nodes.local_node = Node.from_dict(collect_node_info())
        self.nodes.local_node.uuid = self.uuid
        self.nodes.add_or_update(self.nodes.local_node)
        self.set_status('init')
        Services.logger.info("local node added, known nodes are: %s", self.nodes.all_nodes)

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

        # # Secure server
        # secure_server = httpserver.HTTPServer(api_app, ssl_options={
        #     "certfile": "/".join([CONFIG_FOLDER, "beiran.crt"]),
        #     "keyfile" : "/".join([CONFIG_FOLDER, "beiran.key"]),
        # })
        # secure_server.listen(8883)

        # Register daemon events
        EVENTS.on('node.added', self.on_new_node_added)
        EVENTS.on('node.removed', self.on_node_removed)

        # Start plugins
        for name, plugin in Services.plugins.items():
            if 'discovery' in Services.plugins and plugin == Services.plugins['discovery']:
                continue
            Services.logger.info("starting plugin: %s", name)
            await plugin.start()

        # Start discovery last
        if 'discovery' in Services.plugins:
            Services.plugins['discovery'].on('discovered', self.new_node)
            Services.plugins['discovery'].on('undiscovered', self.removed_node)

            await Services.plugins['discovery'].start()

        # Ready
        self.set_status('ready')

    def set_status(self, new_status):
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
        self.set_status('closing')

        if 'discovery' in Services.plugins:
            Services.logger.info("stopping discovery")
            await Services.plugins['discovery'].stop()
            del Services.plugins['discovery']

        for name, plugin in Services.plugins.items():
            Services.logger.info("stopping %s", name)
            await plugin.stop()

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

"""
    Beiran daemon execution script to create server and schedule
    tasks by observing nodes and communication each other.
"""
import os
import sys
import asyncio
import importlib
import signal

from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.options import options
from tornado.netutil import bind_unix_socket
from tornado import httpserver

from pyee import EventEmitter

from beirand.common import logger
from beirand.common import NODES
from beirand.common import EVENTS
from beirand.common import AIO_DOCKER_CLIENT

from beirand.http_ws import APP
from beirand.lib import collect_node_info, DockerUtil
from beirand.lib import get_listen_port, get_advertise_address
from beirand.peer import Peer

from beiran.models import Node, DockerImage

AsyncIOMainLoop().install()


async def new_node(ip_address, service_port=None, **kwargs):  # pylint: disable=unused-argument
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


async def removed_node(ip_address, service_port=None, **kwargs):
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


async def on_node_removed(node):
    """Placeholder for event on node removed"""
    logger.info("new event: an existing node removed %s", node.uuid)


async def on_new_node_added(node):
    """Placeholder for event on node removed"""

    Peer(node)


async def on_node_docker_connected():
    """Placeholder for event on node docker connected"""
    logger.info("connected to docker daemon")


def db_init():
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


DOCKER_UTIL = DockerUtil("/var/lib/docker", AIO_DOCKER_CLIENT)


async def probe_docker_daemon():
    """Deal with local docker daemon states"""

    while True:
        # Delete all data regarding our node
        await DockerUtil.reset_docker_info_of_node(NODES.local_node.uuid.hex)

        # wait until we can update our docker info
        await DOCKER_UTIL.update_docker_info(NODES.local_node)

        # connected to docker daemon
        EVENTS.emit('node.docker.up')
        NODES.local_node.save()
        logger.debug("Saved local node")
        print(NODES.local_node.to_dict())

        # Get mapping of diff-id and digest mappings of docker daemon
        await DOCKER_UTIL.get_diffid_mappings()

        # Get layerdb mapping
        await DOCKER_UTIL.get_layerdb_mappings()

        # Get Images
        logger.debug("Getting docker image list..")
        image_list = await AIO_DOCKER_CLIENT.images.list()
        for image_data in image_list:
            if not image_data['RepoTags']:
                continue

            # remove the non-tag tag from tag list
            image_data['RepoTags'] = [t for t in image_data['RepoTags'] if t != '<none>:<none>']

            if not image_data['RepoTags']:
                continue

            image = DockerImage.from_dict(image_data, dialect="docker")
            image_exists_in_db = False
            try:
                image_ = DockerImage.get(DockerImage.hash_id == image_data['Id'])
                old_available_at = image_.available_at
                image_.update_using_obj(image)
                image = image_
                image.available_at = old_available_at
                image_exists_in_db = True

            except DockerImage.DoesNotExist:
                pass

            try:
                image_details = await AIO_DOCKER_CLIENT.images.get(name=image_data['Id'])

                layers = await DOCKER_UTIL.get_image_layers(image_details['RootFS']['Layers'])
            except Exception as err:  # pylint: disable=unused-variable,broad-except
                continue

            image.layers = [layer.digest for layer in layers]

            for layer in layers:
                layer.set_available_at(NODES.local_node.uuid.hex)
                layer.save()

            image.set_available_at(NODES.local_node.uuid.hex)
            image.save(force_insert=not image_exists_in_db)

        # This will be converted to something like
        #   daemon.plugins['docker'].setReady(true)
        # in the future; will we in docker plugin code.
        EVENTS.emit('node.docker.ready')

        # await until docker is unavailable
        logger.debug("subscribing to docker events for further changes")
        subscriber = AIO_DOCKER_CLIENT.events.subscribe()
        while True:
            event = await subscriber.get()
            if event is None:
                break

            if 'id' in event:
                logger.debug("docker event: %s[%s] %s", event['Action'], event['Type'], event['id'])
            else:
                logger.debug("docker event: %s[%s]", event['Action'], event['Type'])

        # This will be converted to something like
        #   daemon.plugins['docker'].setReady(false)
        # in the future; will we in docker plugin code.
        EVENTS.emit('node.docker.down')
        logger.warning("docker connection lost")
        await asyncio.sleep(100)

class BeiranDaemon(EventEmitter):
    """Beiran Daemon"""

    def __init__(self, loop=None):
        super().__init__()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.discovery = self.init_discovery()

    def init_discovery(self):
        """load discovery module and initialize class instance"""

        discovery_mode = os.getenv('DISCOVERY_METHOD') or 'zeroconf'
        logger.debug("Discovery method is %s", discovery_mode)

        try:
            module = importlib.import_module("beirand.discovery." + discovery_mode)
            discovery_class = getattr(module, discovery_mode.title() + "Discovery")
        except ModuleNotFoundError as error:
            logger.error(error)
            logger.error("Unsupported discovery mode: %s", discovery_mode)
            sys.exit(1)

        return discovery_class(self.loop, {
            "address": get_advertise_address(),
            "port": get_listen_port()
        })

    async def main(self):
        """ Main function """

        # set database
        logger.info("Initializing database...")
        db_init()

        # collect node info and create node object
        NODES.local_node = Node.from_dict(collect_node_info())
        NODES.local_node.status = 'local'
        NODES.add_or_update(NODES.local_node)
        logger.info("local node added, known nodes are: %s", NODES.all_nodes)

        # this is async but we will let it run in background, we have no rush
        self.loop.create_task(probe_docker_daemon())

        # HTTP Daemon. Listen on Unix Socket
        logger.info("Starting Daemon HTTP Server...")
        server = httpserver.HTTPServer(APP)
        logger.info("Listening on unix socket: %s", options.unix_socket)
        socket = bind_unix_socket(options.unix_socket)
        server.add_socket(socket)

        # Also Listen on TCP
        logger.info("Listening on tcp socket: %s:%s", options.listen_address, options.listen_port)
        server.listen(options.listen_port, address=options.listen_address)

        # Register daemon events
        EVENTS.on('node.added', on_new_node_added)
        EVENTS.on('node.removed', on_node_removed)
        EVENTS.on('node.docker.up', on_node_docker_connected)

        EVENTS.on('probe', new_node) # TEMP
        self.discovery.on('discovered', new_node)
        self.discovery.on('undiscovered', removed_node)
        self.discovery.start()

    async def shutdown(self):
        """Graceful shutdown"""
        await self.discovery.stop()
        print("exiting")
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
        signal.signal(signal.SIGINT, self.schedule_shutdown)
        self.loop.create_task(self.main())
        # self.loop.set_debug(True)
        try:
            self.loop.run_forever()
        except Exception as err:
            raise err
        finally:
            self.loop.run_until_complete(self.shutdown())


if __name__ == '__main__':
    THE_DAEMON = BeiranDaemon()
    THE_DAEMON.run()

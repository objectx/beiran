"""
Plugin abstract class for different discovery
service implementations.
"""

import logging
import socket
import sys
import time
from asyncio import get_event_loop
from abc import abstractmethod, ABCMeta
from pyee import EventEmitter
import netifaces


class AbstractBasePlugin(metaclass=ABCMeta):
    """Metaclass for BeiranPlugin modules
    """

    @abstractmethod
    async def init(self):
        """ Init plugin
        """
        pass

    @abstractmethod
    async def start(self):
        """ Start plugin
        """
        pass

    @abstractmethod
    async def stop(self):
        """ Stop plugin
        """
        pass

    @abstractmethod
    async def sync(self, peer):
        """ Sync with another peer
        node object is accessible at peer.node
        """
        pass

    @abstractmethod
    def is_available(self):
        """ Can plugin be utilized by other components
        at the moment of call
        """
        pass


class BasePlugin(AbstractBasePlugin, EventEmitter):  # pylint: disable=too-many-instance-attributes
    """BeiranPlugin with EventEmmiter
    """

    async def init(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def sync(self, peer):
        pass

    def is_available(self):
        pass

    @property
    def status(self):
        """Return plugin status"""
        return self.__status

    @status.setter
    def status(self, value):
        if value == self.__status:
            return self.__status
        self.__status = value
        self.emit('status', value)
        return self.__status

    # todo: remove if we do not need anymore!
    # def get_status(self):
    #     """Get plugin status"""
    #     return self.__status

    def emit(self, event, *args, **kwargs):
        if event != 'new_listener':
            # self.log.debug('[' + self.plugin_type
            # + ':' + self.plugin_name + ':event] ' + event)
            self.log.debug('[%s:%s:event] %s', self.plugin_type, self.plugin_name, event)
        super().emit(event, *args, **kwargs)

    def __init__(self, config):
        """
        Initialization of plugin class with async loop
        """
        super().__init__()
        self.__status = None
        self.api_routes = []
        self.model_list = []
        self.history = None

        self.plugin_name = sys.modules[self.__module__].PLUGIN_NAME
        self.plugin_type = sys.modules[self.__module__].PLUGIN_TYPE
        self.node = config.pop('node')

        if 'logger' in config:
            self.log = config.pop('logger')
        else:
            self.log = logging.getLogger('beiran.plugin.' + self.plugin_name)
            if 'log_handler' in config:
                self.log.addHandler(config.pop('log_handler'))
            else:
                self.log.addHandler(logging.NullHandler())
            if self.log.level == logging.NOTSET:
                self.log.setLevel(logging.WARN)
        self.daemon = config.pop('daemon')
        self.config = config
        self.loop = get_event_loop()
        self.status = 'init'

    def set_log_level(self, level: int):
        """
        Setting log level for plugin classes
        Args:
            level: logging.level
        """
        self.log.level = level


class BaseDiscoveryPlugin(BasePlugin):
    """Discovery Plugin Base
    """

    class DiscoveredNode(object):
        """Beiran node information class"""
        def __init__(self, hostname=None, ip_address=None, port=None):
            self.hostname = hostname
            self.ip_address = ip_address
            self.port = port

        def __str__(self):
            return 'Node: {} Address: {} Port: {}'.format(self.hostname,
                                                          self.ip_address,
                                                          str(self.port))

        def __repr__(self):
            return self.__str__()

    @property
    def network_interface(self):
        """ Gets listen interface for daemon
        """
        if 'interface' in self.config:
            return self.config['interface']

        return netifaces.gateways()['default'][2][1]

    @property
    def port(self):
        """..."""
        if 'port' in self.config:
            return self.config['port']
        return 8888

    @property
    def address(self):
        """ Gets listen address for daemon
        """
        if 'address' in self.config:
            return self.config['address']

        interface = self.get_network_interface()  # todo: fix, no such method pylint: disable=no-member
        return netifaces.ifaddresses(interface)[2][0]['addr']

    @property
    def hostname(self):
        """ Gets hostname for discovery
        """
        if 'hostname' in self.config:
            return self.config['hostname']

        return socket.gethostname()


class BasePackagePlugin(BasePlugin):
    """Base class for package plugins"""
    pass


class History(EventEmitter):
    """Class for keeping update/sync history (of anything)"""

    def __init__(self):
        super().__init__()
        self.version = 0
        self.updated_at = None
        self.updates = []

    def update(self, msg=None):
        """Append update to history and increment the version"""
        self.version += 1
        new_update = {
            "time": time.time(),
            "msg": msg,
            "v": self.version
        }
        self.updated_at = new_update['time']
        self.updates.append(new_update)
        self.emit('update', new_update)

    def updates_since(self, since_time):
        """Return updates since `time`"""
        return [u for u in self.updates if u['time'] >= since_time]

    def delete_before(self, before_time):
        """Delete updates before `time`"""
        self.updates = [u for u in self.updates if u['time'] < before_time]

    @property
    def latest(self):
        """Latest update or None"""
        if not self.updates:
            return None
        return self.updates[-1]

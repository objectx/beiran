"""
Plugin abstract class for different discovery
service implementations.
"""

import logging
import socket
import sys
from asyncio import get_event_loop
from abc import abstractmethod, ABCMeta
from pyee import EventEmitter


class AbstractBeiranPlugin(metaclass=ABCMeta):
    """Metaclass for BeiranPlugin modules
    """

    @abstractmethod
    async def init(self):
        """ 
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


class BeiranPlugin(AbstractBeiranPlugin, EventEmitter):
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
        return self.__status

    @status.setter
    def status(self, value):
        if value == self.__status:
            return
        self.__status = value
        self.emit('status', value)
        return self.__status

    def get_status(self):
        return self.__status

    def emit(self, eventname, *args, **kwargs):
        if eventname != 'new_listener':
            self.log.debug('[' + self.__plugin_type + ':' + self.__plugin_name + ':event] ' + eventname)
        super().emit(eventname, *args, **kwargs)

    def __init__(self, config):
        """
        Initialization of plugin class with async loop
        """
        super().__init__()
        self.__status = None

        self.__plugin_name = sys.modules[self.__module__].PLUGIN_NAME
        self.__plugin_type = sys.modules[self.__module__].PLUGIN_TYPE
        self.node = config['node']

        if 'logger' in config:
            self.log = config['logger']
        else:
            self.log = logging.getLogger(self.__plugin_name)
            if 'log_handler' in config:
                self.log.addHandler(config['log_handler'])
            else:
                self.log.addHandler(logging.NullHandler())
            if self.log.level == logging.NOTSET:
                self.log.setLevel(logging.WARN)
        self.config = config
        self.loop = get_event_loop()

    def set_log_level(self, level: int):
        """
        Setting log level for plugin classes
        Args:
            level: logging.level
        """
        self.log.level = level

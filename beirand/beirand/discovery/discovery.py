"""
Discovery abstract class for different discovery
service implementations.
"""

import logging
import socket
from abc import abstractmethod, ABCMeta
from pyee import EventEmitter


class Node(object):
    """Beiran node information class"""
    def __init__(self, hostname=None, ip_address=None):
        self.hostname = hostname
        self.ip_address = ip_address

    def __str__(self):
        return 'Node: ' + self.hostname + ' Address: ' + self.ip_address

    def __repr__(self):
        return self.__str__()


class AbstractDiscovery(metaclass=ABCMeta):
    """Metaclass for Discovery modules
    """
    @abstractmethod
    def start(self):
        """ Starts discovery service
        """
        pass

    @abstractmethod
    def stop(self):
        """ Unregister service itself and close
        """
        pass

    @abstractmethod
    def list_service(self):
        """ Get already registered services
        Returns:
            tuple: List of services
        """
        pass


class Discovery(AbstractDiscovery, EventEmitter):
    """Discovery with EventEmmiter
    """

    def start(self):
        pass

    def stop(self):
        pass

    def list_service(self):
        pass

    def __init__(self, aioloop):
        """
        Initialization of discovery class with async loop
        Args:
            aioloop: asyncio loop
        """
        super().__init__()
        self.log = logging.getLogger(__name__)
        self.log.addHandler(logging.NullHandler())
        if self.log.level == logging.NOTSET:
            self.log.setLevel(logging.WARN)
        self.host_ip = self.get_host_ip()

        self.loop = aioloop

    def set_log_level(self, level: int):
        """
        Setting log level for discovery classes
        Args:
            level: logging.level
        """
        self.log.level = level

    def get_host_ip(self):
        """ Returns host ip address of current node
        """
        socket_for_host = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_for_host.connect(('google.com', 0))
        host_ip = socket_for_host.getsockname()[0]
        print("ip = " + host_ip)
        return host_ip

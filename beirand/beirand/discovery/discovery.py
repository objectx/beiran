"""
Discovery abstract class for different discovery
service implementations.
"""

import logging
from abc import abstractmethod, ABCMeta


class Discovery(metaclass=ABCMeta):
    """Metaclass for Discovery modules
    """
    def __init__(self, aioloop):
        """
        Initialization of discovery class with async loop
        Args:
            aioloop: asyncio loop
        """
        self.log = logging.getLogger(__name__)
        self.log.addHandler(logging.NullHandler())
        if self.log.level == logging.NOTSET:
            self.log.setLevel(logging.WARN)
        self.loop = aioloop

    def set_log_level(self, level: int):
        """
        Setting log level for discovery classes
        Args:
            level: logging.level
        """
        self.log.level = level

    @abstractmethod
    def start(self):
        """ Starts discovery service
        """
        pass

    @abstractmethod
    def stop(self, zeroconf):
        """ Unregister service itself and close
        Args:
            zeroconf (Zeroconf):

        Returns:
            None:
        """
        pass

    @abstractmethod
    def list_service(self):
        """ Get already registered services
        Returns:
            tuple: List of services
        """
        pass

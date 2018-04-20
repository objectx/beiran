"""
Discovery abstract class for different discovery
service implementations.
"""

import netifaces
import socket
from .base import BeiranPlugin


class BeiranDiscoveryPlugin(BeiranPlugin):
    """Discovery Plugin Base
    """

    class DiscoveredNode(object):
        """Beiran node information class"""
        def __init__(self, hostname=None, ip_address=None, port=None):
            self.hostname = hostname
            self.ip_address = ip_address
            self.port = port

        def __str__(self):
            return 'Node: ' + self.hostname + ' Address: ' + self.ip_address + ' Port: ' + str(self.port)

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

        interface = self.get_network_interface()
        return netifaces.ifaddresses(interface)[2][0]['addr']

    @property
    def hostname(self):
        """ Gets hostname for discovery
        """
        if 'hostname' in self.config:
            return self.config['hostname']

        return socket.gethostname()

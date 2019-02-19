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
Plugin abstract class for different discovery
service implementations.
"""

import logging
import socket
import sys
import time
import pkgutil

from typing import Optional, Union, List, Any # pylint: disable=unused-import
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
    DEFAULTS = {} # type: dict

    def __init__(self, config: dict) -> None:
        """
        Initialization of plugin class with async loop
        """
        super().__init__()
        self.__status = None # type: Optional[str]
        self.api_routes = [] # type: list
        self.model_list = [] # type: list
        self.history = None

        self.plugin_name = sys.modules[self.__module__].PLUGIN_NAME # type: ignore
        self.plugin_type = sys.modules[self.__module__].PLUGIN_TYPE # type: ignore
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
        self.config = self.init_config(config)
        self.loop = get_event_loop()
        self.status = 'init'

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
    def status(self) -> Optional[str]:
        """Return plugin status"""
        return self.__status

    @status.setter
    def status(self, value: str) -> str:
        if value == self.__status:
            return self.__status
        self.__status = value
        self.emit('status', value)
        return self.__status

    # todo: remove if we do not need anymore!
    # def get_status(self):
    #     """Get plugin status"""
    #     return self.__status

    def init_config(self, config: dict):
        """Initialize plugin configuration. Values ​​not in ``config`` are
        set with default values"""
        for key, value in self.DEFAULTS.items():
            config.setdefault(key, value)
        return config

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        if event != 'new_listener':
            # self.log.debug('[' + self.plugin_type
            # + ':' + self.plugin_name + ':event] ' + event)
            self.log.debug('[%s:%s:event] %s', self.plugin_type, self.plugin_name,
                           event)
        super().emit(event, *args, **kwargs)

    def set_log_level(self, level: int) -> None:
        """
        Setting log level for plugin classes
        Args:
            level: logging.level
        """
        self.log.level = level


class BaseDiscoveryPlugin(BasePlugin):
    """Discovery Plugin Base
    """

    class DiscoveredNode:
        """Beiran node information class"""
        def __init__(self, hostname: str = None, ip_address: str = None, port: int = None) -> None:
            self.hostname = hostname
            self.ip_address = ip_address
            self.port = port

        def __str__(self) -> str:
            return 'Node: {} Address: {} Port: {}'.format(self.hostname,
                                                          self.ip_address,
                                                          str(self.port))

        def __repr__(self) -> str:
            return self.__str__()

    @property
    def network_interface(self) -> str:
        """ Gets listen interface for daemon
        """
        if 'interface' in self.config:
            return self.config['interface']

        return netifaces.gateways()['default'][2][1]

    @property
    def port(self) -> int:
        """..."""
        if 'port' in self.config:
            return self.config['port']
        return 8888

    @property
    def address(self) -> str:
        """ Gets listen address for daemon
        """
        if 'address' in self.config:
            return self.config['address']

        interface = self.network_interface
        return netifaces.ifaddresses(interface)[2][0]['addr']

    @property
    def hostname(self) -> str:
        """ Gets hostname for discovery
        """
        if 'hostname' in self.config:
            return self.config['hostname']

        return socket.gethostname()


class BasePackagePlugin(BasePlugin):
    """Base class for package plugins"""
    pass


class BaseInterfacePlugin(BasePlugin):
    """Base class for interface plugins"""
    pass


class History(EventEmitter):
    """Class for keeping update/sync history (of anything)"""

    def __init__(self) -> None:
        super().__init__()
        self.version = 0
        self.updated_at = None # type: Union[float, str, None]
        self.updates = [] # type: list

    def update(self, msg: str = None) -> None:
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

    def updates_since(self, since_time: float) -> List[dict]:
        """Return updates since `time`"""
        return [u for u in self.updates if u['time'] >= since_time]

    def delete_before(self, before_time: float) -> None:
        """Delete updates before `time`"""
        self.updates = [u for u in self.updates if u['time'] < before_time]

    @property
    def latest(self) -> Optional[dict]:
        """Latest update or None"""
        if not self.updates:
            return None
        return self.updates[-1]


def get_installed_plugins() -> List[str]:
    """
    Iterates installed packages and modules to match beiran modules.

    Returns:
        list: list of package name of installed beiran plugins.

    """
    return [
        name
        for finder, name, ispkg
        in pkgutil.iter_modules()
        if name.startswith('beiran_')
    ]

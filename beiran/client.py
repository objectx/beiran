"""
Common client for beiran project
"""
# pylint: disable=duplicate-code

import asyncio
import logging

from typing import Any, Optional # pylint: disable=unused-import

import aiohttp
import async_timeout

from beiran.models import Node
from beiran.models import PeerAddress

class Client:
    """ Beiran Client class
    """
    def __init__(self, peer_address: PeerAddress = None, node: Node = None, version: str = None):
        """
        Initialization method for client
        Args:
            peer_address (PeerAddress): beirand url
            node (Node): Node (optional)
            version (str): string (optional)
        """
        self.node = node
        self.version = node.version if node else version
        self.logger = logging.getLogger('beiran.client')

        if not (peer_address or node):
            raise ValueError("Both node and peer_address can not be None")

        address = peer_address or node.get_latest_connection()

        self.url = address.location

        if address.unix_socket:
            self.client_connector = aiohttp.UnixConnector(path=address.location)
            self.url = address.protocol + '://unixsocket'
        else:
            self.client_connector = None
        self.http_client = None

    async def create_client(self):
        """Create aiohttp client session"""
        self.http_client = aiohttp.ClientSession(connector=self.client_connector)

    async def cleanup(self):
        """Closes aiohttp client session"""
        if self.http_client:
            await self.http_client.close()
            self.http_client = None

    def __del__(self):
        if not self.http_client:
            return

        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(self.cleanup())
        else:
            loop.run_until_complete(self.cleanup())

    class Error(Exception):
        """Base Exception class for Beiran Client operations"""
        def __init__(self, message: str) -> None:
            super().__init__(message)
            self.message = message

    class TimeoutError(Error):
        """..."""
        pass

    class HTTPError(Error):
        """..."""
        def __init__(self, status: int, message: str, **kwargs) -> None:
            super().__init__(message)
            self.status = status
            self.headers = kwargs.pop('headers', None)
            self.history = kwargs.pop('history', None)
            self.request = kwargs.pop('request', None)

    async def request(self, path: str = "/", **kwargs) -> Any:
        """
        Request call to daemon

        Args:
            path: http path to request from daemon
            parse_json (bool): if return value is JSON from daemon,
            return_response (bool): determine if the response returns or not
            data (dict): request payload
            timeout (int): timeout
            raise_error (bool): raising error
            method (str): request method
            it returns parsed JSON

        Returns:
            (dict or str) Response from daemon, dict or json string

        """
        headers = kwargs['headers'] if 'headers' in kwargs else {}

        data = kwargs.pop('data', None)
        if data:
            # kwargs['data'] = json.dumps(data)
            kwargs['json'] = data
            headers['Content-Type'] = 'application/json'

        kwargs['headers'] = headers

        method = kwargs.pop('method', "GET")
        parse_json = kwargs.pop('parse_json', True)

        return_response = kwargs.pop('return_response', False)
        raise_error = kwargs.pop('raise_error', not return_response)

        url = self.url + path
        self.logger.debug("Requesting %s", url)

        try:
            if not self.http_client:
                await self.create_client()

            if 'timeout' in kwargs:
                # raises;
                # asyncio.TimeoutError =? concurrent.futures._base.TimeoutError
                async with async_timeout.timeout(kwargs['timeout']):
                    response = await self.http_client.request(method, url, **kwargs) #type: ignore
            else:
                response = await self.http_client.request(method, url, **kwargs) #type: ignore

            if raise_error:
                # this only raises if status code is >=400
                # raises;
                # aiohttp.HttpProcessingError
                response.raise_for_status()

        except asyncio.TimeoutError as err:
            raise Client.TimeoutError("Timeout")

        except aiohttp.ClientResponseError as err:
            raise Client.HTTPError(err.code, err.message, headers=err.headers,
                                   history=err.history, request=err.request_info)

        if return_response:
            return response

        if parse_json:
            return await response.json()

        return response.content

    async def get_server_info(self, **kwargs) -> dict:
        """
        Gets root path from daemon for server information
        Returns:
            object: parsed from JSON

        """
        return await self.request(path="/", parse_json=True, **kwargs)

    async def get_server_version(self, **kwargs) -> str:
        """
        Daemon version retrieve
        Returns:
            str: semantic version
        """
        return (await self.get_server_info(**kwargs))['version'] # type: ignore

    async def get_node_info(self, uuid: str = None, **kwargs) -> dict:
        """
        Retrieve information about node
        Returns:
            object: info of node
        """
        path = "/info" if not uuid else "/info/{}".format(uuid)
        return await self.request(path=path, parse_json=True, **kwargs)

    async def get_status(self, plugin: str = None, **kwargs) -> dict:
        """
        Retrieve status information about node or one of it's plugins
        Returns:
            object: status of node or plugin
        """
        path = "/status" if not plugin else "/status/plugins/{}".format(plugin)
        return await self.request(path=path, parse_json=True, **kwargs)

    async def ping(self, timeout: int = 10, **kwargs) -> bool:
        """
        Pings the node
        """
        response = await self.request("/ping", return_response=True, timeout=timeout, **kwargs)
        if not response or response.status != 200:
            raise Exception("Failed to receive ping response from node")

        # TODO: Return ping time
        return True

    async def probe_node(self, address: str, probe_back: bool = True, **kwargs) -> dict:
        """
        Connect to a new node
        Returns:
            object: info of node if successful
        """
        path = "/nodes?cmd=probe"
        new_node = {
            "address": address,
            "probe_back": probe_back
        }
        return await self.request(path=path,
                                  data=new_node,
                                  parse_json=True,
                                  method="POST",
                                  **kwargs)

    async def get_nodes(self, all_nodes: bool = False, **kwargs) -> list:
        """
        Daemon get nodes
        Returns:
            list: list of nodes
        """
        path = '/nodes{}'.format('?all=true' if all_nodes else '')

        resp = await self.request(path=path, **kwargs)

        return resp.get('nodes', [])

    async def get_images(self, all_nodes: bool = False, node_uuid: str = None, **kwargs) -> list:
        """
        Get Image list from beiran API
        Returns:
            list: list of images

        """
        if node_uuid and all_nodes:
            raise Exception("node_uuid and all_nodes cannot be defined at the same time")

        path = '/docker/images'

        if node_uuid:
            path = path + '?node={}'.format(node_uuid)
        elif all_nodes:
            path = path + '?all=true'

        resp = await self.request(path=path, **kwargs)
        return resp.get('images', [])

    #pylint: disable-msg=too-many-arguments
    async def pull_image(self, imagename: str, **kwargs) -> aiohttp.client_reqrep.ClientResponse:
        """
        Pull image accross cluster with spesific node support
        Returns:
            result: Pulling process result
        """

        progress = kwargs.pop('progress', False)
        force = kwargs.pop('force', False)
        wait = kwargs.pop('wait', False)
        node = kwargs.pop('node', None)

        path = '/docker/images?cmd=pull'
        data = {
            'image': imagename,
            'node': node,
            'wait': wait,
            'force': force,
            'progress': progress
        }

        resp = await self.request(path,
                                  data=data,
                                  method='POST',
                                  return_response=True,
                                  timeout=600,
                                  **kwargs)
        return resp
    #pylint: enable-msg=too-many-arguments

    async def stream_image(self, imagename: str, **kwargs) -> aiohttp.client_reqrep.ClientResponse:
        """
        Stream image from this node

        Usage::

            image_response = await client.stream_image(image_identifier)
            async for data in image_response.content.iter_chunked(64*1024):
                do something with data chunk
        """

        path = '/docker/images/{}'.format(imagename)

        resp = await self.request(path,
                                  method='GET',
                                  return_response=True,
                                  **kwargs)
        return resp

    async def get_layers(self, all_nodes: bool = False, node_uuid: str = None, **kwargs) -> list:
        """
        Get Layer list from beiran API
        Returns:
            list: list of layers
        """
        if node_uuid and all_nodes:
            raise Exception("node_uuid and all_nodes cannot be defined at the same time")

        path = '/docker/layers'

        if node_uuid:
            path = path + '?node={}'.format(node_uuid)
        elif all_nodes:
            path = path + '?all=true'

        resp = await self.request(path=path, **kwargs)

        return resp.get('layers', [])

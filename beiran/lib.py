"""Beiran Library"""
import aiohttp
import async_timeout


async def async_req(url, timeout=3, method="GET", **kwargs):
    """
    Async http get with aiohttp
    Args:
        url (str): get url
        timeout (int): timeout

    Returns:
        (ClientResponse, dict): response instance, response json

    """

    json = kwargs.pop('json', None)
    data = kwargs.pop('data', None)
    headers = kwargs

    async with aiohttp.ClientSession() as session:
        async with async_timeout.timeout(timeout):
            async with session.request(method, url, json=json,
                                       data=data, headers=headers) as resp:
                response, data = resp, await resp.json(content_type=None)
                return response, data


ADDRESS_FORMAT = "beiran+{protocol}://{hostname}:{port}#{uuid}"

def build_node_address(host, uuid=None, port=8888, protocol="http"):
    """
    Build a node address with given host, port, protocol and uuid

    Args:
        host: hostname
        uuid: uuid of node
        port: service port
        protocol: protocol, default http

    Returns:

    """
    address = ADDRESS_FORMAT.format(host=host, port=port, protocol=protocol, uuid=uuid)
    if not uuid:
        address = address.split('#')[0]

    return address

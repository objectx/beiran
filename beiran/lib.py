"""Beiran Library"""
import aiohttp
import async_timeout

from beiran.util import input_reader

async def async_req(url, return_json=True, timeout=3, method="GET", **kwargs):
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
                if return_json:
                    data = await resp.json(content_type=None)
                    return resp, data
                return resp


async def async_write_file_stream(url, save_path, mode='wb', auth=None, # pylint: disable=too-many-arguments
                                  timeout=3, method="GET", **kwargs):
    """
    Async write a stream to a file
    Args:
        url (str): get url
        save_path (str): path for saving file
        mode (str): file mode
        auth (aiohttp.BasicAuth): configuration of authentication
        timeout (int): timeout

    Returns:

    """
    json = kwargs.pop('json', None)
    data = kwargs.pop('data', None)
    headers = kwargs

    async with aiohttp.ClientSession(auth=auth) as session:
        async with async_timeout.timeout(timeout):
            async with session.request(method, url, json=json,
                                       data=data, headers=headers) as resp:

                with open(save_path, mode)as file:
                    async for chunk in input_reader(resp.content):
                        file.write(chunk)
                return resp

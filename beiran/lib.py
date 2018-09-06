"""Beiran Library"""
from typing import Tuple

import aiohttp
import async_timeout

from beiran.util import input_reader


async def async_req(url: str, return_json: bool = True,
                    timeout: int = 3, method: str = "GET",
                    **kwargs) -> Tuple[aiohttp.client_reqrep.ClientResponse, dict]:
    """
    Async http get with aiohttp
    Args:
        url (str): get url
        return_json (bool): is response json string or not?
        timeout (int): timeout
        method (str): HTTP method

    Returns:
        (ClientResponse, dict): response instance, response json

    """

    json = kwargs.pop('json', None)
    data = kwargs.pop('data', None)
    headers = kwargs

    async with aiohttp.ClientSession() as session: # type: ignore
        async with async_timeout.timeout(timeout):
            async with session.request(method, url, json=json,
                                       data=data, headers=headers) as resp:
                if return_json:
                    data = await resp.json(content_type=None)
                    return resp, data
                return resp


async def async_write_file_stream(url, save_path, mode='wb', timeout=3, method="GET", **kwargs):
    """
    Async write a stream to a file
    Args:
        url (str): get url
        save_path (str): path for saving file
        mode (str): file mode
        timeout (int): timeout
        method (str): HTTP method

    Returns:
        aiohttp.client_reqrep.ClientResponse: request response
    """
    json = kwargs.pop('json', None)
    data = kwargs.pop('data', None)
    headers = kwargs

    async with aiohttp.ClientSession() as session:
        async with async_timeout.timeout(timeout):
            async with session.request(method, url, json=json,
                                       data=data, headers=headers) as resp:

                with open(save_path, mode)as file:
                    async for chunk in input_reader(resp.content):
                        file.write(chunk)
                return resp

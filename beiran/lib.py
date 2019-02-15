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

"""Beiran Library"""
from typing import Tuple

import asyncio
import aiohttp
import async_timeout

from beiran.util import input_reader


async def async_req(url: str, return_json: bool = True, # pylint: disable=too-many-arguments
                    timeout: int = 3, retry: int = 1,
                    retry_interval: int = 2, method: str = "GET",
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

    for _ in range(retry):
        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(timeout):
                    async with session.request(method, url, json=json,
                                               data=data, headers=headers) as resp:
                        if return_json:
                            data = await resp.json(content_type=None)
                            return resp, data
                        return resp, {}
        except asyncio.TimeoutError:
            await asyncio.sleep(retry_interval)
    raise asyncio.TimeoutError

async def async_write_file_stream(url: str, save_path: str, queue=None, # pylint: disable=too-many-arguments,too-many-locals
                                  timeout: int = 3, retry: int = 1,
                                  retry_interval: int = 2, method: str = "GET",
                                  **kwargs) -> aiohttp.client_reqrep.ClientResponse:
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

    for _ in range(retry):
        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(timeout):
                    async with session.request(method, url, json=json,
                                               data=data, headers=headers) as resp:

                        with open(save_path, 'wb')as file:
                            async for chunk in input_reader(resp.content):
                                file.write(chunk)
                                if queue:
                                    queue.put_nowait(chunk)
                        if queue:
                            queue.put_nowait(None)
                        return resp
        except asyncio.TimeoutError:
            await asyncio.sleep(retry_interval)
    raise asyncio.TimeoutError

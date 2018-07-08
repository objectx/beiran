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

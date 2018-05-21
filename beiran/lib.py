"""Beiran Library"""
import aiohttp
import async_timeout


async def async_req(url, timeout=3, method="GET", **headers):
    """
    Async http get with aiohttp
    Args:
        url (str): get url
        timeout (int): timeout

    Returns:
        (ClientResponse, dict): response instance, response json

    """
    async with aiohttp.ClientSession() as session:
        async with async_timeout.timeout(timeout):
            async with session.request(method, url, headers=headers) as resp:
                response, data = resp, await resp.json(content_type=None)
                return response, data

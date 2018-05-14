"""Beiran Library"""
import aiohttp
import async_timeout


async def async_fetch(url, timeout=3, **kwargs):
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
            async with session.get(url, headers=kwargs) as resp:
                response, response = resp, await resp.json()
                return response, response

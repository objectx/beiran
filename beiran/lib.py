"""Beiran Library"""
import aiohttp
import async_timeout

CHUNK_SIZE = 2048


async def async_req(url, timeout=3, method="GET", file_path=False, **kwargs):
    """
    Async http get with aiohttp
    Args:
        url (str): get url
        timeout (int): timeout
        method (str): request method
        download_file_path (str): file path, if we download a file

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
                if not file_path:
                    response, data = resp, await resp.json(content_type=None)
                    return response, data

                with open(file_path, 'wb') as file_handler:

                    while True:
                        chunk = await resp.content.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        file_handler.write(chunk)

                return resp, file_path

import pytest
from beiran.util import parse_subpath, json_streamer


@pytest.mark.parametrize('subpath,result', [
    ('$', [
        {'type': 'root', 'params': None}
    ]),
    ('$.key', [
        {'type': 'root', 'params': None},
        {'type': 'key', 'params': 'key'}
    ]),
    ('$.*', [
        {'type': 'root', 'params': None},
        {'type': 'key', 'params': None}
    ]),
    ('$[:]', [
        {'type': 'root', 'params': None},
        {'type': 'range', 'params': { 'start': 0, 'end': None, 'step': 1}}
    ]),
    ('$[:5]', [
        {'type': 'root', 'params': None},
        {'type': 'range', 'params': { 'start': 0, 'end': 5, 'step': 1}}
    ]),
    ('$[1:]', [
        {'type': 'root', 'params': None},
        {'type': 'range', 'params': { 'start': 1, 'end': None, 'step': 1}}
    ]),
    ('$[3:5]', [
        {'type': 'root', 'params': None},
        {'type': 'range', 'params': {'start': 3, 'end': 5, 'step': 1}}
    ]),
    ('$[::2]', [
        {'type': 'root', 'params': None},
        {'type': 'range', 'params': {'start': 0, 'end': None, 'step': 2}}
    ]),
    ('$[3,5,6]', [
        {'type': 'root', 'params': None},
        {'type': 'range', 'params': [3, 5, 6]}
    ]),
    ('$[5,3,6]', [
        {'type': 'root', 'params': None},
        {'type': 'range', 'params': [3, 5, 6]}
    ])
])
def test_parse_subpath(subpath, result):
    assert parse_subpath(subpath) == result


@pytest.mark.parametrize('string,subpath,result', [
    ('{}', '$', [{}]),
    ('[]', '$', [[]]),
    ('{"key": 123}', '$', [{"key": 123}]),
    ('[1, 2, 3]', '$', [[1, 2, 3]]),
    ('{"ka": 123, "kb": 456}', '$.*', [123, 456]),
    ('[1, 2, 3]', '$[:]', [1, 2, 3]),
    ('[1, 2, 3]', '$[::]', [1, 2, 3]),
    ('{"ka": 123, "kb": 456}', '$.ka', [123]),
    ('{"ka": 123, "kb": 456}', '$.kb', [456]),
    ('[1, 2, 3, 4, 5, 6]', '$[2:]', [3, 4, 5, 6]),
    ('[1, 2, 3, 4, 5, 6]', '$[1:3]', [2, 3]),
    ('[1, 2, 3, 4, 5, 6]', '$[:4]', [1, 2, 3, 4]),
    ('[1, 2, 3, 4, 5, 6]', '$[::2]', [1, 3, 5]),
])
def test_json_streamer(string, subpath, result):
    import asyncio
    
    async def _wrapper(string, subpath):
        import io
        stream = io.BytesIO(string.encode('utf-8'))
        return [v async for v in json_streamer(stream, subpath)]

    async def _main():
        assert await _wrapper(string, subpath) == result

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_main())

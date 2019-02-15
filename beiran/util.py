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

"""
Utilities for beiran project
"""

import sys
import tarfile
import asyncio
import time
import io
import gzip
from typing import Any
from pyee import EventEmitter

class Unbuffered:
    """
    Unbuffered stream write class
    """
    def __init__(self, stream: io.TextIOWrapper) -> None:
        """
        Initialization unbuffered with stream.
        Args:
            stream: any stream to write unbuffered
        """
        self.stream = stream

    def write(self, data: str):
        """
        Write data to stream and flush
        Args:
            data: data to write
        """
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, lines: list):
        """ Write as lines

        Args:
            lines (Array): array of data

        """
        self.stream.writelines(lines)
        self.stream.flush()

    def __getattr__(self, attr: str) -> Any:
        """
        Get a named attribute from an object
        Returns:
            value:
        """
        return getattr(self.stream, attr)


def eprint(*args, **kwargs):
    """
    Printing errors
    Args:
        *args:
        **kwargs:
    """
    print(*args, file=sys.stderr, **kwargs)


def exit_print(exit_code: int, *args, **kwargs):
    """
    Printing exit code
    Args:
        exit_code:
        *args:
        **kwargs:
    """
    print(*args, file=sys.stderr, **kwargs)
    sys.exit(exit_code)


def create_tar_archive(dir_path: str, output_file_path: str):
    """
    create a tar archive from given path

    Args:
        output_file_path: directory path to be saved!
        dir_path (string): directory path to be tarred!

    Returns:


    """
    with tarfile.open(output_file_path, "w") as tar:
        tar.add(dir_path, arcname='.')


async def input_reader(stream, **kwargs):
    """
    input_reder
    """

    if hasattr(stream, 'iter_chunked'):
        async for data in stream.iter_chunked(64*1024):
            yield data
        return

    if hasattr(stream, 'at_eof') and hasattr(stream, 'readchunk'):
        while not stream.at_eof():
            # https://docs.aiohttp.org/en/stable/streams.html#aiohttp.StreamReader.readchunk
            # Retuns [bytes,boolean]
            data = await stream.readchunk()
            yield data
        return

    if isinstance(stream, str):
        yield bytearray(stream, 'utf-8') # at once
        return

    if hasattr(stream, 'read') and hasattr(stream, 'write'):
        chunk_size = kwargs.pop('chunk_size', 1024)
        while True:
            data = stream.read(chunk_size)
            if not data:
                break
            yield data
        return

    raise Exception("Unsupported stream")


def parse_subpath(subpath):
    # pylint: disable=anomalous-backslash-in-string,too-many-branches
    """
    parse subpath:
        This function returns the parsed subpath object.
        subpath object is just a list.

    the regular expression of subpath:
        /\$(\.([\w]+|\*)|\[\d*:\d*:\d*\])*/

    the grammer of subpath:
        subpath        ::= "$" selecter*
        selecter       ::= key_selecter | range_selecter
        key_selecter   ::= "." key_body
        key_body       ::= word* | "*"
        range_selecter ::= "[" range_body "]"
        range_body     ::= int? ":" int? ":" int?

        word           ::= "a" | ... | "z" | "A" | ... | "Z" | digit | "_"
        digit          ::= "0" | ... | "9"

    ref: http://goessner.net/articles/JsonPath
    """

    # pylint: disable=missing-docstring
    def _helper(otype, oparams):
        return {'type': otype, 'params': oparams}

    # pylint: disable=missing-docstring
    def _ext_str(olist, oend):
        ostr = ""
        while olist and not olist[0] in oend:
            ostr += olist.pop(0)
        return ostr

    result = []
    chars = [c for c in subpath]

    if chars.pop(0) != '$':
        raise RuntimeError('subpath is corrupt')
    result.append(_helper('root', None))

    while chars:
        char = chars.pop(0)
        if char == '.':
            if chars[0] == '*':
                chars.pop(0)
                result.append(_helper('key', None))
            else:
                result.append(_helper('key', _ext_str(chars, ".[")))
        elif char == '[':
            string = _ext_str(chars, ":,")
            if chars[0] == ':':
                start = int(string) if string else 0
                chars.pop(0)

                string = _ext_str(chars, ":]")
                end = int(string) if string else None

                if chars.pop(0) == ':':
                    string = _ext_str(chars, "]")
                    step = int(string) if string else 1
                    chars.pop(0)
                else:
                    step = 1

                result.append(_helper('range', {
                    'start': start,
                    'end': end,
                    'step': step
                }))
            elif chars[0] == ',':
                tlist = [int(string)]
                while chars.pop(0) != ']':
                    tlist.append(int(_ext_str(chars, ',]')))
                result.append(_helper('range', sorted(tlist)))
            else:
                raise RuntimeError('subpath is corrupt')
        else:
            raise RuntimeError('subpath is corrupt')

    return result


async def json_streamer(stream, subpath="$"):
    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Parse a stream of JSON chunks"""
    from jsonstreamer import JSONStreamer

    queue = []
    def _catch_all(event, *args):
        queue.append((event, args))

    streamer = JSONStreamer()
    streamer.add_catch_all_listener(_catch_all)
    rules = parse_subpath(subpath)

    keys = [None]
    values = []
    depth = 0


    def _judge(key, rule):
        rtype, rparams = rule['type'], rule['params']

        if rtype == 'root':
            return True
        if rtype == 'key':
            if rparams is None:
                return True
            if rparams == key:
                return True
        if rtype == 'range':
            if isinstance(rparams, list):
                if key in rparams:
                    return True
            if isinstance(rparams, dict):
                if rparams['start'] <= key:
                    if rparams['end'] is None or key < rparams['end']:
                        if (key - rparams['start']) % rparams['step'] == 0:
                            return True
        return False

    async for data in input_reader(stream):
        streamer.consume(data.decode("utf-8"))
        while queue:
            event, args = queue.pop(0)
            pop_flag = False

            if event in ['doc_start', 'doc_end']:
                pass

            if event == 'object_start':
                depth += 1
                values.append({})
            if event == 'array_start':
                depth += 1
                values.append([])
                keys.append(0)

            if event == 'object_end':
                pop_flag = True
            if event == 'array_end':
                keys.pop()
                pop_flag = True

            if event == 'key':
                keys.append(args[0])

            if event == 'value':
                depth += 1
                values.append(args[0])
                pop_flag = True

            if event == 'element':
                depth += 1
                values.append(args[0])
                pop_flag = True

            if pop_flag:
                flag = len(rules) == depth
                val = values.pop()

                if flag and all(_judge(*elem) for elem in zip(keys, rules)):
                    yield val

                if values and isinstance(values[-1], dict):
                    key = keys.pop()
                    values[-1][key] = val
                elif values and isinstance(values[-1], list):
                    key = keys.pop()
                    values[-1].append(val)
                    keys.append(key + 1)
                depth -= 1


def sizeof_fmt(num, suffix='B'):
    """Human readable format for sizes
    source: https://stackoverflow.com/a/1094933
    """
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def wait_task_result(task):
    """
    Blocks thread until given task has finished, and returns the
    result value of the task
    """
    # FIXME! This is a bad way to do this.
    # Not sure if there is a good way.
    while not task.done():
        time.sleep(.1)
    return task.result()


def run_in_loop(coroutine, loop=None, sync=False):
    """
    Runs given coroutine in the given or default asyncio loop.
    Returns Task object is sync if False.
    If sync is True, blocks the thread and returns the task's result.
    """

    if not loop:
        loop = asyncio.get_event_loop()
    task = loop.create_task(coroutine)
    if not sync:
        return task
    return wait_task_result(task)


async def wait_event(emitter, event_name, timeout=None):
    """Wait until emitter is emitted"""
    # TODO: timeout
    future = asyncio.Future()

    def _handler(*args, **kwargs):
        future.set_result({"args": args, **kwargs})

    emitter.once(event_name, _handler)
    return await asyncio.wait_for(future, timeout)

def gunzip(path: str) -> None:
    """Decompress .gz file"""
    with gzip.open(path, 'rb') as gzfile:
        data = gzfile.read()
        path = path.rstrip('.gz')

        with open(path, "wb") as tarf:
            tarf.write(data)

def clean_keys(dict_: dict, keys: list) -> None:
    """Remove keys from the dictionary"""
    for key in keys:
        if key in dict_:
            del dict_[key]

async def until_event(emitter: EventEmitter, name: str, error_event: Optional[str]=None, loop=asyncio.get_event_loop()):
    """Wait task until triggered the event"""
    future: asyncio.Future = asyncio.Future(loop=loop)

    # not consider to duplicate registrations of event
    emitter.once(name, lambda **kw: future.set_result(kw))
    if error_event:
        emitter.once(error_event, lambda err: future.set_exception(err))

    await future

async def until_event_with_match(emitter: EventEmitter, name: str, error_event: Optional[str]=None, cond: dict, loop=asyncio.get_event_loop()):
    """Wait task until triggered the event"""

    while True:
        values = await until_event(emitter, name, error_event=error_event, loop=loop)
        matching = True
        for k, v in dict:
            if k not in values:
                matching = False
                break
            if v != values[k]:
                matching = False
                break
        if matching:
            return values

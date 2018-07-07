"""
Utilities for beiran project
"""

import sys
import tarfile


class Unbuffered(object):
    """
    Unbuffered stream write class
    """
    def __init__(self, stream):
        """
        Initialization unbuffered with stream.
        Args:
            stream: any stream to write unbuffered
        """
        self.stream = stream

    def write(self, data):
        """
        Write data to stream and flush
        Args:
            data: data to write
        """
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, lines):
        """ Write as lines

        Args:
            lines (Array): array of data

        """
        self.stream.writelines(lines)
        self.stream.flush()

    def __getattr__(self, attr):
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


def exit_print(exit_code, *args, **kwargs):
    """
    Printing exit code
    Args:
        exit_code:
        *args:
        **kwargs:
    """
    print(*args, file=sys.stderr, **kwargs)
    sys.exit(exit_code)


def create_tar_archive(dir_path, output_file_path):
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
    async def tornado_input_reader(stream):
        while not stream.at_eof():
            data = await stream.readchunk()
            yield data

    if hasattr(stream, 'iter_chunked'):
        async for data in stream.iter_chunked(64*1024):
            yield data
        return

    if hasattr(stream, 'at_eof') and hasattr(stream, 'readchunk'):
        async for data in tornado_input_reader(stream):
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
    def _helper(t, a):
        return { 'type': t, 'args': a }

    def _ext_str(l, e):
        s = ""
        while l and not l[0] in e:
            s += l.pop(0)
        return s

    result = []
    chars = [c for c in subpath]

    if chars.pop(0) != '$':
        raise RuntimeError('subpath is corrupt')
    result.append(_helper('root', None))

    while chars:
        c = chars.pop(0)
        if c == '.':
            if chars[0] == '*':
                chars.pop(0)
                result.append(_helper('key', None))
            else:
                result.append(_helper('key', _ext_str(chars, ".[")))
        elif c == '[':
            t = _ext_str(chars, ":,")
            if chars[0] == ':':
                start = int(t) if t else 0
                chars.pop(0)

                t = _ext_str(chars, ":]")
                end = int(t) if t else None

                if chars.pop(0) == ':':
                    t = _ext_str(chars, "]")
                    step = int(t) if t else 1
                    chars.pop(0)
                else:
                    step = 1

                result.append(_helper('range', {
                        'start': start,
                        'end': end,
                        'step': step
                    }))
            elif chars[0] == ',':
                l = [int(t)]
                while chars.pop(0) != ']':
                    l.append(int(_ext_str(chars, ',]')))
                result.append(_helper('range', sorted(l)))
            else:
                raise RuntimeError('subpath is corrupt')
        else:
            raise RuntimeError('subpath is corrupt')

    return result


async def json_streamer(stream, subpath="$"):
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
        if rule['type'] == 'root':
            return True
        if rule['type'] == 'key':
            if rule['args'] is None:
                return True
            if rule['args'] == key:
                return True
        if rule['type'] == 'range':
            if type(rule['args']) is list:
                if key in rule['args']:
                    return True
            if type(rule['args']) is dict:
                args = rule['args']
                if args['start'] <= key:
                    if args['end'] is None or key < args['end']:
                        if (key - args['start']) % args['step'] == 0:
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

                if values and type(values[-1]) is dict:
                    key = keys.pop()
                    values[-1][key] = val
                elif values and type(values[-1]) is list:
                    key = keys.pop()
                    values[-1].append(val)
                    keys.append(key + 1)
                
                depth -= 1
                
    stream.close()


def test_parser():
    assert parse_subpath('$') == [
            { 'type': 'root', 'args': None }
            ]

    assert parse_subpath('$.key') == [
            { 'type': 'root', 'args': None },
            { 'type': 'key', 'args': 'key' }
            ]

    assert parse_subpath('$.*') == [
            { 'type': 'root', 'args': None },
            { 'type': 'key', 'args': None }
            ]

    assert parse_subpath('$[:]') == [
            { 'type': 'root', 'args': None },
            { 'type': 'range', 'args': { 'start': 0, 'end': None, 'step': 1 } }
            ]

    assert parse_subpath('$[:5]') == [
            { 'type': 'root', 'args': None },
            { 'type': 'range', 'args': { 'start': 0, 'end': 5, 'step': 1 } }
            ]

    assert parse_subpath('$[1:]') == [
            { 'type': 'root', 'args': None },
            { 'type': 'range', 'args': { 'start': 1, 'end': None, 'step': 1 } }
            ]

    assert parse_subpath('$[3:5]') == [
            { 'type': 'root', 'args': None },
            { 'type': 'range', 'args': { 'start': 3, 'end': 5, 'step': 1 } }
            ]

    assert parse_subpath('$[3:11:2]') == [
            { 'type': 'root', 'args': None },
            { 'type': 'range', 'args': { 'start': 3, 'end': 11, 'step': 2 } }
            ]

    assert parse_subpath('$[3,5,6]') == [
            { 'type': 'root', 'args': None },
            { 'type': 'range', 'args': [3, 5, 6] }
            ]

    assert parse_subpath('$[5,3,6]') == [
            { 'type': 'root', 'args': None },
            { 'type': 'range', 'args': [3, 5, 6] }
            ]


def test_json():
    import asyncio
    import io
    
    async def _wrapper(json, subpath):
        stream = io.BytesIO(json.encode('utf-8'))
        return [v async for v in json_streamer(stream, subpath)]

    async def _main():
        import io

        print('- vacant dict')
        assert await _wrapper('{}', '$') == [{}]
        print('- vacant list')
        assert await _wrapper('[]', '$') == [[]]

        print('- dict + no subpath')
        assert await _wrapper('{"key": 123}', '$') == [{"key": 123}]
        print('- array + no subpath')
        assert await _wrapper('[1, 2, 3]', '$') == [[1, 2, 3]]

        print('- dict + asterisk')
        assert await _wrapper('{"key_a": 123, "key_b": 456}', '$.*') == [123, 456]

        print('- array + slice(all) part1')
        assert await _wrapper('[1, 2, 3]', '$[:]') == [1, 2, 3]
        print('- array + slice(all) part2')
        assert await _wrapper('[1, 2, 3]', '$[::]') == [1, 2, 3]

        print('- dict + simple subpath')
        assert await _wrapper('{"key_a": 123, "key_b": 456}', '$.key_a') == [123]
        print('- array + slice part1')
        assert await _wrapper('[1, 2, 3, 4, 5, 6]', '$[2:]') == [3, 4, 5, 6]
        print('- array + slice part2')
        assert await _wrapper('[1, 2, 3, 4, 5, 6]', '$[1:3]') == [2, 3]
        print('- array + slice part3')
        assert await _wrapper('[1, 2, 3, 4, 5, 6]', '$[:4]') == [1, 2, 3, 4]
        print('- array + slice part4')
        assert await _wrapper('[1, 2, 3, 4, 5, 6]', '$[::2]') == [1, 3, 5]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_main())


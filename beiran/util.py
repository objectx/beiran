"""
Utilities for beiran project
"""

import sys
import tarfile


class Unbuffered:
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

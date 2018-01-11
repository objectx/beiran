import sys

class Unbuffered(object):
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def writelines(self, datas):
        self.stream.writelines(datas)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def exit_print(exit_code, *args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    sys.exit(exit_code)

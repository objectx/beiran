"""Beiran multiple progressbar"""
import sys
from itertools import count
import progressbar

class MultipleProgressBar(progressbar.ProgressBar): # pylint: disable=too-many-ancestors
    """This class realizes display of multiple progress bars"""
    _position = count(0)

    def __init__(self, *args, finish_immediately=True, **kwargs):
        self.position = next(self._position)
        self.finish_immediately = finish_immediately

        if 'widgets' not in kwargs and 'desc' in kwargs:
            widgets = [
                kwargs['desc'] + ' ', progressbar.Percentage(), ' ', progressbar.Bar(),
                ' ', progressbar.ETA(), ' ', progressbar.FileTransferSpeed()
            ]
        super().__init__(
            widgets=widgets, maxval=100, *args, **kwargs
        )

    @classmethod
    def cursor_up(cls):
        """Up the cursor"""
        sys.stdout.write('\x1b[1A')
        sys.stdout.flush()

    @classmethod
    def cursor_down(cls):
        """Down the cursor"""
        sys.stdout.write('\n')
        sys.stdout.flush()

    @classmethod
    def seek(cls, lastpos, newpos):
        """Seek the cursor from last position to new position"""
        if lastpos > newpos:
            for _ in range(lastpos - newpos):
                cls.cursor_up()
        elif lastpos < newpos:
            for _ in range(newpos - lastpos):
                cls.cursor_down()

    def update_and_seek(self, value, lastpos):
        """Update position of cursor and progressbar's value"""
        self.seek(lastpos, self.position)
        self.update(value)
        if self.finish_immediately and self.value == self.max_value:
            self.finish()
            return self.position + 1
        return self.position

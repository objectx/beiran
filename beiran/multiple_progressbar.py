"""Beiran multiple progressbar"""
import sys, progressbar
from itertools import count

class MultipleProgressBar(progressbar.ProgressBar):
    """This class realizes display of multiple progress bars"""
    _position = count(0)

    def __init__(self, finish_immediately=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.position = next(self._position)
        self.finish_immediately = finish_immediately

    @classmethod
    def up(cls):
        """Up the cursor"""
        sys.stdout.write('\x1b[1A')
        sys.stdout.flush()

    @classmethod
    def down(cls):
        """Down the cursor"""
        sys.stdout.write('\n')
        sys.stdout.flush()

    @classmethod
    def seek(cls, lastpos, newpos):
        """Seek the cursor from last position to new position"""
        if lastpos > newpos:
            for _ in range(lastpos - newpos):
                cls.up()
        elif lastpos < newpos:
            for _ in range(newpos - lastpos):
                cls.down()
    
    def update_and_seek(self, value, lastpos):
        """Update position of cursor and progressbar's value"""
        self.seek(lastpos, self.position)
        self.update(value)
        if self.finish_immediately and self.value == self.max_value:
            self.finish()
            return self.position + 1
        return self.position

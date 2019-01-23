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

"""Beiran multiple progressbar"""
import sys
from itertools import count
import progressbar

class ProgressbarValues:
    """All progressbars share the values"""
    prevpos = 0
    exist_bars = [] # type: list

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
        ProgressbarValues.exist_bars.append(self)

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
    def seek_by_manual(cls, prevpos, newpos):
        """Seek the cursor from previous position to new position (manual)"""
        if prevpos > newpos:
            for _ in range(prevpos - newpos):
                cls.cursor_up()
        elif prevpos < newpos:
            for _ in range(newpos - prevpos):
                cls.cursor_down()

    def seek(self):
        """Seek the cursor from previous position to new position"""
        if ProgressbarValues.prevpos > self.position:
            for _ in range(ProgressbarValues.prevpos - self.position):
                self.cursor_up()
        elif ProgressbarValues.prevpos < self.position:
            for _ in range(self.position - ProgressbarValues.prevpos):
                self.cursor_down()

    def seek_last_line(self):
        """Seek cursor to the end of set of progress bars.
        Don't run this function in 'update_and_seek'. Because there is a possibility of
        executing this before the elements of set of progressbars are all gathered.
        """
        if ProgressbarValues.exist_bars == []:
            lastpos = next(self._position)
            for _ in range(lastpos - self.position - 1):
                self.cursor_down()

    def update_and_seek(self, value):
        """Update position of cursor and progressbar's value"""
        self.seek()
        self.update(value)
        if self.finish_immediately and self.value == self.max_value:
            self.finish()
            ProgressbarValues.exist_bars.remove(self)
            ProgressbarValues.prevpos = self.position + 1
        else:
            ProgressbarValues.prevpos = self.position

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

import pytest


from beiran.util import wait_event
from pyee import EventEmitter
import asyncio

@pytest.mark.timeout(0.3)
def test_wait_event():
	my_emitter = EventEmitter()
	loop = asyncio.get_event_loop()

	async def test():
	    loop.create_task(test2())
	    event_args = await wait_event(my_emitter, "hello")
	    assert event_args['args'][0] == 'from test'
	    assert event_args['abc'] == 'hello'

	async def test2():
	    await asyncio.sleep(0.1)
	    my_emitter.emit('hello', "from test", 5, True, abc="hello")

	loop.run_until_complete(test())

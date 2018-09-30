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

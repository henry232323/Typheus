import asyncio
from phue import Bridge
import time

async def change(b, num, light):
    b.set_light(int(num), {'transitiontime': 30, 'on': True, 'bri': 254})
    await asyncio.sleep(3)
    b.set_light(num, 'bri', 0, transitiontime=30)
    b.set_light(num, 'on', False)

async def main():
    b = Bridge("10.0.1.4")
    b.connect()
    a = b.get_api()
    for num, light in a['lights'].items():
        #if not light['state']['on']:
        if num == '4':
            b.set_light(int(num), 'on', False)
            for x in range(5):
                asyncio.ensure_future(change(b, int(num), light))

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.run_forever()
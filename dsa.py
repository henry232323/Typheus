import aiohttp
import asyncio
import urllib.request
import re

async def go():
    with open("dave.txt", 'w+') as e:
        for i in range(1939, 10200):
            with urllib.request.urlopen('http://www.mspaintadventures.com/?s=6&p={}'.format(str(i).zfill(6))) as response:
               html = response.read()

            a = re.findall(r'<span style="color: #e00707">TG: (.*)</span>', html.decode())
            print(i, len(a), "found")
            b = "\n".join(a)
            e.write(b)

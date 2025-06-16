import websockets
from websockets.asyncio.server import serve
import asyncio
import time

print("server is starting")
Bullets = []


async def hs(server):
    async for message in server:
        if message != 'hello':
            await server.send(message)
async def main():
    async with serve(hs, "localhost", 3000) as server:
        await server.serve_forever()

asyncio.run(main())

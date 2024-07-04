import asyncio
from asyncio.proactor_events import _ProactorSocketTransport


class EchoClientProtocol(asyncio.Protocol):
    def __init__(self, message: bytes, on_con_lost: asyncio.Future):
        self.message: bytes = message
        self.on_con_lost: asyncio.Future = on_con_lost

    def connection_made(self, transport: _ProactorSocketTransport):
        print('Connected to server')
        loop = asyncio.get_running_loop()
        loop.create_task(cli(transport))
        transport.write(self.message)

    def data_received(self, data):
        print(f'Data received: {data.decode()}')

    def connection_lost(self, exc):
        print('The server closed the connection')
        self.on_con_lost.set_result(True)

async def ainput(prompt: str = "") -> str:
    return await asyncio.to_thread(input, prompt)

async def cli(transport: _ProactorSocketTransport):
    while True:
        data: str = await ainput('> ')
        print(f'Sending data: {data}')
        transport.write(data.encode())


async def main():
    # Get a reference to the event loop as we plan to use
    # low-level APIs.
    loop = asyncio.get_running_loop()
    on_con_lost: asyncio.Future = loop.create_future()
    message = 'Hello World!'

    transport, protocol = await loop.create_connection(
        lambda: EchoClientProtocol(message.encode(), on_con_lost),
        '127.0.0.1', 8087)

    # Wait until the protocol signals that the connection
    # is lost and close the transport.
    try:
        await on_con_lost
    finally:
        transport.close()


asyncio.run(main())
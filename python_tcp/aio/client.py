import asyncio
from event import Event
from loguru import logger


async def ainput(prompt: str = "") -> str:
    return await asyncio.to_thread(input, prompt)

async def cli(transport: asyncio.StreamWriter):
    while True:
        data: str = await ainput('> ')
        print(f'Sending data: {data}')
        transport.write(data.encode())
        await transport.drain()


class SocketClient():
    def __init__(self, host: str, port: int) -> None:
        self.received = Event(bytes)
        self.transmited = Event(bytes)
        self.disconnected = Event()
        self.connected = Event()
        self.error = Event(Exception)
        self._host: str = host
        self._port: int = port
        self._running_flag = False
        # self.transport: asyncio.Transport
        self._connection_status: bool = False
        self.writer: asyncio.StreamWriter
        self.reader: asyncio.StreamReader

    async def _read_routine(self):
        while self._running_flag:
            data: bytes = await self.reader.read(1024)
            if not data:
                logger.warning('Got empty data')
                break
            logger.debug(f'Received: {data}')
            self.received.emit(data)

    async def connect(self) -> bool:
        if self._connection_status:
            return True
        # self._running_flag = True
        # while self._running_flag:
        try:
            self.reader, self.writer = await asyncio.open_connection(self._host, self._port)
            self._connection_status = True
            self._running_flag = True
            logger.success(f'Connected to server {self._host}:{self._port}')
            loop = asyncio.get_running_loop()
            loop.create_task(self._read_routine())
            self.connected.emit()
            return True
        except ConnectionRefusedError as err:
            logger.debug(err)
            self.error.emit(err)
            return False

    async def disconnect(self) -> None:
        if self._running_flag:
            self._connection_status = False
            self._running_flag = False
            self.writer.close()
            await self.writer.wait_closed()
            logger.debug('Disconnected from server')
            self.disconnected.emit()

    async def send(self, data: bytes) -> None:
        if self._connection_status:
            try:
                self.writer.write(data)
                await self.writer.drain()
                self.transmited.emit(data)
            except ConnectionError:
                logger.debug("Client suddenly closed, cannot send")
                await self.disconnect()
        else:
            logger.warning('Not connected to server')


# if __name__ == '__main__':
#     client = SocketClient('localhost', 8087)
#     asyncio.run(client.routine())
#     loop = asyncio.get_running_loop()
#     loop.create_task(cli(client.writer))
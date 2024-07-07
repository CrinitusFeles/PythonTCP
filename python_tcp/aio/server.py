import asyncio
from asyncio import start_server, Server, StreamWriter
from dataclasses import dataclass
from event import Event
from loguru import logger


@dataclass
class ReceivedData:
    sock: asyncio.StreamWriter
    msg: bytes


class SocketServer:
    def __init__(self, host: str, port: int) -> None:
        self.host: str = host
        self.port: int = port
        self.transmited: Event = Event(bytes)
        self.received: Event = Event(ReceivedData)
        self.client_disconnected: Event = Event(tuple)
        self.client_connected: Event = Event(tuple)
        self._server: asyncio.Server
        self.clients: dict[str, list[StreamWriter]] = {}

    async def start_server(self) -> None:
        self._server: Server = await start_server(self.handler, self.host,
                                                  self.port)
        async with self._server:
            logger.info(f'KPA Gateway server listening at '\
                         f'{self.host}:{self.port}')
            await self._server.serve_forever()

    async def handler(self, reader: asyncio.StreamReader,
                      writer: asyncio.StreamWriter) -> None:
        addr: tuple[str, int] = writer.get_extra_info("peername")
        self.clients.setdefault(addr[0], []).append(writer)
        self.client_connected.emit(addr)
        logger.debug(f"Connected by {addr}")
        while True:
            try:
                data: bytes = await reader.read(1024)
                if not data:
                    logger.warning(f'Got empty data from {addr}')
                    break
                logger.debug(f'from {addr} got msg: {data}')
                self.received.emit(ReceivedData(writer, data))
            except ConnectionError:
                logger.debug(f"Client suddenly closed while receiving from {addr}")
                break
        self._disconnection_handler(writer)

    def _disconnection_handler(self, writer: StreamWriter) -> None:
        addr: tuple[str, int] = writer.get_extra_info("peername")
        writer.close()
        self.client_disconnected.emit(addr)
        del self.clients[addr[0]]
        logger.debug(f"Disconnected by {addr}")

    def get_connected_clients(self):
        return self.clients

    async def send_to_client(self, client_ip: str, data: bytes) -> None:
        client: list[StreamWriter] | None = self.clients.get(client_ip, None)
        if client:
            for sock in client:
                try:
                    sock.write(data)
                    await sock.drain()
                except ConnectionError:
                    logger.debug("Client suddenly closed, cannot send")
                    self._disconnection_handler(sock)
        else:
            logger.error(f'Client {client_ip} not connected')

    def broadcast(self, data: bytes) -> None:
        for ip, sock_list in self.clients.items():
            [client.write(data) for client in sock_list]

    # def send(self, data: bytes) -> None:
    #     self._tx_queue.put(data)

if __name__ == '__main__':
    server = SocketServer('localhost', 8087)
    asyncio.run(server.start_server())
from dataclasses import dataclass
from queue import Empty, Queue
import selectors
import socket
from threading import Thread
from loguru import logger
from event.event import Event

EVENTS = list[tuple[selectors.SelectorKey, int]]

@dataclass
class ReceivedData:
    sock: socket.socket
    msg: bytes

class SocketServer:
    def __init__(self, port: int) -> None:
        self.received: Event = Event(ReceivedData)
        self.transmited: Event = Event(bytes)
        self.connected: Event = Event(dict)
        self.disconnected: Event = Event(str)
        self.label: str = ''
        self._host: str = '0.0.0.0'
        self._port: int = port
        self._socket: socket.socket | None = None
        self._selector = selectors.DefaultSelector()
        self._thread: Thread
        self._handler_thread: Thread
        self._running_flag = False
        self._tx_queue = Queue()
        self._rx_queue = Queue()
        self._run_status: bool = False
        self._handlers: dict = {selectors.EVENT_READ: self._read_handler,
                                selectors.EVENT_WRITE: self._write_handler}
        self.clients: dict[str, list[socket.socket]] = {}

    def is_running(self) -> bool:
        return self._run_status

    def send_to_client(self, client_ip: str, data: bytes) -> None:
        client_socks: list[socket.socket] | None = self.clients.get(client_ip,
                                                                    None)
        if client_socks:
            [sock.send(data) for sock in client_socks]
        else:
            logger.error(f'Client {client_ip} not connected')

    def broadcast(self, data: bytes) -> None:
        for sock_list in self.clients.values():
            [client.send(data) for client in sock_list if client.fileno()]

    def send(self, data: bytes) -> None:
        self._tx_queue.put(data)

    def _rx_routine(self) -> None:
        while self._running_flag:
            data: ReceivedData = self._rx_queue.get()
            self.received.emit(data)

    def _read_handler(self, sock: socket.socket) -> bool:
        try:
            data: bytes = sock.recv(1024)
            if not data:
                logger.debug("Disconnected by", sock.getpeername())
                return False
            self._rx_queue.put_nowait(ReceivedData(sock, data))
            logger.debug(f'received: {data.hex(" ").upper()}')
        except ConnectionResetError:
            logger.debug("Client disconnected")
            return False
        except ConnectionError:
            logger.debug("Client suddenly closed while receiving")
            del self.clients[sock.getpeername()[0]]
            return False
        return True

    def _write_handler(self, sock: socket.socket) -> bool:
        try:
            data: bytes = self._tx_queue.get_nowait()
            sock.send(data)
            logger.debug(f'sended: {data.hex(" ").upper()}')
        except Empty:
            pass
        except ConnectionError:
            logger.debug("Client suddenly closed while receiving")
            del self.clients[sock.getpeername()[0]]
            return False
        return True

    def _accept_connection(self, sel: selectors.SelectSelector,
                           serv_sock: socket.socket, mask: int) -> None:
        client: tuple[socket.socket, tuple[str, int]] = serv_sock.accept()
        client_sock: socket.socket = client[0]
        addr: tuple[str, int] = client[1]
        logger.debug(f"Connected client {addr}")
        sel.register(client_sock, selectors.EVENT_READ | selectors.EVENT_WRITE,
                     self._selector_ready)
        self.clients.setdefault(addr[0], []).append(client_sock)
        self.connected.emit({addr[0]: client_sock})

    def _selector_ready(self, sel: selectors.SelectSelector,
                        sock: socket.socket, mask: int) -> None:
        def lost_connection_handler(sock: socket.socket) -> None:
            for ip, sock_obj in self.clients.items():
                if sock in sock_obj:
                    sock_obj.remove(sock)
                    if not len(sock_obj):
                        logger.debug(f'Client { ip } disconnected')
                        self.disconnected.emit(ip)
            logger.debug('Client disconnected')
            sel.unregister(sock)
            sock.close()

        is_read: int = mask & selectors.EVENT_READ
        is_write: int = mask & selectors.EVENT_WRITE
        if is_write:
            if not self._write_handler(sock):
                lost_connection_handler(sock)
        if is_read:
            if not self._read_handler(sock):
                lost_connection_handler(sock)
        if not is_read and not is_write:
            lost_connection_handler(sock)

    def _run(self) -> None:
        """Starts the server and accepts connections indefinitely."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self._host, self._port))
        self._socket.listen()
        self._selector.register(self._socket, selectors.EVENT_READ,
                                self._accept_connection)
        logger.info(f'Starting server at {self._host}:{self._port}')
        while self._running_flag:
            events: EVENTS = self._selector.select()
            for key, mask in events:
                callback = key.data
                callback(self._selector, key.fileobj, mask)

    def start_server(self) -> None:
        if not self._running_flag:
            self._thread = Thread(name=f'{self.label}_server_thread',
                                  target=self._run, daemon=True)
            self._handler_thread = Thread(name=f'{self.label}_rx_thread',
                                          target=self._rx_routine, daemon=True)
            self._running_flag = True
            self._thread.start()
            self._handler_thread.start()
        else:
            logger.warning('Server is already running')
        self._run_status = True

    def stop(self) -> None:
        if self._running_flag:
            self._running_flag = False
            self._thread.join(0.2)
            self._handler_thread.join(0.2)
        else:
            logger.error('Server is not running')
        self._run_status = False


if __name__ == "__main__":
    import sys
    port: int = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    server = SocketServer(port)
    server.start_server()
    server.received.subscribe(lambda data: print(data.msg.hex(' ').upper()))
    try:
        while True:
            in_data: str = input('<')
            server.broadcast(in_data.encode())
    except KeyboardInterrupt:
        server.stop()
        print('shutdown')

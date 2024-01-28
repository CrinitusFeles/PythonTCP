# import time
import socket
from threading import Thread
import time

from loguru import logger

from event.event import Event

class SocketClient:

    def __init__(self, host: str, port: int) -> None:
        self.received = Event(bytes)
        self.transmited = Event(bytes)
        self.disconnected = Event()
        self.connected = Event()
        self._host: str = host
        self._port: int = port
        self._socket: socket.socket
        self._running_flag = False
        self._thread: Thread
        self._connection_status: bool = False

    def _routine(self) -> None:
        try:
            while self._running_flag:
                msg: bytes = self._socket.recv(1024)
                if not msg:
                    break
                logger.debug(f"< {msg}")
                self.received.emit(msg)
                time.sleep(0.1)
        except ConnectionResetError as err:
            logger.error(f'Lost connection with server: {err}')
        except ConnectionAbortedError:
            logger.info('Disconnected from server')
            return None
        logger.info('Lost connection with server. Trying to reconnect.')
        self.disconnect()
        self.connect()

    def _connect_routine(self) -> bool:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._socket.connect((self._host, self._port))
            self._connection_status = True
            logger.success(f'Connected to server {self._host}:{self._port}')
            self.connected.emit()
        except ConnectionRefusedError:
            logger.error(f'Can not connect to {self._host}:{self._port}. '\
                         f'Trying to reconect')
            return False
        except ConnectionResetError as err:
            logger.error(f'\nLost connection with server: {err}')
            self.disconnect()
            return False

        self._running_flag = True
        self._thread = Thread(target=self._routine, daemon=True)
        self._thread.start()
        return True

    def connect(self) -> bool:
        while not self._connect_routine():
            time.sleep(1)
        return True

    def disconnect(self) -> None:
        if self._running_flag:
            self._connection_status = False
            self._running_flag = False
            time.sleep(0.2)
            self._socket.close()
            self.disconnected.emit()

    def send(self, data: bytes) -> None:
        if self._connection_status:
            self._socket.send(data)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        host, port = sys.argv[1], int(sys.argv[2])
    else:
        host, port = "localhost", 7777
    client = SocketClient(host, port)
    try:
        client.connect()
        while True:
            in_data: str = input('>')
            client.send(in_data.encode())
    except KeyboardInterrupt:
        client.disconnect()
        print('shutdown')

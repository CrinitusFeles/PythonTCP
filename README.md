# PythonTCP
Python socket client and server examples


## Installation

```sh
poetry add git+https://github.com/CrinitusFeles/PythonTCP.git
```

or

```sh
pip install git+https://github.com/CrinitusFeles/PythonTCP.git
```

## Client

Run:
``` sh
python -m python_tcp.client <HOST_IP> <PORT_NUM>
```
You should see something like this:

```
Connected to server localhost:7777
```
If HOST_IP or PORT_NUM is incorrect you will see:
```
Can not connect to localhost:7772. Trying to reconect
```
> **NOTE!** Client will be trying to reconnect every second while you do not terminate it with *CTRL-C*

You can susbscribe on next events:

* received: bytes
* transmited: bytes
* disconnected: None
* connected: None

```python

def my_handler(data: bytes):
    print(data)

if __name__ == "__main__":
    client = SocketClient("localhost", 7777)
    client.received.subscribe(my_handler)
    client.transmited.subscribe(my_handler)
    client.connected.subscribe(lambda: print('Connected'))
    client.disconnected.subscribe(lambda: print('Discnnected'))
    try:
        client.connect()
        while True:
            in_data: str = input('>')
            client.send(in_data.encode())
    except KeyboardInterrupt:
        client.disconnect()
        print('shutdown')
```

## Server

Run:

```sh
python -m python_tcp.server <PORT_NUM>
```

If you choose port num e.x. 6000, you should see next output:

```
Starting server at 0.0.0.0:6000
```

After that you can connect to server.

Server module has next events on which you can subscribe:

* received: _ReceivedData_
* transmited: _bytes_
* connected: _dict_
* disconnected : _str_

```python
@dataclass
class ReceivedData:
    sock: socket.socket
    msg: bytes
```

>**Note!** To get received data from `received` event you need to call `.msg` attribute.
> <br>E.x.: `server.received.subscribe(lambda data: print(data.msg))`
> <br>This could be usefull when you need to destinguish data from several clients and send answer to socket from which was obtained data.

```python
from python_tcp.server import SocketServer

def my_handler(data):
    print(data)

if __name__ == '__main__':
    server = SocketServer(5555)
    server.start_server()
    server.connected.subscribe(my_handler)
    server.disconnected.subscribe(my_handler)
    server.received.subscribe(my_handler)
    server.transmited.subscribe(my_handler)
    try:
        while True:
            in_data: str = input('<')
            server.broadcast(in_data.encode())
    except KeyboardInterrupt:
        server.stop()
        print('shutdown')
```
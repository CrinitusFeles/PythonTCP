from python_tcp.server import SocketServer

if __name__ == '__main__':
    server = SocketServer(5555)
    server.start_server()
    try:
        while True:
            in_data: str = input('<')
            server.broadcast(in_data.encode())
    except KeyboardInterrupt:
        server.stop()
        print('shutdown')
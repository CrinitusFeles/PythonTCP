from ast import literal_eval
import asyncio


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr: tuple[str, int] = writer.get_extra_info("peername")
    print("Connected by", addr)
    while True:
        try:
            data = await reader.read(1024)
        except ConnectionError:
            print(f"Client suddenly closed while receiving from {addr}")
            break
        if not data:
            break
        print(f'got request: {data}')
        try:
            writer.write(data)
            await writer.drain()
        except ConnectionError:
            print("Client suddenly closed, cannot send")
            break
    writer.close()
    print("Disconnected by", addr)

async def run_server():
    server: asyncio.Server = await asyncio.start_server(handle_client, 'localhost', 8087)
    async with server:
        print('start server')
        await server.serve_forever()

asyncio.run(run_server())
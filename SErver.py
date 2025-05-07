import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import threading
import time

app = FastAPI()

clients = {}  # client_id -> ClientConnection

# Use this queue for passing commands from the thread to the asyncio world.
command_queue = asyncio.Queue()

class ClientConnection:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def send_command(self, command: str):
        await self.websocket.send_text(command)

    async def run(self):
        try:
            while True:
                # Receive output from client (command response)
                try:
                    output = await asyncio.wait_for(self.websocket.receive_text(), timeout=0.1)
                    print(f"\n[Output from client] {output}\n")
                except asyncio.TimeoutError:
                    pass
        except WebSocketDisconnect:
            print(f"Client disconnected")
            return


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    connection = ClientConnection(websocket)
    clients[client_id] = connection
    print(f"Client '{client_id}' connected.")

    await connection.run()

    clients.pop(client_id, None)
    print(f"Client '{client_id}' disconnected.")


def command_input_thread():
    """
    This runs in a background thread to collect user input.
    It sends commands into the asyncio queue for processing.
    """
    while True:
        inp = input("Enter command (<client_id> <command>): ").strip()
        parts = inp.split(" ", 1)
        if len(parts) == 2:
            client_id, command = parts
            asyncio.run_coroutine_threadsafe(command_queue.put((client_id, command)), loop)
        else:
            print("Invalid format. Use: <client_id> <command>")


async def process_command_queue():
    """
    This coroutine runs in the asyncio event loop.
    It reads commands from the queue and sends them to the correct client.
    """
    while True:
        client_id, command = await command_queue.get()
        if client_id in clients:
            await clients[client_id].send_command(command)
        else:
            print(f"Client '{client_id}' not connected.")


async def main():
    global loop
    loop = asyncio.get_event_loop()

    # Start background thread for command input
    threading.Thread(target=command_input_thread, daemon=True).start()

    # Start processing command queue in the asyncio event loop
    asyncio.create_task(process_command_queue())

    # Run FastAPI server
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)

    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())


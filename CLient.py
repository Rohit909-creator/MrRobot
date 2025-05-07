import asyncio
import sys
import subprocess
import websockets

async def run_client(client_id: str, server_uri: str):
    uri = f"{server_uri.rstrip('/')}/ws/{client_id}"
    async with websockets.connect(uri) as websocket:
        print(f"Connected to server at {uri}")

        while True:
            try:
                # Wait for a command from the server
                command = await websocket.recv()
                print(f"Executing command: {command}")

                # Execute the command
                try:
                    output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError as e:
                    output = e.output

                output = output.decode('utf-8', errors='ignore').strip()
                if not output:
                    output = "No output"

                # Send back result
                await websocket.send(output)

            except websockets.ConnectionClosed:
                print("Disconnected from server.")
                break

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python client.py <client_id> <server_ws_url>")
        print("Example: python client.py laptop1 ws://192.168.1.7:8000")
        sys.exit(1)

    client_id = sys.argv[1]
    server_uri = sys.argv[2]

    asyncio.run(run_client(client_id, server_uri))

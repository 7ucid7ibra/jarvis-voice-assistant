#!/usr/bin/env python3

import asyncio
import json
import websockets

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJiODE1NmJhNTk4ZjE0NWRiYjZhMmY4ZTQ1NDQ4YWUyYiIsImlhdCI6MTc2NzgzNTIxOSwiZXhwIjoyMDgzMTk1MjE5fQ.-wYSGq29UBh_5GgUAeVLF9y-b6RDHFlLqRtyrvdq5qk"
WS_URL = "ws://192.168.178.34:8123/api/websocket"

async def subscribe_entities():
    async with websockets.connect(WS_URL) as websocket:
        # Authenticate
        auth_msg = json.dumps({"type": "auth", "access_token": TOKEN})
        await websocket.send(auth_msg)
        response = await websocket.recv()
        print(f"Auth response: {response}")

        # Subscribe to entities
        sub_msg = json.dumps({"id": 5, "type": "subscribe_entities"})
        await websocket.send(sub_msg)
        response = await websocket.recv()
        print(f"Subscribe entities response: {response}")

        # Listen for updates
        try:
            for _ in range(10):
                update = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                print(f"Entity update: {update}")
        except asyncio.TimeoutError:
            print("No more updates")

asyncio.run(subscribe_entities())
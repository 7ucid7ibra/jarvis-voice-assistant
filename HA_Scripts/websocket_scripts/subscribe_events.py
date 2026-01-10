#!/usr/bin/env python3

import asyncio
import json
import websockets

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJiODE1NmJhNTk4ZjE0NWRiYjZhMmY4ZTQ1NDQ4YWUyYiIsImlhdCI6MTc2NzgzNTIxOSwiZXhwIjoyMDgzMTk1MjE5fQ.-wYSGq29UBh_5GgUAeVLF9y-b6RDHFlLqRtyrvdq5qk"
WS_URL = "ws://192.168.178.34:8123/api/websocket"

async def subscribe_events():
    async with websockets.connect(WS_URL) as websocket:
        # Authenticate
        auth_msg = json.dumps({"type": "auth", "access_token": TOKEN})
        await websocket.send(auth_msg)
        response = await websocket.recv()
        print(f"Auth response: {response}")

        # Subscribe to events
        sub_msg = json.dumps({"id": 1, "type": "subscribe_events"})
        await websocket.send(sub_msg)
        response = await websocket.recv()
        print(f"Subscribe response: {response}")

        # Listen for events (for demo, listen for 10 seconds)
        try:
            for _ in range(10):
                event = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                print(f"Event: {event}")
        except asyncio.TimeoutError:
            print("No more events in timeout")

asyncio.run(subscribe_events())
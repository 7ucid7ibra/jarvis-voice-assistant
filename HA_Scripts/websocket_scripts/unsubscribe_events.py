#!/usr/bin/env python3

import asyncio
import json
import websockets

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJiODE1NmJhNTk4ZjE0NWRiYjZhMmY4ZTQ1NDQ4YWUyYiIsImlhdCI6MTc2NzgzNTIxOSwiZXhwIjoyMDgzMTk1MjE5fQ.-wYSGq29UBh_5GgUAeVLF9y-b6RDHFlLqRtyrvdq5qk"
WS_URL = "ws://192.168.178.34:8123/api/websocket"

async def unsubscribe_events():
    async with websockets.connect(WS_URL) as websocket:
        # Authenticate
        auth_msg = json.dumps({"type": "auth", "access_token": TOKEN})
        await websocket.send(auth_msg)
        response = await websocket.recv()
        print(f"Auth response: {response}")

        # Assume subscription id 1, unsubscribe
        unsub_msg = json.dumps({"id": 9, "type": "unsubscribe_events", "subscription": 1})
        await websocket.send(unsub_msg)
        response = await websocket.recv()
        print(f"Unsubscribe response: {response}")

asyncio.run(unsubscribe_events())
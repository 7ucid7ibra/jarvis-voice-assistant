#!/usr/bin/env python3

import asyncio
import json
import websockets

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJiODE1NmJhNTk4ZjE0NWRiYjZhMmY4ZTQ1NDQ4YWUyYiIsImlhdCI6MTc2NzgzNTIxOSwiZXhwIjoyMDgzMTk1MjE5fQ.-wYSGq29UBh_5GgUAeVLF9y-b6RDHFlLqRtyrvdq5qk"
WS_URL = "ws://192.168.178.34:8123/api/websocket"

async def fire_event_ws(event_type, data):
    async with websockets.connect(WS_URL) as websocket:
        # Authenticate
        auth_msg = json.dumps({"type": "auth", "access_token": TOKEN})
        await websocket.send(auth_msg)
        response = await websocket.recv()
        print(f"Auth response: {response}")

        # Fire event
        event_msg = json.dumps({
            "id": 4,
            "type": "fire_event",
            "event_type": event_type,
            "event_data": json.loads(data) if data else {}
        })
        await websocket.send(event_msg)
        response = await websocket.recv()
        print(f"Fire event response: {response}")

if __name__ == "__main__":
    import sys
    event_type = sys.argv[1]
    data = sys.argv[2] if len(sys.argv) > 2 else "{}"
    asyncio.run(fire_event_ws(event_type, data))
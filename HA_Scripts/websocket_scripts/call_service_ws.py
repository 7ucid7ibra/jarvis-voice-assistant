#!/usr/bin/env python3

import asyncio
import json
import websockets
import sys

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJiODE1NmJhNTk4ZjE0NWRiYjZhMmY4ZTQ1NDQ4YWUyYiIsImlhdCI6MTc2NzgzNTIxOSwiZXhwIjoyMDgzMTk1MjE5fQ.-wYSGq29UBh_5GgUAeVLF9y-b6RDHFlLqRtyrvdq5qk"
WS_URL = "ws://192.168.178.34:8123/api/websocket"

async def call_service_ws(domain, service, data):
    async with websockets.connect(WS_URL) as websocket:
        # Authenticate
        auth_msg = json.dumps({"type": "auth", "access_token": TOKEN})
        await websocket.send(auth_msg)
        response = await websocket.recv()
        print(f"Auth response: {response}")

        # Call service
        call_msg = json.dumps({
            "id": 2,
            "type": "call_service",
            "domain": domain,
            "service": service,
            "service_data": json.loads(data) if data else {}
        })
        await websocket.send(call_msg)
        response = await websocket.recv()
        print(f"Service call response: {response}")

if __name__ == "__main__":
    domain = sys.argv[1]
    service = sys.argv[2]
    data = sys.argv[3] if len(sys.argv) > 3 else "{}"
    asyncio.run(call_service_ws(domain, service, data))
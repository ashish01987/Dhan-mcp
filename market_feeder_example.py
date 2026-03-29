#!/usr/bin/env python3
"""
Market Feeder Example - Real-time Market Data Broadcasting
Demonstrates how multiple clients receive live ticks automatically
"""

import asyncio
import websockets
import json
from datetime import datetime


class MarketClient:
    """A market data client that subscribes to live ticks"""

    def __init__(self, client_id: int, security_id: str):
        self.client_id = client_id
        self.security_id = security_id
        self.ws = None
        self.running = False

    async def connect(self, uri: str = "ws://localhost:3005/market"):
        """Connect to market feed WebSocket"""
        try:
            self.ws = await websockets.connect(uri)
            self.running = True
            print(f"[Client {self.client_id}] Connected to {uri}")

            # Subscribe to market data
            await self.subscribe()

            # Listen for ticks
            await self.listen()

        except Exception as e:
            print(f"[Client {self.client_id}] Error: {e}")
        finally:
            self.running = False

    async def subscribe(self):
        """Subscribe to a security's market data"""
        msg = {
            "action": "subscribe",
            "security_id": self.security_id,
            "exchange": "NSE",
            "mode": "Ticker"
        }
        await self.ws.send(json.dumps(msg))
        print(f"[Client {self.client_id}] Subscribed to {self.security_id}")

    async def listen(self):
        """Listen for incoming market ticks"""
        try:
            async for msg in self.ws:
                data = json.loads(msg)
                await self.on_tick(data)
        except websockets.exceptions.ConnectionClosed:
            print(f"[Client {self.client_id}] Connection closed")

    async def on_tick(self, data: dict):
        """Handle incoming tick data"""
        tick_type = data.get("type")

        if tick_type == "latest_tick":
            print(f"[Client {self.client_id}] Latest tick: {data['data']}")

        elif tick_type == "tick":
            tick_data = data.get("data", {})
            ltp = tick_data.get("ltp", "N/A")
            bid = tick_data.get("bid", "N/A")
            ask = tick_data.get("ask", "N/A")
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            print(
                f"[Client {self.client_id}] {timestamp} | "
                f"LTP: {ltp} | Bid: {bid} | Ask: {ask}"
            )

        else:
            print(f"[Client {self.client_id}] {data}")

    async def unsubscribe(self):
        """Unsubscribe from market data"""
        msg = {"action": "unsubscribe", "security_id": self.security_id}
        await self.ws.send(json.dumps(msg))
        print(f"[Client {self.client_id}] Unsubscribed from {self.security_id}")

    async def ping(self):
        """Send ping to keep connection alive"""
        msg = {"action": "ping"}
        await self.ws.send(json.dumps(msg))


async def example_single_client():
    """Example 1: Single client subscribing to RELIANCE (NSE:1333)"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Single Client Subscribing to Market Data")
    print("="*60)

    client = MarketClient(client_id=1, security_id="1333")  # RELIANCE

    # Run for 10 seconds then stop
    try:
        task = asyncio.create_task(client.connect())
        await asyncio.sleep(10)
        await client.unsubscribe()
        await client.ws.close()
    except asyncio.CancelledError:
        pass


async def example_multiple_clients():
    """Example 2: Multiple clients subscribing to same security (auto-broadcast)"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Multiple Clients Auto-Broadcast")
    print("="*60)
    print("3 clients subscribing to RELIANCE (1333)")
    print("All 3 receive the SAME ticks automatically\n")

    # Create 3 clients for the same security
    clients = [
        MarketClient(client_id=1, security_id="1333"),  # RELIANCE
        MarketClient(client_id=2, security_id="1333"),  # RELIANCE
        MarketClient(client_id=3, security_id="1333"),  # RELIANCE
    ]

    # Connect all clients concurrently
    tasks = [asyncio.create_task(client.connect()) for client in clients]

    # Run for 15 seconds
    await asyncio.sleep(15)

    # Clean up
    for client in clients:
        try:
            await client.unsubscribe()
            await client.ws.close()
        except:
            pass


async def example_multiple_securities():
    """Example 3: Multiple clients subscribing to different securities"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Multiple Securities")
    print("="*60)
    print("Client 1: RELIANCE (1333)")
    print("Client 2: TCS (3)")
    print("Client 3: INFOSYS (2880)\n")

    clients = [
        MarketClient(client_id=1, security_id="1333"),   # RELIANCE
        MarketClient(client_id=2, security_id="3"),      # TCS
        MarketClient(client_id=3, security_id="2880"),   # INFOSYS
    ]

    # Connect all clients concurrently
    tasks = [asyncio.create_task(client.connect()) for client in clients]

    # Run for 20 seconds
    await asyncio.sleep(20)

    # Clean up
    for client in clients:
        try:
            await client.unsubscribe()
            await client.ws.close()
        except:
            pass


async def example_dynamic_subscribe():
    """Example 4: Dynamically subscribe/unsubscribe to multiple securities"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Dynamic Subscribe/Unsubscribe")
    print("="*60)

    client = MarketClient(client_id=1, security_id="1333")

    async def manage_subscriptions():
        """Subscribe to different securities over time"""
        securities = [
            ("1333", 5),   # RELIANCE for 5 sec
            ("3", 5),      # TCS for 5 sec
            ("2880", 5),   # INFOSYS for 5 sec
        ]

        await asyncio.sleep(2)  # Wait for initial connection

        for security_id, duration in securities:
            print(f"\n[Dynamic] Switching to {security_id}")
            await client.unsubscribe()

            # Update security and resubscribe
            client.security_id = security_id
            await client.subscribe()

            await asyncio.sleep(duration)

        await client.unsubscribe()
        await client.ws.close()

    try:
        await asyncio.gather(
            client.connect(),
            manage_subscriptions(),
            return_exceptions=True
        )
    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Run examples"""
    print("\n" + "█"*60)
    print("█ Dhan Market Feeder - Auto-Broadcast Examples")
    print("█"*60)

    choice = input(
        "\nSelect example:\n"
        "1. Single Client\n"
        "2. Multiple Clients (Same Security - Auto-Broadcast)\n"
        "3. Multiple Securities\n"
        "4. Dynamic Subscribe/Unsubscribe\n"
        "5. Run All\n"
        "Enter choice (1-5): "
    )

    if choice == "1":
        await example_single_client()
    elif choice == "2":
        await example_multiple_clients()
    elif choice == "3":
        await example_multiple_securities()
    elif choice == "4":
        await example_dynamic_subscribe()
    elif choice == "5":
        await example_single_client()
        await example_multiple_clients()
        await example_multiple_securities()
        await example_dynamic_subscribe()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())

from collections import deque

import anyio

# Typing imports.
from anyio.abc import UDPSocket
from typing import Any, Optional, Callable


class _Server:
    """Represents a UDP server.

    It can be iterated over to receive packets.
    Packets will be decoded with ``_Server.decode(packet)``.
    """
    def __init__(self):
        # Public attributes.
        self.encode: Callable[[Any], bytes] = lambda x: x
        self.decode: Callable[[bytes], Any] = lambda x: x

        # Private internal variables.
        self._socket: Optional[UDPSocket] = None
        self._address: Optional[tuple[str, int]] = None
        self._in_queue: deque[tuple[Any, tuple[str, int]]] = deque()  # Incoming packets.
        self._out_queue: deque[tuple[tuple[str, int], Any]] = deque()  # Outgoing packets.
        self.tick_func: Callable = lambda: None  # The main server tick function.
        self.game_state: dict = {}  # The main game state to send to all the clients every tick.
        self.clients: set[tuple[str, int]] = set()  # Keep track of the clients currently connected.

    @property
    def address(self) -> Optional[tuple[str, int]]:
        """The address of the server as a tuple of ``host``, ``port``."""
        return self._address

    async def _sendto(self, address: tuple[str, int], packet: Any):
        """The internal coroutine in charge of actually sending the packet."""
        await self._socket.sendto(self.encode(packet), *address)

    def sendto(self, address: tuple[str, int], packet: Any):
        """Queue a packet to be sent to the given client.

        The packet will be encoded with ``_Server.encode(packet)``.
        """
        self._out_queue.append((address, packet))

    def sendall(self, packet: Any):
        """Queue a packet to be sent to all the currently registered clients."""
        for address in self.clients:
            self._out_queue.append((address, packet))

    async def _recv_loop(self):
        """The task responsible for receiving packets."""
        async for packet, address in self._socket:
            self._in_queue.append((self.decode(packet), address))

    def __iter__(self):
        return self

    def __next__(self) -> tuple[Any, tuple[str, int]]:
        if self._in_queue:
            return self._in_queue.popleft()
        else:
            raise StopIteration

    async def _server_tick(self):
        """The task responsible for ticking the server and sending out packets to the clients."""
        while True:
            # Do one server tick.
            self.tick_func()
            await anyio.sleep(0)
            # Send updated game state to the clients.
            for address in self.clients:
                await self._sendto(address, self.game_state)
            # Send client specific events.
            for address, packet in self._out_queue:
                await self._sendto(address, packet)
            # Clear the outgoing queue to prepare for the next tick.
            self._out_queue.clear()

    def run(self, host: str, port: int, tick_func: Callable):
        """Start the server on the given network address and use ``tick_func`` as a server tick.

        This function blocks until an error is thrown.
        To manually shut down the server from outside, use a keyboard interrupt with ^C.
        """
        async def main():
            # Create the server socket.
            async with await anyio.create_udp_socket(local_host=host, local_port=port) as socket:
                # Assign internal variables.
                self._socket = socket
                self._address = host, port
                self.tick_func = tick_func
                async with anyio.create_task_group() as tg:
                    # Run all of these tasks in parallel.
                    tg.start_soon(self._recv_loop, name="Receive Loop")  # noqa
                    tg.start_soon(self._server_tick, name="Server Tick")  # noqa
        # Enter the async loop.
        anyio.run(main)  # noqa


# Grant outside access to the server.
server = _Server()

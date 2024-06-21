from collections import deque

import anyio

# Typing imports.
from typing import Callable, Awaitable, Optional, Any
from anyio.abc import ConnectedUDPSocket, CancelScope


class _Connection:
    """Represents a remote connection to a server.

    It can be iterated over to receive packets.
    Packets will be decoded with ``_Connection.decode(packet)``.
    """
    def __init__(self):
        # Public attributes.
        self.encode: Callable[[Any], bytes] = lambda x: x
        self.decode: Callable[[bytes], Any] = lambda x: x

        # Private variables.
        self._socket: Optional[ConnectedUDPSocket] = None
        self._address: tuple[Optional[str], Optional[int]] = None, None  # The remote address connected to.
        self._out_queue: deque[bytes] = deque()  # Outgoing packets.
        self._in_queue: deque[bytes] = deque()  # Incoming packets.
        # Reference to the cancel scope of the task group to allow shutdown.
        self._cancel_scope: Optional[CancelScope] = None

        # Internal flag variables to determine requested socket state.
        self._close: bool = False  # Flag set when connection closing is requested.
        self._connect_address: Optional[tuple[str, int]] = None  # Flag set when new connection is requested.

    @property
    def address(self) -> tuple[Optional[str], Optional[int]]:
        """The address connected to as a tuple of ``host``, ``port``.

        Returns ``(None,None)`` if the connection is closed or not running.
        To connect to a new remote address, use ``Connection.connect(host,port)``.
        """
        return self._address

    @property
    def closed(self) -> bool:
        """Whether the connection is closed. Returns ``True`` if not running.

        A closed connection won't receive any packets and will silently swallow any sent packets.
        To connect to a remote address, use ``Connection.connect(host,port)``.
        """
        return self._socket is None

    async def _close_socket(self):
        """Close the socket if open and update internal variables."""
        if not self.closed:
            await self._socket.aclose()
            # Update state variables.
            self._socket = None
            self._address = None, None
            # Clear queues to remove leftover packets.
            self._out_queue.clear()
            self._in_queue.clear()

    async def _socket_loop(self):
        """The task responsible for opening and closing the connection."""
        while True:
            # Connection closing has been requested.
            if self._close:
                self._close = False
                await self._close_socket()
            # Connection opening has been requested.
            if self._connect_address is not None:
                # We must trigger anyio.ClosedResourceError in _send_loop and _recv_loop,
                # to clear references to the old self._socket.
                # Without this code, the old socket will linger and no new packets will be received.
                await self._close_socket()
                # Create new socket.
                self._socket = await anyio.create_connected_udp_socket(*self._connect_address)
                # Update state variables.
                self._address = self._connect_address
                self._connect_address = None
            # Yield to other tasks.
            await anyio.sleep(0)

    def connect(self, host: str, port: int):
        """Connect to a new remote address.

        If currently connected to a remote address, close that connection and connect to the new address.

        If the connection isn't running, it will connect when ``Connection.run`` is called.
        """
        self._connect_address = host, port

    def close(self):
        """Close the current connection.

        A closed connection won't receive any packets and will silently swallow any sent packets.
        To connect to a remote address, use ``Connection.connect(host,port)``.

        Does nothing if the connection is closed or not running.
        """
        self._close = True

    async def _send_loop(self):
        """The task responsible for sending packets."""
        while True:
            try:
                if not self.closed and self._out_queue:
                    # As long as there are packets, send them out.
                    await self._socket.send(self._out_queue.popleft())
                else:
                    # Yield to other tasks.
                    await anyio.sleep(0)
            except anyio.ClosedResourceError:
                # This is triggered whenever the socket is closed.
                pass

    async def _recv_loop(self):
        """The task responsible for receiving packets."""
        while True:
            try:
                if not self.closed:
                    # Enter an infinite loop of waiting for packets.
                    # This is terminated by anyio.ClosedResourceError when the socket is closed.
                    async for packet in self._socket:
                        self._in_queue.append(packet)
                else:
                    # Yield to other tasks.
                    await anyio.sleep(0)
            except anyio.ClosedResourceError:
                # This is triggered whenever the socket is closed.
                pass

    def send(self, packet: Any):
        """Queue packet to be sent to the connected address.

        If the connection is closed or not running, nothing is queued.
        The packet will be encoded with ``_Connection.encode(packet)``.
        """
        if not self.closed:
            self._out_queue.append(self.encode(packet))

    def __iter__(self):
        return self

    def __next__(self) -> Any:
        if self._in_queue:
            return self.decode(self._in_queue.popleft())
        else:
            raise StopIteration

    async def pump(self, clear_packets: bool = False):
        """Pump the network connection.

        Should be called often while running to allow network events to occur.
        Optionally clear the received packet queue if not clearing it through iteration.
        """
        if clear_packets:
            self._in_queue.clear()
        await anyio.sleep(0)

    def run(self, coroutine: Callable[..., Awaitable], *args, address: Optional[tuple[str, int]] = None):
        """Run ``coroutine`` in a network aware context.

        This function blocks until ``Connection.shutdown()`` is called from ``coroutine``.
        ``Connection.running`` is ``True`` inside of this function and ``False`` outside of it.
        An address can be given, which will be connected to as soon as possible.
        """
        # Set flag to connect to the address as soon as possible.
        self._connect_address = address

        async def main():
            async with anyio.create_task_group() as tg:
                # Keep track of the cancel scope for easy shutdown later.
                self._cancel_scope = tg.cancel_scope
                # Run all of these tasks in parallel.
                tg.start_soon(self._socket_loop, name="Socket Loop")  # noqa
                tg.start_soon(self._send_loop, name="Send Loop")  # noqa
                tg.start_soon(self._recv_loop, name="Receive Loop")  # noqa
                tg.start_soon(coroutine, *args, name="Application Loop")
            # Clean up by closing the socket.
            await self._close_socket()
        # Enter the async loop.
        anyio.run(main)  # noqa

    def shutdown(self):
        """Terminate the network processes and cause ``Connection.run`` to return.

        This function does nothing if the connection isn't running.
        """
        if self._cancel_scope:
            self._cancel_scope.cancel()
            self._cancel_scope = None

    @property
    def running(self) -> bool:
        """Whether the connection is running.

        Check ``Connection.closed`` to see if the connection is connected to a remote address.
        """
        return self._cancel_scope is not None


# Grant outside access to the connection.
connection = _Connection()

from enum import IntEnum, auto

__all__ = (
    "HOST",
    "PORT",
    "SCREEN_SIZE",
    "Event",
    "PLAYER_RADIUS",
    "INITIAL_GAME_STATE",
)

# This file holds variables used by both the client and the server.

HOST = "127.0.0.1"
PORT = 12345

SCREEN_SIZE = (800, 600)

PLAYER_RADIUS = 20


# This enumeration keeps track of all the different event types that can be sent back and forth.
class Event(IntEnum):
    JOIN = auto()
    JOINED = auto()
    UPDATE = auto()
    MOVE = auto()


# The game state held by the server as the source of truth.
# Clients must yield to the server's view of the world.
INITIAL_GAME_STATE = {
    "event": Event.UPDATE,  # This marker is for the clients so they can properly handle this being sent.
    "player_dicts": {},  # Dict of player attributes, like position and name.
}

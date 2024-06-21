#!/usr/bin/env python3
# -*- coding: utf8 -*-

import json
import random

from server import server

from settings import *

# This dictionary maps client addresses to player ids.
client_ids: dict[tuple[str, int], int] = {}


def spawn_point() -> tuple[int, int]:
    """Generate a random point within the screen bounds for spawning players in."""
    return random.randrange(SCREEN_SIZE[0]), random.randrange(SCREEN_SIZE[1])


def game_tick():
    """This function reads in packets and updates clients and game state."""
    for packet, address in server:
        # Get the player id of the address, setting it if unknown.
        client_id = client_ids.setdefault(address, len(client_ids))
        # The player wants to join the server.
        if packet["event"] == Event.JOIN:
            print(f"Client {client_id} \"{packet["name"]}\" joined from {address}")
            # Add the client to the server's list, so it receives game state updates.
            server.clients.add(address)
            # Add a new player dictionary to the game state.
            server.game_state["player_dicts"][client_id] = {"name": packet["name"], "position": (0, 0)}
            # Send a reply to the client letting them know their id and position.
            server.sendto(address, {"event": Event.JOINED, "id": client_id, "position": spawn_point()})
        # The player has moved.
        if packet["event"] == Event.MOVE:
            # Record the new position in the game state.
            server.game_state["player_dicts"][client_id]["position"] = packet["position"]


if __name__ == '__main__':
    # Set up the server to use json as a codec.
    server.encode = lambda x: bytes(json.dumps(x), "utf8")
    server.decode = lambda x: json.loads(x)
    # Give the server an initial game state.
    server.game_state = INITIAL_GAME_STATE
    print(f"Server started on {HOST}:{PORT}")
    try:
        # Run the server on the server address until terminated by an exception.
        server.run(HOST, PORT, game_tick)
    except KeyboardInterrupt as exc:
        print("Server terminated by ^C.")
    else:
        print("Server shut down.")

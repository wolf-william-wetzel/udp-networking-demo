#!/usr/bin/env python3
# -*- coding: utf8 -*-

import json

import pygame as pg

from client import connection

from settings import *

PLAYER_SPEED = 100


async def game_loop():
    # Set up pygame variables.
    pg.display.set_caption("UDP Client")
    screen = pg.display.set_mode(SCREEN_SIZE)
    clock = pg.time.Clock()
    font = pg.font.Font(size=24)

    # Set up variables in an initial state before we are connected to the server.
    player_pos = [SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2]
    game_state = INITIAL_GAME_STATE
    player_id = None

    # Wait until we are connected to the server.
    while connection.closed:
        await connection.pump()

    # Ask to join the server.
    connection.send({"event": Event.JOIN, "name": username})

    # Enter the main application loop.
    while True:
        # Get the delta time in seconds.
        dt = clock.tick() / 1000
        # Yield to network events.
        await connection.pump()

        # Handle incoming packets.
        for packet in connection:
            # The server accepted our join request.
            if packet["event"] == Event.JOINED:
                # Save the player id and the position.
                player_id = packet["id"]
                player_pos = packet["position"]
            # The server has sent out an update of the game world.
            if packet["event"] == Event.UPDATE:
                # Only handle this if we have a valid ID, and it is registered in the game state.
                # Sometimes we receive packets out of order.
                if player_id is not None:
                    game_state = packet
                    if player_id in game_state["player_dicts"]:
                        # Get the new position of the player.
                        player_pos = game_state["player_dicts"][player_id]["position"]

        # Handle pygame events.
        for event in pg.event.get():
            if event.type == pg.QUIT:
                connection.shutdown()  # Terminate connection to server immediately.
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    connection.shutdown()  # Terminate connection to server immediately.

        # Move the player in a frame-independent way, wrapping around the screen.
        if pg.key.get_pressed()[pg.K_RIGHT]:
            player_pos[0] += PLAYER_SPEED * dt
            player_pos[0] %= SCREEN_SIZE[0]
        if pg.key.get_pressed()[pg.K_LEFT]:
            player_pos[0] -= PLAYER_SPEED * dt
            player_pos[0] %= SCREEN_SIZE[0]
        if pg.key.get_pressed()[pg.K_UP]:
            player_pos[1] -= PLAYER_SPEED * dt
            player_pos[1] %= SCREEN_SIZE[1]
        if pg.key.get_pressed()[pg.K_DOWN]:
            player_pos[1] += PLAYER_SPEED * dt
            player_pos[1] %= SCREEN_SIZE[1]

        # Alert the server of our new position.
        connection.send({"event": Event.MOVE, "position": player_pos})

        # Clear the screen for the next frame drawing.
        screen.fill((0, 0, 0))

        # Draw each player on the screen.
        for pid, attrs in game_state["player_dicts"].items():
            # You are green, other players are cyan.
            color = (0, 255, 0) if int(pid) == player_id else (0, 255, 255)
            # Get the position of the current player.
            pos = game_state["player_dicts"][pid]["position"]
            # Draw the player to the screen.
            pg.draw.circle(screen, color, pos, PLAYER_RADIUS)
            # Render the username of the player on top of them.
            name_surf = font.render(f"{game_state["player_dicts"][pid]["name"]}", True, (0, 0, 0))
            screen.blit(name_surf, pg.Vector2(pos) - (name_surf.width // 2, name_surf.height // 2))

        # Render the FPS.
        fps_surf = font.render(f"FPS: {clock.get_fps():.0f}", True, (255, 255, 255), (0, 0, 0))
        screen.blit(fps_surf, (0, 0))
        # Update the entire screen.
        pg.display.flip()

if __name__ == '__main__':
    # Set up the connection to use json as a codec.
    connection.encode = lambda x: bytes(json.dumps(x), "utf8")
    connection.decode = lambda x: json.loads(x)
    # Get a username from the user.
    username = input("Username: ")
    # Initialize the graphics library.
    pg.init()
    print(f"Connected to {HOST}:{PORT}")
    # Connect to the server address and enter the main application loop.
    connection.run(game_loop, address=(HOST, PORT))
    # Quit the graphics library.
    pg.quit()

# Overview

This software demo shows off a UDP server capable of handling multiple clients that can move around in a virtual world.
To start the server, run it in the command line with python. It will begin hosting on `127.0.0.1:12345`.
To start a client, run it in the command line with python. Give it a username and it will connect to `127.0.0.1:12345`.

I wrote this software because I needed experience with UDP networking and using concurrency.

[Software Demo Video](https://youtu.be/OUFc7Bqc1Cg)

# Network Communication

This software uses client/server architecture.

This software uses User Datagram Protocol and by default runs the server on `127.0.0.1` with port number 12345.

The packets being sent between the client and the server are JSON objects,
which are serialized and deserialized on either end by the built-in `json` module that comes with Python.
However, you can choose whatever serialization protocol you want. It is easy to choose a different one internally.

# Development Environment

I used Pycharm Community as my IDE.

I used Python 3.12.2 as my programming language.
I used `pygame-ce v2.5.0` as my graphics library.
I used `anyio v4.4.0` as my concurrency library.

# Useful Websites

* [anyio API Reference](https://anyio.readthedocs.io/en/stable/api.html)
* [Pygame Community Documentation](https://pyga.me/docs/)

# Future Work

* Separate send task from tick task in server to reduce lag.
* Add monotonic nanosecond clock to server to track delta time and sign packets.
* Handle timeouts for sensitive packets and packet duplication and re-ordering.
* Have clients warn server they are disconnecting.
* Make clients interact in some way, probably with a simple game of tag.
* Have the user's client be drawn over other players, so they are always visible.
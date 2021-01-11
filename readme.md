# Popellers - a 2d multiplayer shooter game

Technologies: Python, UDP, TCP

# Instructions

To play the game first launch server.py and then client.py
Controls:
- turn, keys j and l
- shoot, key f

To make file transfers first launch file_server.py and then file_client.py
The server will upload files from folder /files/server_upload_file
The client will download the files to folder /files/client_download_file

Server addresses can be set in files in folder /files/

# Description

The application is a real-time multiplayer 2D shooter game. It is coded in Python and consists of clients and a server that communicate using UDP and TCP. In the game players will control an airplane viewed from above and try to shoot down other airplanes (controlled by other players). The airplane automatically flies ahead at constant speed. Players have three things they can do: turn left, turn right and shoot.

The game is controlled at the server and server decides if players collide or if they shoot another down. Server receives actions from players (turn, shoot) and updates this information to all players. Server sends this action information to clients right away. On top of this server sends regular updates to clients every three seconds. This information includes player positions and directions.

When client starts the game the clients game sends UDP packet to server requesting player ID number. Server generates ID number and sends it to client. After receiving this client game starts. If the client doesn't receive this packet it sends new requests until it receives it. Server identifies clients by their IP address and port number.

During the game all data is sent in UDP with triple redundancy. Client action data from client to server is one byte in payload (+ 20 bytes IP header and 8 bytes UDP header). Clients send only this type of data during the game. Server sends to clients three types of data:
1. instant updates after client makes an action (2 bytes ID number, 5 bits sequence number, 3 bits action data (direction north, east, south or west and if shooting or not), total 3 bytes)
2. regular updates every three seconds (2 bytes ID number, 18 bits position x, 18 bits position y, 2 bits direction, 1 bit if destroyed, 1 unused bit; total 5 bytes of information about one player multiplied by the amount of players; plus sequence number of 5 bits inside a byte with 3 bits unused.
3. update if an airplane has been destroyed (2 bytes ID number, 5 bit sequence number in a byte and one extra byte total 4 bytes)

Client identifies data type by the size of it. Instant update is 3 bytes, regular update is 6 bytes or more and destroy update is 4 bytes. The client checks the sequence number that it is what is expected. If the sequence number is same as previous the message is discarded. If the sequence number is next from previous the message is read. If the sequence number is higher than what should had been but inside a defined margin, it is read.

The margin is defined as 8 which means that if previous sequence number was 20 but now is received 28 it still will be read. This system is for dealing with burst errors. If the sequence number is higher than that, the message is discarded.

When player makes an action it is drawn on the player's screen right away. With longer round trip times the player will end up running a little behind of the game on server and may experience some sudden jumps in player positions on screen. This could be smoothed by making the sprites slide and not jump on the screen and by trying to predict positions based on latency but this is not implemented in this game.

The file download system uses TCP. It establishes a connection for each file. The server slices the files to 1400 byte size segments and sends to client. This is to avoid exceeding possible 1500 byte MTU.

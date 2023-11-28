# Tugas Besar Jaringan Komputer

## Table of Contents

- [Tugas Besar Jaringan Komputer](#tugas-besar-jaringan-komputer)
  - [Table of Contents](#table-of-contents)
  - [Project Description](#project-description)
  - [Running the Program](#running-the-program)


## Project Description

This project is a TCP implementation with the UDP protocol, made using python. This projet includes a rock-paper-scissors game, and a peer-to-peer network exchange. This project also supports sending intranet, just by updating the IP address of the host and the target.

## Running the Program

`python client.py {client port} {server port} {output path with no ext} no`
`python server.py {server port} {input path}`


to play game
`python rps.py {server port}`

`python player.py {client port} {server port}`

the first player to connect is player 1


send client to client
`python client.py {clientA port} {clientA port} {output path with no extension} no`
`python client.py {clientB port} {clientA port} {input path with extension} p2p`

import argparse
from enum import Enum
import socket
import typing
from node import MessageInfo
from server import Server


class rps_type(Enum):
  ROCK = 1,
  PAPER = 2,
  SCISSOR = 3

rps_dict = {
  1: rps_type.ROCK,
  2: rps_type.PAPER,
  3: rps_type.SCISSOR
}

class rps(Server):

  count: int = 0
  players: typing.Dict[int, rps_type] = {}
  is_first: bool = True

  def check(self):

    player_1 = self.players[0]
    player_2 = self.players[1]
    if player_1 == rps_type.ROCK and player_2 == rps_type.SCISSOR:
      print("[GAME] Player 1 throws ROCK and Player 2 throws SCISSOR")
      return 0
    if player_1 == rps_type.ROCK and player_2 == rps_type.PAPER:
      print("[GAME] Player 1 throws ROCK and Player 2 throws PAPER")
      return 1
    if player_1 == rps_type.ROCK and player_2 == rps_type.ROCK:
      print("[GAME] Player 1 throws ROCK and Player 2 throws ROCK")
      return 2
    if player_1 == rps_type.PAPER and player_2 == rps_type.ROCK:
      print("[GAME] Player 1 throws PAPER and Player 2 throws ROCK")
      return 0
    if player_1 == rps_type.PAPER and player_2 == rps_type.SCISSOR:
      print("[GAME] Player 1 throws PAPER and Player 2 throws SCISSOR")
      return 1
    if player_1 == rps_type.PAPER and player_2 == rps_type.PAPER:
      print("[GAME] Player 1 throws PAPER and Player 2 throws PAPER")
      return 2
    if player_1 == rps_type.SCISSOR and player_2 == rps_type.ROCK:
      print("[GAME] Player 1 throws SCISSOR and Player 2 throws ROCK")
      return 0
    if player_1 == rps_type.SCISSOR and player_2 == rps_type.PAPER:
      print("[GAME] Player 1 throws SCISSOR and Player 2 throws PAPER")
      return 1
    if player_1 == rps_type.SCISSOR and player_2 == rps_type.SCISSOR:
      print("[GAME] Player 1 throws SCISSOR and Player 2 throws SCISSOR")
      return 2
    return None
    
  # running the rps server game
  def run(self):
    self.players_address = []
    print("[!] Listening for players.\n")
    while len(self.connections) < 2 and len(self.players_address) < 2:
      addr = None
      try:
          addr = self.listen_broadcast(False)
          self.players_address.append(addr)
      except socket.error:
        print("Timeout")
    
    for i in self.players_address:
      print("[!] Waiting for player input")
      self.is_first = True
      conn = self.handshake(i[0], i[1])
      while conn is not None:
        self.listen()
        conn = self.connections.get((i[0], i[1]))


  def handle_message(self, message: MessageInfo):
    super().handle_message(message)
    if not self.is_first:
      self.players[self.count] = rps_dict[int(message.segment.payload)]
      self.count += 1
    else:
      self.is_first = False


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument("port", type=int)
  args = parser.parse_args()

  server = rps('127.0.0.1', args.port)
  
  
  server.run()
  winner = server.check()

  if winner is None:
    print("[GAME] Input is not valid")
  elif winner != 2:
    print("[GAME] Game ended! Winner is player", winner + 1)
  else:
    print("[GAME] Game ended in a draw!")
  print("[!] Finished broadcasting")

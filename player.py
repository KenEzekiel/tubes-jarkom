import argparse
import os
from client import Client
from segment import Segment


class player(Client):
  def __init__(self, action: int, ip: str, port: int, server_ip: str, server_port: int):
    super().__init__(ip, port, server_ip, server_port)
    self.action_type: int = action

  def run(self):
     # sending broadcast request
    self.send(self.server_ip, self.server_port, Segment.syn(0))

    # listening to handshake
    while self.get_server() is None:
      self.listen()
    
    client.transfer('127.0.0.1', self.server_port, f"{self.port}.txt")
      

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("client_port", type=int)
    parser.add_argument("server_port", type=int)
    args = parser.parse_args()
    action = input("input action (1 : ROCK, 2 : PAPER, 3 : SCISSOR) : ")

    file = open(f"{args.client_port}.txt", "w")
    file.write(str(action))
    file.close()
  
    client = player(action, '127.0.0.1', args.client_port, "127.0.0.1", args.server_port)
    client.run()
    
  
    os.remove(f"{args.client_port}.txt")

    
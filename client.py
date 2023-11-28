import argparse
import json
import typing
from node import Node, MessageInfo
from segment import Segment, SegmentFlags


class Client(Node):
  
  def __init__(self, ip: str, port: int, server_ip: str, server_port: typing.Optional[int]=None) -> None:
    super().__init__(ip, port)
    self.register_handler(self.handle_message)
    self.server_ip = server_ip
    self.server_port = server_port
    self.data: list[bytes] = []
    self.is_first = True
    self.output_path_extension = None
    self.p2p = False
  # def send(self, segment: Segment):
  #   self.send(self.server_ip, self.server_port, segment)

  def run(self):
    if self.port == self.server_port:
      # wait for another client to send a message
      conn = None
      print("[P2P] Waiting for peer node to connect")
      while conn is None:
        addr, segment = self.listen()
        conn = self.connections.get((addr[0], addr[1]))

      # listen for message from peer 
      while conn is not None:
        self.listen()
        conn = self.connections.get((addr[0], addr[1]))
    else:
      # if not p2p, then syn broadcast request
      if not self.p2p:
        # sending broadcast request
        print(f"[!] Sent SYN to {self.server_ip}:{self.server_port}")
        self.send(self.server_ip, self.server_port, Segment.syn(0))

      # listening to handshake
      while self.get_server() is None:
        self.listen()
        
      # receive files
      while self.get_server() is not None:
        self.listen()

  def get_server(self):
    return self.connections.get((self.server_ip, self.server_port))

  def handle_message(self, message_info: MessageInfo):
    if self.is_first:
      metadata_segment= message_info.segment
      metadata = json.loads(metadata_segment.payload.decode())
      self.output_path_filename = metadata['filename']
      self.output_path_extension = metadata['extension']
      self.is_first = False
    else:
      self.data.append(message_info.segment.payload)
    print(f"[Segment SEQ={message_info.segment.seq_num}] Received, Ack sent")

ip_alisha = "10.5.105.30"
ip_ken = '10.5.105.82'
localhost = '127.0.0.1'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("client_port", type=int)
    parser.add_argument("server_port", type=int)
    parser.add_argument("output_path", type=str)
    parser.add_argument("peer", type=str)
    args = parser.parse_args()
    client = Client(localhost, args.client_port, localhost, args.server_port)
    output_path = args.output_path
    if args.peer == "p2p":
      # send to peer node
      # server port is client peer node
      # output path is file to be transfered
      client.handshake('127.0.0.1', args.server_port)
      client.transfer('127.0.0.1', args.server_port, args.output_path)
    else:
      if args.server_port == args.client_port:
        client.p2p = True
      client.run()
      path = "output/"
      path += output_path if client.output_path_extension is None else output_path + ('.' + client.output_path_extension)
      with open(path, "wb") as f:
        for data in client.data:
          f.write(data)

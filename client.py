import argparse
import json
from node import Node, MessageInfo
from segment import Segment, SegmentFlags


class Client(Node):
  def __init__(self, ip: str, port: int, server_ip: str, server_port: int) -> None:
    super().__init__(ip, port)
    self.register_handler(self.handle_message)
    self.server_ip = server_ip
    self.server_port = server_port
    self.data: list[bytes] = []
    self.is_first = True
  
  # def send(self, segment: Segment):
  #   self.send(self.server_ip, self.server_port, segment)

  def run(self):
    # sending broadcast request
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
      metadata_segment, checksum = Segment.from_bytes(message_info.segment.payload)
      print("checksum", metadata_segment.is_valid_checksum())
      print(str(metadata_segment))
      print(metadata_segment.payload.decode())
      metadata = json.loads(metadata_segment.payload.decode())
      self.output_path = metadata['filename'] + 'a.' + metadata['extension']
      self.is_first = False
      print(self.output_path, "is now detected")
    else:
      self.data.append(message_info.segment.payload)
    print(f"[Segment SEQ={message_info.segment.seq_num}] Received, Ack sent")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("client_port", type=int)
    parser.add_argument("server_port", type=int)
    # parser.add_argument("output_path", type=str)
    args = parser.parse_args()

    client = Client('127.0.0.1', args.client_port, "127.0.0.1", args.server_port)
    # output_path = args.output_path
    client.run()

    with open(client.output_path, "wb") as f:
      for data in client.data:
        f.write(data)

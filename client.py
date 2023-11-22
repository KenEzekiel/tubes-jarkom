from node import Node, MessageInfo
from segment import Segment, SegmentFlags


class Client(Node):
  def __init__(self, ip: str, port: int, server_ip: str, server_port: int) -> None:
    super().__init__(ip, port)
    self.register_handler(self.handle_message)
    self.server_ip = server_ip
    self.server_port = server_port
    self.data: list[bytes] = []
  
  # def send(self, segment: Segment):
  #   self.send(self.server_ip, self.server_port, segment)

  def run(self):
    # sending broadcast request
    self.send(self.server_ip, self.server_port, Segment.syn(0))

    # listening to handshake
    while self.get_server() is None or self.get_server().receive.is_connected is False:
      self.listen()
      
    # receive files
    while self.get_server() is not None:
      self.listen()

  def get_server(self):
    return self.connections.get((self.server_ip, self.server_port))

  def handle_message(self, message_info: MessageInfo):
    self.data.append(message_info.segment.payload)
    

HOST = "127.0.0.1"
PORT = 65433

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 65432

client = Client(HOST, PORT, SERVER_HOST, SERVER_PORT)
client.run()
print(client.data)

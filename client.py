from node import Connection, Node, MessageInfo
from segment import Segment, SegmentFlags


class Client(Node):
  def __init__(self, connection: Connection, server_ip: str, server_port: int) -> None:
    super().__init__(connection)
    self.connection.register_handler(self.handle_message)
    self.server_ip = server_ip
    self.server_port = server_port
  
  def send(self, segment: Segment):
    self.connection.send(self.server_ip, self.server_port, segment)

  def handle_message(self, message_info: MessageInfo):
    print(message_info.segment.payload)

HOST = "127.0.0.1"
PORT = 65433

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 65432

connection = Connection(HOST, PORT)
client = Client(connection, SERVER_HOST, SERVER_PORT)


client.send(Segment(SegmentFlags(True, False, False), 0, 0, bytes("Hello World", "utf-8")))
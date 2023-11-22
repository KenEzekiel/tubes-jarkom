from node import Connection, MessageInfo, Node


class Server(Node):
  def __init__(self, connection: Connection) -> None:
    super().__init__(connection)
    self.connection.register_handler(self.handle_message)
  
  def run(self):
    self.connection.listen()

  def handle_message(self, message: MessageInfo):
    print("==========================")
    print("Received message from ", message.ip, message.port)
    print(message.segment)
    print("==========================")

HOST = "127.0.0.1"
PORT = 65432

connection = Connection(HOST, PORT)
server = Server(connection)
server.run()

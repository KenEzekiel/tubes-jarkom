from node import MessageInfo, Node


class Server(Node):
  def __init__(self, ip: str, port: int) -> None:
    super().__init__(ip, port)
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
server = Server(HOST, PORT)
server.run()

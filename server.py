from connection import Connection, MessageInfo

HOST = "127.0.0.1"
PORT = 65432

connection = Connection(HOST, PORT)
def handler(message: MessageInfo):
  print("==========================")
  print("Received message from ", message.ip, message.port)
  print(message.segment)
  print("==========================")

connection.register_handler(handler=handler)
connection.listen()

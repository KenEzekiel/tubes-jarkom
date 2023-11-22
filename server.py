import socket
from node import MessageInfo, Node
from segment import Segment, SegmentError


class Server(Node):
  def __init__(self, ip: str, port: int) -> None:
    super().__init__(ip, port)
    self.register_handler(self.handle_message)
    self.listen_addresses: list[tuple[str, int]] = []
  
  def run(self):
    listening = True
    while listening:
        try:
          self.listen_broadcast()
        except socket.timeout:
          print("Timeout")
        isListenMore = input("Listen more? (y/n)")
        if isListenMore == "n":
            break
    self.broadcast()

  def listen_broadcast(self):
    addr, segment = self.listen_base(30)
    try:
      if segment.flags.syn and not segment.flags.ack and addr not in self.listen_addresses:
        self.listen_addresses.append(addr)
        print(f"[!] Received request from {addr[0]}:{addr[1]}")
    except SegmentError as e:
      print(e)

  def broadcast(self):
    for addr in self.listen_addresses:
      conn = self.handshake(addr[0], addr[1])
      seq_num = conn.send.seq_num
      self.send(conn.send.remote_ip, conn.send.remote_port, Segment.payload(conn.send.seq_num, b"Hello World"))
      while conn.send.seq_num == seq_num:
        try:
          self.listen(30)
        except socket.timeout:
          print("Timeout")
          break
      self.end_connection(conn.send.remote_ip, conn.send.remote_port)

  def handle_message(self, message: MessageInfo):
    print("==========================")
    print("Received message from ", message.ip, message.port)
    print(message.segment)
    print("==========================")

HOST = "127.0.0.1"
PORT = 65432
server = Server(HOST, PORT)
server.run()

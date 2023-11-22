import argparse
import math
import os
import socket
from connection import get_seqnum_diff, increment_seqnum
from node import MessageInfo, Node
from segment import MAX_PAYLOAD, Segment, SegmentError


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

  def listen_broadcast(self):
    addr, segment = self.listen_base(30)
    try:
      if segment.flags.syn and not segment.flags.ack and addr not in self.listen_addresses:
        self.listen_addresses.append(addr)
        print(f"[!] Received request from {addr[0]}:{addr[1]}")
    except SegmentError as e:
      print(e)

  def broadcast(self, file_path: str):
    file = open(file_path, "rb")
    filesize = os.path.getsize(file_path)
    max_segment = math.ceil(filesize / MAX_PAYLOAD)

    for addr in self.listen_addresses:
      conn = self.handshake(addr[0], addr[1])
      sent_segment = 0
      while sent_segment < max_segment:
        to_send = min(conn.send.window_size, max_segment - sent_segment)
        for i in range(to_send):
          file.seek((sent_segment + i) * MAX_PAYLOAD)
          print(f"[Segment SEQ={conn.send.seq_num + i}] Sent")
          self.send(conn.send.remote_ip, conn.send.remote_port, Segment.payload(conn.send.seq_num + i, file.read(MAX_PAYLOAD)))

        start_seq_num = conn.send.seq_num
        start_sent_segment = sent_segment

        for i in range(to_send):
          self.listen(5)
          diff = get_seqnum_diff(start_seq_num, conn.send.seq_num)
          if start_sent_segment + diff > sent_segment:
            sent_segment = start_sent_segment + diff
          if diff == to_send:
            break
      self.end_connection(conn.send.remote_ip, conn.send.remote_port)
      print(f"[!] Finished sending to {addr[0]}:{addr[1]}")

  def handle_message(self, message: MessageInfo):
    print("==========================")
    print("Received message from ", message.ip, message.port)
    print(message.segment)
    print("==========================")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int)
    parser.add_argument("input_path", type=str)
    args = parser.parse_args()

    server = Server('127.0.0.1', args.port)
    input_path = args.input_path
    
    server.run()
    server.broadcast(input_path)
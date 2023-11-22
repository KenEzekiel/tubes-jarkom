import argparse
import math
import os
import socket
from connection import get_seqnum_diff
from node import MessageInfo, Node
from segment import MAX_PAYLOAD, Segment, SegmentError


class Server(Node):
  def __init__(self, ip: str, port: int, file_path: str) -> None:
    super().__init__(ip, port)
    self.register_handler(self.handle_message)
    self.listen_addresses: list[tuple[str, int]] = []
    self.file_path = file_path
    self.filesize = os.path.getsize(file_path)
  
  def run(self):
    listening = True
    print("[!] Listening for broadcast request for clients.\n")
    while listening:
        try:
          self.listen_broadcast()
        except socket.timeout:
          print("Timeout")
        is_listen_more = input("[?] Listen more? (y/n) ")
        if is_listen_more == "n":
            break

  def listen_broadcast(self):
    try:
      addr, segment, valid_checksum = self.listen_base(30)
      if valid_checksum and segment.flags.syn and not segment.flags.ack and addr not in self.listen_addresses:
        self.listen_addresses.append(addr)
        print(f"[!] Received request from {addr[0]}:{addr[1]}")
    except SegmentError as e:
      print(e)

  def broadcast(self):
    file = open(self.file_path, "rb")
    max_segment = math.ceil(self.filesize / MAX_PAYLOAD)
    print(f"\nClient list:")
    for i, addr in enumerate(self.listen_addresses):
      print(f"{i+1}. {addr[0]}:{addr[1]}")
    print()

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
        i = 0
        while i < to_send:
          for i in range(to_send):
            try:
              addr, segment = self.listen(5)
              if segment is not None and segment.flags.ack and addr == (conn.send.remote_ip, conn.send.remote_port):
                print(f"[Segment SEQ={segment.ack_num-1}] Ack received", end="")
                diff = get_seqnum_diff(start_seq_num, conn.send.seq_num)
                if start_sent_segment + diff > sent_segment:
                  print(f", new sequence base = {segment.ack_num}")
                  sent_segment = start_sent_segment + diff
                else:
                  print()
                i += 1
                if diff == to_send:
                  break
            except socket.timeout:
              break
      print(f"[!] Finished sending to {addr[0]}:{addr[1]}")
      self.end_connection(conn.send.remote_ip, conn.send.remote_port)

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

    server = Server('127.0.0.1', args.port, args.input_path)
    
    server.run()
    server.broadcast()
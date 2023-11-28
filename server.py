import argparse
import math
import os
import socket
import typing
from connection import get_seqnum_diff, increment_seqnum
from node import MessageInfo, Node
from segment import MAX_PAYLOAD, Segment, SegmentError
import threading

ENABLE_PARALLEL = True

# For parallelization
class PausableBroadcastThread(threading.Thread):
  def __init__(self, server, addr: tuple[str, int]):
    super().__init__()
    self.server = server
    self.addr = addr
    self.is_paused = False
    self.is_stopped = False
    self.pause_cond = threading.Condition(threading.Lock())

  # thread run method
  def run(self):
    with self.pause_cond:
      while self.is_paused:
        self.pause_cond.wait()
      file = open(server.file_path, "rb")
      max_segment = math.ceil(server.filesize / MAX_PAYLOAD)
      addr = self.addr
      conn = server.handshake(addr[0], addr[1])
      sent_segment = 0
      # Send metadata
      metadata = {
        'filename': server.file_path.split('.')[-2],
        'extension': server.file_path.split('.')[-1]
      }
      metadata_segment = Segment.metadata(conn.send.seq_num + 1, metadata)
      is_ack = False
      server.send(conn.send.remote_ip, conn.send.remote_port, metadata_segment)
      while not is_ack:
        print("waiting for ack")
        try:
          addr, segment = server.listen(2)
          if segment is not None and segment.flags.ack and addr == (conn.send.remote_ip, conn.send.remote_port):
            print(f"[Segment SEQ={segment.ack_num-1}] Ack metadata received")
            is_ack = True
            sent_segment += 0
        except socket.timeout:
          print(f"[Socket timeout] ACK not received")
    while sent_segment < max_segment:
      with self.pause_cond:
        while self.is_paused:
          self.pause_cond.wait()
        to_send = min(conn.send.window_size, max_segment - sent_segment)
        for i in range(to_send):
          file.seek((increment_seqnum(sent_segment, i)) * MAX_PAYLOAD)
          print(f"[Segment SEQ={increment_seqnum(conn.send.seq_num, i)}] Sent")
          server.send(conn.send.remote_ip, conn.send.remote_port, Segment.payload(increment_seqnum(conn.send.seq_num, i), file.read(MAX_PAYLOAD)))

        start_seq_num = conn.send.seq_num
        start_sent_segment = sent_segment
        i = 0
      while i < to_send:
        with self.pause_cond:
          while self.is_paused:
            self.pause_cond.wait()
          for _ in range(to_send):
            try:
              addr, segment = server.listen(5)
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
              i = to_send
              break
    print(f"[!] Finished sending to {addr[0]}:{addr[1]}")
    server.end_connection(conn.send.remote_ip, conn.send.remote_port)

  def pause(self):
    if not self.is_paused:
      self.is_paused = True
      self.pause_cond.acquire()
  
  def resume(self):
    self.is_paused = False
    self.pause_cond.notify()
    self.pause_cond.release()


class Server(Node):
  def __init__(self, ip: str, port: int, file_path: typing.Optional[str]=None) -> None:
    super().__init__(ip, port)
    self.register_handler(self.handle_message)
    self.listen_addresses: dict[tuple[str, int], typing.Optional[PausableBroadcastThread]] = {}
    self.file_path = file_path
    if file_path is not None:
      self.filesize = os.path.getsize(file_path)
  
  def run(self):
    listening = True
    print("[!] Listening for broadcast request for clients.\n")
    while listening:
        addr = None
        try:
          if ENABLE_PARALLEL:
            for addr, thread in self.listen_addresses.items():
              if thread is not None:
                thread.resume()
          addr = self.listen_broadcast()
          if addr is not None and ENABLE_PARALLEL:
            self.listen_addresses[addr] = PausableBroadcastThread(self, addr)
            self.listen_addresses[addr].pause()
            self.listen_addresses[addr].start()
        except socket.error:
          print("Timeout")
        for addr, thread in self.listen_addresses.items():
          if thread is not None:
            thread.pause()
        is_listen_more = input("[?] Listen more? (y/N) ")
        if is_listen_more != "y":
            break

  # Listening for broadcast request from client
  def listen_broadcast(self, timeout: typing.Optional[bool]=True):
    try:
      addr, segment, valid_checksum = self.listen_base(5 if timeout else None)
      if valid_checksum and segment.flags.syn and not segment.flags.ack and addr not in self.listen_addresses:
        self.listen_addresses[addr] = None
        print(f"[!] Received request from {addr[0]}:{addr[1]}")
        return addr
      else:
        return self.listen_broadcast()
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
      # Send metadata
      metadata = {
        'filename': server.file_path.split('.')[-2],
        'extension': server.file_path.split('.')[-1]
      }
      metadata_segment = Segment.metadata(conn.send.seq_num + 1, metadata)
      is_ack = False
      server.send(conn.send.remote_ip, conn.send.remote_port, metadata_segment)
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
          for _ in range(to_send):
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

    server = Server('172.20.10.7', args.port, args.input_path)
    
    server.run()
    if ENABLE_PARALLEL:
      for addr, thread in server.listen_addresses.items():
        if thread is not None:
          thread.resume()
      for addr, thread in server.listen_addresses.items():
        if thread is not None:
          thread.join()
    else:
      server.broadcast()
    print("[!] Finished broadcasting")
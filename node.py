import math
import os
import socket
from segment import MAX_PAYLOAD, Segment, SegmentError
import typing
from abc import abstractmethod, ABC
from connection import Connection, generate_seqnum, get_seqnum_diff, increment_seqnum

# Message info class, describing the ip and port of segment source
class MessageInfo:
  def __init__(self, ip: str, port: int, segment: Segment) -> None:
    self.ip = ip
    self.port = port
    self.segment = segment

class HandshakeError(Exception):
  def __init__(self) -> None:
    super().__init__("Handshake error")

class Node(ABC):
  def __init__(self, ip: str, port: int) -> None:
    self.ip = ip
    self.port = port
    self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.__socket.bind((self.ip, self.port))
    self.connections: typing.Dict[(str, int), Connection] = {}
    self.__handler = None
    self.__on_close = None
    self.__on_connect = None

  # Atomic send method
  def send(self, ip_remote: str, port_remote: int, segment: Segment):
    self.__socket.sendto(segment.pack_headers() + segment.payload, (ip_remote, port_remote))

  # Handshake wrapper method, defines the logic of the handshake (init part, sendin syn)
  def handshake(self, ip_remote: str, port_remote: int):
    # init connection
    new_connection = Connection(self.ip, self.port, ip_remote, port_remote)
    new_connection.send.seq_num = generate_seqnum()
    # add connection to list of connection
    self.connections[(ip_remote, port_remote)] = new_connection
    # send syn
    print(f"[Handshake] Sending SYN to {ip_remote}:{port_remote}")
    self.send(ip_remote, port_remote, Segment.syn(new_connection.send.seq_num))
    # wait for syn ack
    is_ack = False
    try_num = 1
    while not is_ack and try_num < 2:
      try:
        # listen for syn ack
        self.listen(2)
        # if connected, then set is ack true, because ack is received in the connection
        if new_connection.send.is_connected:
          is_ack = True
      except socket.timeout:
        # if listen timed out
        if new_connection.send.is_connected:
          is_ack = True
          break
        try_num += 1
        # try another time for sending syn
        print("[Handshake] Timeout, resending syn")
        self.send(ip_remote, port_remote, Segment.syn(new_connection.send.seq_num))
    if not is_ack:
      # fail handshake
      self.connections.pop((ip_remote, port_remote))
      raise HandshakeError()
    
    return new_connection

  # Registers a handler, to handle when receiving message
  def register_handler(self, handler: typing.Callable[[MessageInfo], None]):
    self.__handler = handler
  
  # Registers a protocol to be used when closing a connection
  def register_on_close(self, on_close: typing.Callable[[MessageInfo], None]):
    self.__on_close = on_close

  # Registers a protocol to be used when connecting to a new connection
  def register_on_connect(self, on_connect: typing.Callable[[MessageInfo], None]):
    self.__on_connect = on_connect

  # Listen wrapper, calling on receive here and checking checksum
  def listen(self, timeout: typing.Optional[float] = None):
    try:
      addr, segment, checksum_valid = self.listen_base(timeout)
      if checksum_valid:
        self.__on_receive(addr, segment)
        return addr, segment
      else:
        # Checksum failed
        print(f"[Segment SEQ={segment.seq_num}] Checksum failed, Ack prev sequence number")
        self.send(addr[0], addr[1], Segment.ack(segment.seq_num))
    except SegmentError as e:
      print(e)

  # Atomic listen, listens to the socket and translate from bytes
  def listen_base(self, timeout: typing.Optional[float] = None):
    self.__socket.settimeout(timeout)
    data, addr = self.__socket.recvfrom(32768)
    segment, checksum_valid = Segment.from_bytes(data)
    return (addr, segment, checksum_valid)

  # Handler for when receiving certain flags (included in handshake algorithm)
  def __on_receive(self, addr: tuple[str, int], segment: Segment):
    connection = self.connections.get((addr[0], addr[1]))
    # syn not ack, server receive connection request
    if segment.flags.syn and not segment.flags.ack:
      # server acknowledgement of the syn, receive is now connected
      new_connection = Connection(self.ip, self.port, addr[0], addr[1])
      new_connection.receive.seq_num = increment_seqnum(segment.seq_num)
      new_connection.receive.is_connected = True
      new_connection.send.seq_num = generate_seqnum()

      # send ack
      self.connections[(addr[0], addr[1])] = new_connection
      self.send(addr[0], addr[1], Segment.syn_ack(new_connection.send.seq_num, new_connection.receive.seq_num))
      print(f"[Handshake] Received SYN from {addr[0]}:{addr[1]}\n[Handshake] sending SYN ACK with SEQNUM [{new_connection.send.seq_num}] and ACK NUM [{new_connection.receive.seq_num}]")
      # wait for ack
      print(f"[Handshake] Waiting for ACK with ACK NUM [{increment_seqnum(new_connection.receive.seq_num)}]")
      is_ack = False
      try_num = 1
      while not is_ack and try_num < 2:
        try:
          self.listen(2)
          if new_connection.send.is_connected:
            is_ack = True
            print(f"[Handshake] Connection established {addr[0]}:{addr[1]}")
        except socket.timeout:
          if new_connection.send.is_connected:
            is_ack = True
            print(f"[Handshake] Connection established {addr[0]}:{addr[1]}")
            break
          try_num += 1
          print("[Handshake] Timeout, resending syn ack")
          self.send(addr[0], addr[1], Segment.syn_ack(new_connection.send.seq_num, new_connection.receive.seq_num))
      if not is_ack:
        raise HandshakeError()

    # syn ack, client receive ack of syn from server
    elif segment.flags.syn and segment.flags.ack:
      connection = self.connections.get((addr[0], addr[1]))
      self.send(addr[0], addr[1], Segment.ack(increment_seqnum(segment.seq_num)))
      print(f"[Handshake] Received SYN ACK from {addr[0]}:{addr[1]}\n[Handshake] Sending ACK with ACK NUM [{increment_seqnum(segment.seq_num)}]")
      # If connection is not registered, or send connection is connected, or not the correct ack, continue
      if connection is None or connection.send.is_connected or segment.ack_num != increment_seqnum(connection.send.seq_num):
        return
      # Send connection is connected
      connection.send.is_connected = True
      connection.send.seq_num = segment.ack_num
      
      # Send ack for the syn
      connection.receive.seq_num = increment_seqnum(segment.seq_num)
      connection.receive.is_connected = True
      print(f"[Handshake] Connection established {addr[0]}:{addr[1]}")

      if self.__on_connect is not None:
        self.__on_connect(MessageInfo(addr[0], addr[1], segment))

    # fin
    elif segment.flags.fin and not segment.flags.ack:
      print(f"[~] Received FIN")
      # cek
      if connection is None or not connection.receive.is_connected:
        return

      # receive connection set to false
      connection.receive.is_connected = False
      
      # send fin ack
      self.send(addr[0], addr[1], Segment.fin_ack())
      print(f"[~] Sending FIN ACK, waiting for ACK...")
      # wait for ack
      is_ack = False
      try_num = 1
      while not is_ack and try_num < 2:
        try:
          self.listen(2)
          if not connection.send.is_connected:
            is_ack = True
            print(f"[Termination] Connection closed {addr[0]}:{addr[1]}")
        except socket.timeout:
          if not connection.send.is_connected:
            is_ack = True
            print(f"[Termination] Connection closed {addr[0]}:{addr[1]}")
            break
          try_num += 1
          print("[Termination] Timeout, resending fin ack")
          self.send(addr[0], addr[1], Segment.fin_ack())
    
    # fin ack
    elif segment.flags.fin and segment.flags.ack:
      self.send(addr[0], addr[1], Segment.ack(0))
      if connection is None or not connection.send.is_connected:
        return
      connection.send.is_connected = False
      self.connections.pop((addr[0], addr[1]))
      print(f"[Termination] Connection closed {addr[0]}:{addr[1]}")
      if self.__on_close is not None:
        self.__on_close(MessageInfo(addr[0], addr[1], segment))
  
    # ack only, server receive final ack
    elif segment.flags.ack:
      print(f"[~] Received ACK with ACK NUM [{segment.ack_num}]")
      if connection is None:  
        return
      # ack for the fin
      if not connection.receive.is_connected:
        conn = self.connections.pop((addr[0], addr[1]))
        conn.send.is_connected = False
        if self.__on_close is not None:
          self.__on_close(MessageInfo(addr[0], addr[1], segment))
        return
      # If not connected
      if not connection.send.is_connected:
        # If ack num is not the same as seq num + 1
        if segment.ack_num != increment_seqnum(connection.send.seq_num):
          return
        connection.send.is_connected = True
        connection.send.seq_num = segment.ack_num
        if self.__on_connect is not None:
          self.__on_connect(MessageInfo(addr[0], addr[1], segment))
      else:
        # If connected, set the seq num to the ack num
        if connection.send.is_valid_ack(segment.ack_num):
          connection.send.seq_num = segment.ack_num
          
    # receive payload
    else:
      if connection is None or not connection.receive.is_connected:
        return
      if self.__handler is not None:
        # send ack and call the message handler
        connection.receive.seq_num = increment_seqnum(segment.seq_num)
        self.send(addr[0], addr[1], Segment.ack(connection.receive.seq_num))
        self.__handler(MessageInfo(addr[0], addr[1], segment))
  
  def close(self):
    self.__socket.close()

  def end_connection(self, ip: str, port: int):
    connection = self.connections.get((ip, port))
    if connection is None:
      return
    self.send(ip, port, Segment.fin())
    while self.connections.get((ip, port)) is not None:
      try:
        self.listen(2)
      except socket.timeout:
        self.send(ip, port, Segment.fin())

  @abstractmethod
  def run():
    pass

  @abstractmethod
  def handle_message(segment: Segment):
    pass
  
  def transfer(self, ip: str, port: int, file_path: str):
    print("Transfer file...")
    file = open(file_path, "rb")
    filesize = os.path.getsize(file_path)
    max_segment = math.ceil(filesize / MAX_PAYLOAD)

    conn = self.connections[(ip, port)]
    sent_segment = 0
    # Send metadata
    metadata = {
      'filename': file_path.split('.')[-2],
      'extension': file_path.split('.')[-1]
    }
    metadata_segment = Segment.metadata(conn.send.seq_num + 1, metadata)
    is_ack = False
    self.send(conn.send.remote_ip, conn.send.remote_port, metadata_segment)
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
      print(f"[!] Finished sending to {ip}:{port}")
      self.end_connection(conn.send.remote_ip, conn.send.remote_port)
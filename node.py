import socket
from segment import Segment, SegmentError
import typing
from abc import abstractmethod, ABC
from connection import Connection, generate_seqnum, increment_seqnum

class MessageInfo:
  def __init__(self, ip: str, port: int, segment: Segment) -> None:
    self.ip = ip
    self.port = port
    self.segment = segment


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

  def send(self, ip_remote: str, port_remote: int, segment: Segment):
    self.__socket.sendto(segment.pack_headers() + segment.payload, (ip_remote, port_remote))

  def handshake(self, ip_remote: str, port_remote: int):
    new_connection = Connection(self.ip, self.port, ip_remote, port_remote)
    new_connection.send.seq_num = generate_seqnum()
    self.connections[(ip_remote, port_remote)] = new_connection
    self.send(ip_remote, port_remote, Segment.syn(new_connection.send.seq_num))
    while not new_connection.send.is_connected:
      try:
        self.listen(2)
      except socket.timeout:
        self.send(ip_remote, port_remote, Segment.syn(new_connection.send.seq_num))
    return new_connection

  def register_handler(self, handler: typing.Callable[[MessageInfo], None]):
    self.__handler = handler
  
  def register_on_close(self, on_close: typing.Callable[[MessageInfo], None]):
    self.__on_close = on_close

  def register_on_connect(self, on_connect: typing.Callable[[MessageInfo], None]):
    self.__on_connect = on_connect

  def listen(self, timeout: typing.Optional[float] = None):
    try:
      addr, segment = self.listen_base(timeout)
      self.__on_receive(addr, segment)
    except SegmentError as e:
      print(e)

  def listen_base(self, timeout: typing.Optional[float] = None):
    self.__socket.settimeout(timeout)
    data, addr = self.__socket.recvfrom(32768)
    segment: Segment = Segment.from_bytes(data)
    return (addr, segment)

  
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
      
    # syn ack, client receive ack of syn from server
    elif segment.flags.syn and segment.flags.ack:
      connection = self.connections.get((addr[0], addr[1]))
      # If connection is not registered, or send connection is connected, or not the correct ack, continue
      if connection is None or connection.send.is_connected or segment.ack_num != increment_seqnum(connection.send.seq_num):
        return
      # Send connection is connected
      connection.send.is_connected = True
      connection.send.seq_num = segment.ack_num
      
      # Send ack for the syn
      connection.receive.seq_num = increment_seqnum(segment.seq_num)
      connection.receive.is_connected = True
      self.send(addr[0], addr[1], Segment.ack(connection.receive.seq_num))

      if self.__on_connect is not None:
        self.__on_connect(MessageInfo(addr[0], addr[1], segment))

    elif segment.flags.fin and not segment.flags.ack:
      # cek
      if connection is None or not connection.receive.is_connected:
        return

      # receive connection set to false
      connection.receive.is_connected = False
      
      # send fin ack
      self.send(addr[0], addr[1], Segment.fin_ack())
    
      
    elif segment.flags.fin and segment.flags.ack:
      if connection is None or not connection.send.is_connected:
        return
      connection.send.is_connected = False
      self.connections.pop((addr[0], addr[1]))
      self.send(addr[0], addr[1], Segment.ack(0))
      if self.__on_close is not None:
        self.__on_close(MessageInfo(addr[0], addr[1], segment))
  
    # ack only, server receive final ack
    elif segment.flags.ack:
      if connection is None:  
        return
      # ack for the fin
      if not connection.receive.is_connected:
        self.connections.pop((addr[0], addr[1]))
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
  
  
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
  connections: typing.Dict[(str, int), Connection] = {}

  def __init__(self, ip: str, port: int) -> None:
    self.ip = ip
    self.port = port
    self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


  def send(self, ip_remote: str, port_remote: int, segment: Segment):
    self.__socket.sendto(segment.pack_headers() + segment.payload, (ip_remote, port_remote))

  def register_handler(self, handler: typing.Callable[[MessageInfo]], on_close: typing.Callable[[MessageInfo]]):
    self.__handler = handler
    self.__on_close = on_close

  def listen(self):
    self.__socket.bind((self.ip, self.port))
    self.__socket.settimeout(10)

    while True:
      data, addr = self.__socket.recvfrom(32768)
      try:
        segment: Segment = Segment.from_bytes(data)
        self.__on_receive(addr, segment)
      except SegmentError as e:
        print(e)
        continue

  
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
      self.send(addr[0], addr[1], Segment.ack(connection.receive.seq_num))

    elif segment.flags.fin and not segment.flags.ack:
      # cek
      if connection is None or not connection.receive.is_connected:
        return

      # receive connection set to false

      connection.receive.is_connected = False
      self.__on_close(MessageInfo(addr[0], addr[1], segment))
      # send fin ack
      self.send(addr[0], addr[1], Segment.fin_ack())
    
      
    elif segment.flags.fin and segment.flags.ack:
      if connection is None or not connection.send.is_connected:
        return
      self.__on_close(MessageInfo(addr[0], addr[1], segment))
      self.connections.pop((addr[0], addr[1]))
      self.send(addr[0], addr[1], Segment.ack(0))
  
    # ack only, server receive final ack
    elif segment.flags.ack:
      if connection is None:  
        return
      # ack for the fin
      if not connection.receive.is_connected:
        self.connections.pop((addr[0], addr[1]))
        return
      # If not connected
      if not connection.send.is_connected:
        # If ack num is not the same as seq num + 1
        if segment.ack_num != increment_seqnum(connection.send.seq_num):
          return
        connection.send.is_connected = True
        connection.send.seq_num = segment.ack_num
      else:
        # If connected, set the seq num to the ack num
        if connection.send.is_valid_ack(segment.ack_num):
          connection.send.seq_num = segment.ack_num
          
    # receive payload
    else:
      if connection is None or not connection.receive.is_connected:
        return
      
      self.__handler(MessageInfo(addr[0], addr[1], segment))

  
  
  def close(self):
    self.__socket.close()

  @abstractmethod
  def run():
    pass

  @abstractmethod
  def handle_message(segment: Segment):
    pass
  
  
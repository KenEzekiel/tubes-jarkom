import socket
from segment import Segment, SegmentError
import typing
from abc import abstractmethod, ABC


class MessageInfo:
  def __init__(self, ip: str, port: int, segment: Segment) -> None:
    self.ip = ip
    self.port = port
    self.segment = segment


class Connection:
  def __init__(self, ip: str, port: int) -> None:
    self.ip = ip
    self.port = port
    self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


  def send(self, ip_remote: str, port_remote: int, segment: Segment):
    self.__socket.sendto(segment.pack_headers() + segment.payload, (ip_remote, port_remote))

  def register_handler(self, handler: typing.Callable[[MessageInfo], None]):
    self.__handler = handler

  def listen(self):
    self.__socket.bind((self.ip, self.port))
    self.__socket.settimeout(10)

    while True:
      data, addr = self.__socket.recvfrom(32768)
      try:
        segment = Segment.from_bytes(data)
        self.__handler(MessageInfo(addr[0], addr[1], segment))
      except SegmentError as e:
        print(e)
        continue

  def close(self):
    self.__socket.close()

  
class Node(ABC):
  def __init__(self, connection: Connection) -> None:
    self.connection = connection
  
  @abstractmethod
  def run():
    pass

  @abstractmethod
  def handle_message(segment: Segment):
    pass
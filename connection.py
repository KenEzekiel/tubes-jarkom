

import random
import typing


WINDOW_SIZE = 5

def generate_seqnum():
  return random.randint(0, 2**32 - 1)

def increment_seqnum(seqnum: int, increment: typing.Optional[int] = None):
  if increment is None:
    increment = 1
  seqnum = seqnum + increment

  # overflow 32bit
  if seqnum > 0xFFFFFFFF:
    return (seqnum) - 0xFFFFFFFF
  return seqnum
    

def get_seqnum_diff(seqnum_low: int, seqnum_high: int):
  if seqnum_low > seqnum_high:
    return seqnum_high + (0xFFFFFFFF - seqnum_low)
  return seqnum_high - seqnum_low

class ConnectionSend:
  def __init__(self, ip: str, port: int, remote_ip: str, remote_port: int) -> None:
    self.ip = ip
    self.port = port
    self.remote_ip = remote_ip
    self.remote_port = remote_port
    # same as sequence base
    self.seq_num = 0
    self.is_connected = False

  @property
  def window_size(self):
    return WINDOW_SIZE

  @property
  def sequence_max(self):
    return increment_seqnum(self.seq_num + self.window_size + 1)
  
  def is_valid_ack(self, ack_num: int):
    if (self.sequence_max < self.seq_num):
      return self.seq_num <= ack_num - 1 or ack_num - 1 < self.sequence_max
    return self.seq_num <= ack_num - 1 < self.sequence_max
    

class ConnectionReceive:
  def __init__(self, ip: str, port: int, remote_ip: str, remote_port: int) -> None:
    self.ip = ip
    self.port = port
    self.remote_ip = remote_ip
    self.remote_port = remote_port
    self.seq_num = 0
    self.is_connected = False
  
class Connection:
  def __init__(self, ip: str, port: int, remote_ip: str, remote_port: int) -> None:
    self.receive = ConnectionReceive(ip, port, remote_ip, remote_port)
    self.send = ConnectionSend(ip, port, remote_ip, remote_port)

# ack itu punya send
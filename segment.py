import json
from struct import pack, unpack
from typing import Optional


MAX_PAYLOAD = 32756

class SegmentError(Exception):
  def __init__(self, message: str) -> None:
    super().__init__(message)

class SegmentFlags:
  def __init__(self, syn: bool, ack: bool, fin: bool) -> None:
    self.syn = syn
    self.ack = ack
    self.fin = fin

  def get_flag_bytes(self):
    return ((self.syn << 1) | (self.ack << 4) | self.fin)
  
  @staticmethod
  def from_byte(data: int):
    return SegmentFlags(bool(data >> 1 & 1), bool(data >> 4 & 1), bool(data & 1))
  
  def __str__(self) -> str:
    return f"SYN: {self.syn}, ACK: {self.ack}, FIN: {self.fin}"

class Segment:
  def __init__(self, flags: SegmentFlags, seq_num: int, ack_num: int, payload: bytes, checksum: Optional[int] = None) -> None:
    self.flags = flags
    self.seq_num = seq_num
    self.ack_num = ack_num
    self.payload = payload
    if not isinstance(checksum, int):
      self.checksum = self.__calculate_checksum()
    else:
      self.checksum = checksum

  @staticmethod
  def syn(seq_num: int):
    return Segment(SegmentFlags(True, False, False), seq_num, 0, b"", b"")
  
  @staticmethod
  def ack(ack_num: int):
    return Segment(SegmentFlags(False, True, False), 0, ack_num, b"", b"")
  
  @staticmethod
  def syn_ack(seq_num: int, ack_num: int):
    return Segment(SegmentFlags(True, True, False), seq_num, ack_num, b"", b"")

  @staticmethod
  def fin():
    return Segment(SegmentFlags(False, False, True), 0, 0, b"", b"")
  
  @staticmethod
  def fin_ack():
    return Segment(SegmentFlags(False, True, True), 0, 0, b"", b"")
  
  @staticmethod
  def payload(seq_num: int, payload: bytes):
    return Segment(SegmentFlags(False, False, False), seq_num, 0, payload)
  
  @staticmethod
  def metadata(seq_num: int, metadata: dict):
    payload = json.dumps(metadata)
    payload = payload.encode()
    seg = Segment(SegmentFlags(False, False, False), seq_num, 0, payload)
    return seg

  @staticmethod
  def from_bytes(data: bytes):
    if (len(data) < 12):
      raise SegmentError("data must be at least 12 bytes")
    seq_num, ack_num, flags, _, checksum = unpack("!IIBBH", data[:12])
    payload = data[12:] if len(data) > 12 else b""
    segment = Segment(SegmentFlags.from_byte(flags), seq_num, ack_num, payload, checksum)
    return segment, segment.is_valid_checksum()
  

  def __calculate_checksum(self, is_recv = False):
    # checksum 16 bit one's complement
    # 16 bit means adding per 2 bytes
    # seq num

    checksum = ((self.seq_num >> 16) + (self.seq_num & 0xFFFF))
    # ack num
    checksum += ((self.ack_num >> 16) + (self.ack_num & 0xFFFF))
    # flags and empty
    checksum += (self.flags.get_flag_bytes() << 8) & 0xFF00

    # payload
    for i in range(0, len(self.payload), 2):
      checksum += (self.payload[i] << 8)
      if i + 1 < len(self.payload):
        checksum += self.payload[i + 1]

    # add carry
    while checksum >> 16:
      checksum = (checksum >> 16) + (checksum & 0xFFFF)
    if is_recv:
      return checksum
    else:
      return (~checksum) & 0xFFFF
    
  def update_checksum(self):
    self.checksum = self.__calculate_checksum()

  def is_valid_checksum(self):
    return self.__calculate_checksum(True) + self.checksum == 0xFFFF
    
  def pack_headers(self):
    return pack("!IIBBH", self.seq_num, self.ack_num, self.flags.get_flag_bytes(), 0x00, self.checksum)
  
  def __str__(self) -> str:
    return f"seq_num: {self.seq_num}\nack_num: {self.ack_num}\nflags: {self.flags}\nchecksum: {self.checksum:b}\npayload: {self.payload}"
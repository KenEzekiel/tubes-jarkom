from connection import Connection
from segment import Segment, SegmentFlags


HOST = "127.0.0.1"
PORT = 65433

connection = Connection(HOST, PORT)

connection.send(HOST, 65432, Segment(SegmentFlags(True, False, False), 0, 0, bytes("Hello World", "utf-8")))
connection.send(HOST, 65432, Segment(SegmentFlags(True, False, False), 1, 0, b""))
#!/usr/bin/python2

from StringIO import StringIO
from pprint import pprint
import sys
import struct


class Buffer(StringIO):
    def read_uint32(self):
        b = self.read(4)
        return struct.unpack('!I', b)[0]

    def write_uint32(self, val):
        b = struct.pack('!I', val)
        self.write(b)
        return b

    def read_int32(self):
        b = self.read(4)
        return struct.unpack('!i', b)[0]

    def write_int32(self, val):
        b = struct.pack('!i', val)
        self.write(b)
        return b

    def read_int64(self):
        b = self.read(8)
        return struct.unpack('!q', b)[0]

    def write_int64(self, val):
        b = struct.pack('!q', val)
        self.write(b)
        return b

    def read_uint64(self):
        b = self.read(8)
        return struct.unpack('!Q', b)[0]

    def write_uint64(self, value):
        b = struct.pack('!Q', value)
        self.write(b)
        return b

    def read_int16(self):
        b = self.read(2)
        return struct.unpack('!h', b)[0]

    def write_int16(self, val):
        b = struct.pack('!h', val)
        self.write(b)
        return b

    def read_uint16(self):
        b = self.read(2)
        return struct.unpack('!H', b)[0]

    def write_uint16(self, val):
        b = struct.pack('!H', val)
        self.write(b)
        return b

    def read_int8(self):
        b = self.read(1)
        return struct.unpack('!b', b)[0]

    def write_int8(self, val):
        b = struct.pack('!b', val)
        self.write(b)
        return b

    def read_uint8(self):
        b = self.read(1)
        return struct.unpack('!B', b)[0]

    def write_uint8(self, val):
        b = struct.pack('B', val)
        self.write(b)
        return b


class TlvType(object):
    INT8 = 7
    UINT8 = 8
    INT16 = 9
    UINT16 = 10
    INT32 = 11
    UINT32 = 12
    BYTES = 13
    MSG = 14


class ItemParser(object):
    def __init__(self):
        self.parsers = dict()
        self.parsers[TlvType.INT8] = self.parse_int8
        self.parsers[TlvType.UINT8] = self.parse_uint8
        self.parsers[TlvType.INT16] = self.parse_int16
        self.parsers[TlvType.UINT16] = self.parse_uint16
        self.parsers[TlvType.INT32] = self.parse_int32
        self.parsers[TlvType.UINT32] = self.parse_uint32
        self.parsers[TlvType.BYTES] = self.parse_bytes
        self.parsers[TlvType.MSG] = self.parse_msg

    def parse_msg(self, data):
        return Message.unpack(data)

    def parse_int8(self, data):
        return Buffer(data).read_int8()

    def parse_uint8(self, data):
        return Buffer(data).read_uint8()

    def parse_int16(self, data):
        return Buffer(data).read_int16()

    def parse_uint16(self, data):
        return Buffer(data).read_uint16()

    def parse_int32(self, data):
        return Buffer(data).read_int32()

    def parse_uint32(self, data):
        return Buffer(data).read_uint32()

    def parse_bytes(self, data):
        return data

    def parse_item(self, item_type, data):
        parser = self.parsers[item_type]
        return parser(data)

    def object_to_tlv(self, value):
        class Tlv(object):
            pass
        tlv = Tlv()
        if isinstance(value, int):
            bits = value.bit_length()
            if (0 <= bits) and (8 >= bits):
                tlv.size = 1
                tlv.type = TlvType.UINT8
                tlv.value = Buffer().write_uint8(value)
            elif (9 <= bits) and (16 >= bits):
                tlv.size = 2
                tlv.type = TlvType.UINT16
                tlv.value = Buffer().write_uint16(value)
            elif (17 <= bits) and (32 >= bits):
                tlv.size = 4
                tlv.type = TlvType.UINT32
                tlv.value = Buffer().write_uint32(value)
            else:
                raise ValueError('supported values are 8bit, 16bit, and 32bit')
        elif isinstance(value, str):
            tlv.size = len(value)
            tlv.type = TlvType.BYTES
            tlv.value = value
        elif isinstance(value, Message):
            tlv.type = TlvType.MSG
            tlv.value = value.pack()
            tlv.size = len(tlv.value)
        else:
            raise TypeError('supported types: int, str, Message')

        return tlv


class ItemID(dict):
    ID_PERSON = 1
    ID_PERSON_NAME = 2
    ID_PERSON_AGE = 3
    ID_PERSON_NKIDS = 4
    ID_PERSON_KIDS = 5

    def __init__(self):
        super(ItemID, self).__init__()
        self[ItemID.ID_PERSON] = "Person"
        self["Person"] = ItemID.ID_PERSON
        self[ItemID.ID_PERSON_NAME] = "Name"
        self["Name"] = ItemID.ID_PERSON_NAME
        self[ItemID.ID_PERSON_AGE] = "Age"
        self['Age'] = ItemID.ID_PERSON_AGE
        self[ItemID.ID_PERSON_NKIDS] = "#kids"
        self["#kids"] = ItemID.ID_PERSON_NKIDS
        self[ItemID.ID_PERSON_KIDS] = "Kids"
        self["Kids"] = ItemID.ID_PERSON_KIDS


class Message(list):
    MAGIC = 0x12345678

    def get_packed_size(self):
        pass

    def pack(self):
        stream = Buffer()
        parser = ItemParser()
        id_parser = ItemID()
        stream.write_int32(self.MAGIC)
        stream.write_int32(len(self))
        for key, value in self:
            stream.write_int16(id_parser[key])
            tlv = parser.object_to_tlv(value)
            stream.write_int16(tlv.type)
            stream.write_int16(tlv.size)
            stream.write(tlv.value)
        return stream.getvalue()

    @classmethod
    def unpack(cls, buf):
        stream = Buffer(buf)
        parser = ItemParser()
        id_parser = ItemID()
        msg = Message()
        magic = stream.read_int32()
        errmsg = 'Missing magic from buffer. expected %s, found %s' % (hex(Message.MAGIC), hex(magic))
        assert magic == Message.MAGIC, errmsg
        nitems = stream.read_int32()
        for index in xrange(nitems):
            itemid = stream.read_int16()
            itemid = id_parser[itemid]
            item_type = stream.read_int16()
            size = stream.read_int16()
            item_data = stream.read(size)
            msg.append((itemid, parser.parse_item(item_type, item_data)))
        leftover = stream.read()
        if 0 != len(leftover):
            print 'found %d trailing bytes while parsing' % (len(leftover), )
        return msg


def main():
    packed = open(sys.argv[1], 'rb').read()
    msg = Message.unpack(packed)
    pprint(msg)
    newmsg = msg.pack()
    newmsg = Message.unpack(newmsg)
    return 0

if __name__ == '__main__':
    sys.exit(main())

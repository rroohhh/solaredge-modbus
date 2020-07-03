#!/usr/bin/env python3

from sortedcontainers import SortedDict
import struct
from pymodbus.client.sync import ModbusTcpClient
from influxdb import InfluxDBClient
import datetime

MODBUSIP = 'solaredge.lan'
MODBUSPORT = '1502'

INFLUXDBIP = 'localhost'
INFLUXDBPORT = 8086
INFLUXDBUSER = 'root'
INFLUXDBPASS = 'root'
INFLUXDBDB = 'pv_monitoring'


regs = SortedDict()

with open("sunspec.tsv") as f:
    next(f) # skip header
    for l in f:
        address, size, name, ty, units, desc = l.split('\t')
        address = address.strip()
        size = size.strip()
        name = name.strip()
        ty = ty.strip()
        units = units.strip()
        desc = desc.strip()

        regs[int(address)] = {"size": int(size), "name": name, "type": ty, "units": units, "desc": desc }

with open("power.tsv") as f:
    next(f) # skip header
    for l in f:
        address, size, rw, name, ty, value_range, units = l.split('\t')
        address = address.strip()
        size = size.strip()
        rw = rw.strip()
        name = name.strip()
        ty = ty.strip()
        value_range = value_range.strip()
        units = units.strip()

        regs[int(address, 16)] = {"size": int(size), "name": name, "type": ty, "units": units, "range": value_range, "rw": rw }

blocks = []
regs_for_block = SortedDict()

first_addr = regs.keys()[0]
block_start = first_addr
next_address = first_addr + regs[first_addr]["size"]
regs_for_block[first_addr] = regs[first_addr]

for addr, reg in regs.items()[1:]:
    if next_address == addr:
        regs_for_block[addr] = reg
        next_address += reg["size"]
    elif next_address < addr:
        blocks.append((block_start, next_address - block_start, regs_for_block))


        regs_for_block = SortedDict()

        block_start = addr
        next_address = addr + reg["size"]
        regs_for_block[addr] = reg
    else:
        print("overlapping regs at:", addr)
        exit(-1)

def read_block(client, start, size):
    result = []
    while size > 0:
        to_read = min(76, size) # important, only value I found that does not end up in the middle of some big register and thus fails
        result += client.read_holding_registers(start, count=to_read, unit=1).registers
        size -= to_read
        start += to_read

    return bytes(b for i in result for b in [i >> 8, i & 0xff])

client = ModbusTcpClient(host=MODBUSIP, port=MODBUSPORT, timeout=1)

def decode(ty, data):
    orig = ty
    ty = ty.lower()

    if ty == "uint16":
        return struct.unpack('!H', data)[0]
    elif ty == "int16":
        return struct.unpack('!h', data)[0]
    elif ty == "uint32":
        if orig == "Uint32":
            data = bytes([data[2], data[3], data[0], data[1]])
        return struct.unpack('!I', data)[0]
    elif ty == "acc32":
        return struct.unpack('!I', data)[0]
    elif ty == "int32":
        if orig == "Int32":
            data = bytes([data[2], data[3], data[0], data[1]])
        return struct.unpack('!i', data)[0]
    elif ty == "uint64":
        return struct.unpack('!Q', data)[0]
    elif ty == "float32":
        data = bytes([data[2], data[3], data[0], data[1]])
        return struct.unpack('!f', data)[0]
    elif ty.startswith("string"):
        return data.decode('utf-8')
    else:
        return None
        # print("unknown type", ty)
        # exit(-1)

values = {}

for start, size, regs in blocks:
    try:
        data = read_block(client, start, size)
        for addr, reg in regs.items():
            reg_data = data[2 * (addr - start):2 * (addr - start +  reg["size"])]

            if reg["name"].lower() != "reserved":
                val = decode(reg["type"], reg_data)
                if val is not None:
                    values[reg["name"]] = val
                continue
    except AttributeError:
        continue

data = [{
    "measurement": "pv_monitoring",
    "time": datetime.datetime.now().astimezone().isoformat()
}]
data[0]["fields"] = values

client = InfluxDBClient(INFLUXDBIP, INFLUXDBPORT, INFLUXDBUSER, INFLUXDBPASS, INFLUXDBDB)
client.write_points(data)

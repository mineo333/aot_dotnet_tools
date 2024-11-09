from binaryninja import *
import ctypes


'''
Random utility classes that make working with the binary a little easier

'''

READER = None

def read8(address): 
    global READER
    return READER.read8(address)  

def read16(address):
    global READER
    return READER.read16(address)

def read32(address):
    global READER
    return READER.read32(address)

def read64(address):
    global READER
    return READER.read64(address)

def read(address, read_len):
    global READER
    return READER.read(read_len, address)

#convert an unsigned byte to a signed byte
def s8(val): 
    return ctypes.c_byte(val & 0xff).value

def u8(val):
    return ctypes.c_ubyte(val & 0xff).value

def s32(val):
    return ctypes.c_int(val & 0xffffffff).value

def u32(val):
    return ctypes.c_uint(val & 0xffffffff).value

def s64(val):
    return ctypes.c_long(val).value

def u64(val):
    return ctypes.c_ulong(val).value

def u16(val):
    return ctypes.c_ushort(val).value
    
def s16(val):
    return ctypes.c_short(val).value

def initialize_utils(bv):
    global READER
    READER = bv.reader(0)
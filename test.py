import ctypes

#convert an unsigned byte to a signed byte
def s8(val): 
    return ctypes.c_byte(val & 0xff).value

def u8(val):
    return ctypes.c_ubyte(val & 0xff).value

def s32(val):
    return ctypes.c_int(val & 0xffffffff).value

a = 0xfb
b = 0x5d
c = 0x07

print((s32(s8(c)) << 13))

value = (s32(a) >> 3) | (s32(b) << 5) | (s32(s8(c)) << 13)
print(value)
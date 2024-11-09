from binaryninja import *
from ..utils import *

#The nativeformat reading for the primitives are generated manually here: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/MdBinaryReader.cs

#The c# primitive type to primtive type name map can be found here: https://github.com/dotnet/runtime/blob/e133fe4f5311c0397f8cc153bada693c48eb7a9f/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator/SchemaDef.cs#L197

#These are primitive wrappers so they don't return objects, instead they return the underlying primitive

class Boolean:
    SIZE = 1
    def Read(reader, offset):
        value = reader.ReadUInt8(offset)
        return (offset+1, value == 1)

#String is technically not a primitive but its in the same file
class String:
    def Read(reader, offset):
        return reader.DecodeString(offset)

class Char:
    SIZE = 1
    def Read(reader, offset):
        value = reader.ReadUInt8(offset)
        return (offset+1, value)

# AKA short
class Int16:
    SIZE = 2
    def Read(reader, offset):
        (offset, value) = reader.DecodeSigned(offset)
        return (offset, s16(value))

class SByte:
    SIZE = 1
    def Read(reader, offset):
        value = reader.ReadUInt8(offset)
        return (offset+1, s8(value))

#AKA ulong
class UInt64:
    SIZE = 8
    def Read(reader, offset):
        (offset, value) = reader.DecodeUnsignedLong(offset)
        return (offset, u64(value))

#AKA int 
class Int32:
    SIZE = 4
    def Read(reader, offset):
        (offset, value) = reader.DecodeSigned(offset)
        return (offset, s32(value))
    
#AKA uint
class UInt32:
    SIZE = 4
    def Read(reader, offset):
        (offset, value) = reader.DecodeUnsigned(offset)
        return (offset, u32(value))

class Byte:
    SIZE = 1
    def Read(reader, offset):
        value = reader.ReadUInt8(offset)
        return (offset+1, value)

#AKA ushort
class UInt16:
    SIZE = 2
    def Read(reader, offset):
        (offset, value) = reader.DecodeUnsigned(offset)
        return (offset, u16(value))

#AKA long
class Int64:
    SIZE = 8
    def Read(reader, offset):
        (offset, value) = reader.DecodeSignedLong(offset)
        return (offset, s64(value))
    

    
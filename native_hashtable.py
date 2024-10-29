from binaryninja import *
import struct
import ctypes
from enum import IntEnum
#CONSTANTS 

#pulled from: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/nativeaot/Runtime/inc/ModuleHeaders.h#L10
READY_TO_RUN_SIG = b'\x52\x54\x52\x00'

#pulled from: https://github.com/dotnet/runtime/blob/cca022b6212f33adc982630ab91469882250256c/src/coreclr/tools/Common/Internal/Runtime/MetadataBlob.cs#L6 - Note that 300 is added to all these numbers
METHOD_TO_ENTRYPOINT_MAP_SECTION_ID = 306

#pulled from: https://github.com/dotnet/runtime/blob/cca022b6212f33adc982630ab91469882250256c/src/coreclr/tools/Common/Internal/Runtime/MetadataBlob.cs#L6 - Note that 300 is added to all these numbers
COMMON_FIXUPS_TABLE = 308

MASK_64 = 0xffffffffffffffff


# Pulled from: https://github.com/dotnet/runtime/blob/main/src/coreclr/tools/Common/Internal/Runtime/MappingTableFlags.cs#L21
class InvokeTableFlags(IntEnum):
    HasVirtualInvoke = 0x00000001
    IsGenericMethod = 0x00000002
    HasMetadataHandle = 0x00000004
    IsDefaultConstructor = 0x00000008
    RequiresInstArg = 0x00000010
    HasEntrypoint = 0x00000020
    IsUniversalCanonicalEntry = 0x00000040
    NeedsParameterInterpretation = 0x00000080
    CallingConventionDefault = 0x00000000
    Cdecl = 0x00001000
    Winapi = 0x00002000
    StdCall = 0x00003000
    ThisCall = 0x00004000
    FastCall = 0x00005000
    CallingConventionMask = 0x00007000



#END CONSTANTS
sections = None
#define needed types
def initialize_types():
    #pulled from: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/nativeaot/Runtime/inc/ModuleHeaders.h#L10
    if bv.get_type_by_name('ReadyToRunHeader') is None:
        ready_to_run_builder = StructureBuilder.create()
        ready_to_run_builder.append(Type.int(4, False), 'Signature')
        ready_to_run_builder.append(Type.int(2, False), 'MajorVersion')
        ready_to_run_builder.append(Type.int(2, False), 'MinorVersion')
        ready_to_run_builder.append(Type.int(4, False), 'Flags')
        ready_to_run_builder.append(Type.int(2, False), 'NumberOfSections')
        ready_to_run_builder.append(Type.int(1, False), 'EntrySize')
        ready_to_run_builder.append(Type.int(1, False), 'EntryType')
        bv.define_type(Type.generate_auto_type_id('source', 'ReadyToRunHeader'), 'ReadyToRunHeader', ready_to_run_builder.immutable_copy())
    else:
        print('ReadyToRunHeader already exists')
    #pulled from: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/nativeaot/Runtime/TypeManager.h#L27
    if bv.get_type_by_name('ModuleInfoRow') is None:
        module_info_row = StructureBuilder.create()
        module_info_row.append(Type.int(4), 'SectionId')
        module_info_row.append(Type.int(4), 'Flags')
        module_info_row.append(Type.pointer(bv.arch, Type.void()), 'Start')
        module_info_row.append(Type.pointer(bv.arch, Type.void()), 'End')
        bv.define_type(Type.generate_auto_type_id('source', 'ModuleInfoRow'), 'ModuleInfoRow', module_info_row.immutable_copy())
    else:
        print('ModuleInfoRow already exists')


READER = bv.reader(0)

#TODO: Change this so that we are not allocating objects every time 
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


def initialize_rtr():
    global sections
    #the objective here is to find and parse the ReadyToRun header
    rdata_address = bv.sections['.rdata'].start #the ReadyToRun header is always in rdata
    ready_to_run_header = bv.find_next_data(rdata_address, READY_TO_RUN_SIG)
    print(f'ReadyToRun Header Section: {hex(ready_to_run_header)}')
    bv.define_data_var(ready_to_run_header, 'ReadyToRunHeader') #define as a ReadyToRunHeader
    header_val = bv.get_data_var_at(ready_to_run_header).value
    major_version = header_val['MajorVersion']
    minor_version = header_val['MinorVersion']
    print(f'Major Version: {major_version}, Minor Version: {minor_version}')
    section_header_start = ready_to_run_header + bv.get_data_var_at(ready_to_run_header).type.width
    bv.define_data_var(section_header_start, Type.array(bv.get_type_by_name('ModuleInfoRow'), header_val['NumberOfSections']))
    sections = bv.get_data_var_at(section_header_start).value
    
    

def find_section_start_end(section_id):
    global sections
    for section in sections:
        if section['SectionId'] == section_id:
            return (section['Start'], section['End'])
        
        
#https://github.com/dotnet/runtime/blob/main/src/coreclr/nativeaot/Common/src/Internal/Runtime/TypeLoader/ExternalReferencesTable.cs#L15
class ExternalReferencesTable:
    def __init__(self, section_id):
        (start, end) = find_section_start_end(section_id)
        self.elements = start
        self.elementsCount = (end-start)//4
    def GetIntPtrFromIndex(self, idx):
        return self.GetAddressFromIndex(idx)

    def GetFunctionPointerFromIndex(self, idx):
        return self.GetAddressFromIndex(idx)
    
    def GetRuntimeTypeHandleFromIndex(self, idx):
        return self.GetAddressFromIndex(idx) #update this impl if needed
    
    def GetAddressFromIndex(self, idx):
        #in this case, we use the relative pointer version
        if idx >= self.elementsCount:
            raise ValueError('Bad Image Format Exception')
        
        pRelPtr32 = self.elements + idx*4
        return pRelPtr32 + s64(s32(read32(pRelPtr32)))


#pulled from: https://github.com/dotnet/runtime/blob/cca022b6212f33adc982630ab91469882250256c/src/coreclr/tools/Common/Internal/NativeFormat/NativeFormatReader.cs#L217
#This also integrates the functionality of NativePrimitiveDecoder: https://github.com/dotnet/runtime/blob/cca022b6212f33adc982630ab91469882250256c/src/coreclr/tools/Common/Internal/NativeFormat/NativeFormatReader.Primitives.cs#L16C36-L16C58
class NativeReader:
    def __init__(self, base, size):
        self.base = base
        self.size = size
    
    def EnsureOffsetInRange(self, offset, lookAhead):
        if(s32(offset) < 0 or (offset + lookAhead) >= self.size):
            raise ValueError('Offset out of range')
    
    def ReadUInt8(self, offset):
        self.EnsureOffsetInRange(offset, 0)
        return read8(self.base + offset)
    
    def ReadUInt16(self, offset):
        self.EnsureOffsetInRange(offset, 1)
        return read16(self.base + offset)
    
    def ReadUInt32(self, offset):
        self.EnsureOffsetInRange(offset, 3)
        return read32(self.base + offset)
    
    def ReadUInt64(self, offset):
        self.EnsureOffsetInRange(offset, 7)
        return read64(self.base + offset)
    
    def DecodeUnsigned(self, offset):
        stream = self.base + offset
        val = read8(stream)
        
        if ((val & 1) == 0):
            pvalue = val >> 1
            stream += 1
        elif ((val & 2) == 0):
            pvalue = (val >> 2) | (u32(read8(stream+1)) << 6)
            stream += 2
        elif ((val & 4) == 0):
            pvalue = (val >> 3) | (u32(read8(stream+1)) << 5) | (u32(read8(stream+2)) << 13)
            stream += 3
        elif ((val & 8) == 0):
            pvalue = (val >> 4) | (u32(read8(stream+1)) << 4) | (u32(read8(stream+2)) << 12) | (u32(read8(stream+3)) << 20)
            stream += 4
        elif ((val & 16) == 0):
            stream += 1
            pvalue = u32(read32(stream))
            stream += 4 #this 4 is from the increment in ReadUInt32
        else:
            raise ValueError("Fuck you")
        return (stream-self.base, pvalue)
    
    #returns the new offset as well as the value
    def DecodeSigned(self, offset):
        stream = self.base + offset
        #try to make the casting as deliberate as possible
        val = s32(read8(stream))  # Read the byte at the current offset

        if ((val & 1) == 0):
            pvalue = s32(s8(val) >> 1)
            stream += 1
        elif ((val & 2) == 0):
            pvalue = (val >> 2) | s32(s8(read8(stream+1)) << 6)
            stream += 2
        elif ((val & 4) == 0):
            pvalue = (s32(val) >> 3) | (s32(read8(stream+1)) << 5) | (s32(s8(read8(stream+2))) << 13)
            stream += 3
        elif ((val & 8) == 0):
            pvalue = (val >> 4) | s32(read8(stream+1)) << 4 | s32(read8(stream+2)) << 12 | s32(s8(read8(stream+3)) << 20)
            stream += 4
        elif ((val & 16) == 0):
            stream += 1
            pvalue = s32(br.read32())
            stream += 4 #this 4 is to account for the 4 bytes incremented in ReadUInt32
        else:
            raise ValueError("Fuck you")
        return (stream - self.base, pvalue)
    
    def SkipInteger(self, offset):
        val = read8(self.base + offset)
        
        if (val & 1) == 0:
            return offset + 1
        elif (val & 2) == 0:
            return offset + 2
        elif (val & 4) == 0:
            return offset + 3
        elif (val & 8) == 0:
            return offset + 4
        elif (val & 16) == 0:
            return offset + 5
        elif (val & 32) == 0:
            return offset + 9
        else:
            raise ValueError('Bad Image Format Exception')

class NativeParser:
    def __init__(self, reader, offset):
        self.offset = offset
        self.reader = reader
    
    def GetUInt8(self):
        val = self.reader.ReadUInt8(self.offset)
        self.offset += 1
        return val
    
    def GetUnsigned(self):
        (self.offset, val) = self.reader.DecodeUnsigned(self.offset)
        return val
    
    def GetSigned(self):
        (self.offset, val) = self.reader.DecodeSigned(self.offset)
        return val
    
    def GetRelativeOffset(self):
        pos = self.offset 
        (self.offset, delta) = self.reader.DecodeSigned(self.offset)
        rel_offset = u32(pos + delta)
        #print('pos', hex(pos), 'delta', delta, 'rel offset', hex(rel_offset))
        return rel_offset #reader._base + _offset + delta - this offset is associated with pos
    
    def GetParserFromRelativeOffset(self):
        return NativeParser(self.reader, self.GetRelativeOffset())

    def SkipInteger(self):
        self.offset = self.reader.SkipInteger(self.offset)
    
    def GetAddress(self):
        return self.reader.base + self.offset

   

#https://github.com/dotnet/runtime/blob/main/src/coreclr/tools/Common/Internal/NativeFormat/NativeFormatReader.cs#L456
class NativeHashTable:
    def __init__(self, parser): 
        header = parser.GetUInt8()
        self.base_offset = parser.offset 
        self.reader = parser.reader
        
        
        number_of_buckets_shift = header >> 2
        if (number_of_buckets_shift > 31):
            raise ValueError("Bad image format exception") 
        self.bucket_mask = (1 << number_of_buckets_shift) - 1

        entry_index_size = header & 3
        
        if (entry_index_size > 2):
            raise ValueError("Bad image format exception") 
        self.entry_index_size = entry_index_size
        
    
    class AllEntriesEnumerator:
        def __init__(self, table):
            self.table = table
            self.current_bucket = 0
            #self.parser is the parser for the bucekt
            #end_offset is the end of the the current bucket
            (self.parser, self.end_offset) = table.GetParserForBucket(self.current_bucket)

        def GetNext(self):
            while (True):
                while (self.parser.offset < self.end_offset):
                    #return new binary reader from current binary reader
                    self.parser.GetUInt8()
                    return self.parser.GetParserFromRelativeOffset()
                if (self.current_bucket >= self.table.bucket_mask):
                    return #the default value for an object is null
                self.current_bucket += 1
                (self.parser, self.end_offset) = self.table.GetParserForBucket(self.current_bucket)
    
    def GetParserForBucket(self, bucket): #returns the NativeParser and the endOffset
        if (self.entry_index_size == 0):
            bucket_offset = self.base_offset + bucket
            _start = self.reader.ReadUInt8(bucket_offset)
            _end = self.reader.ReadUInt8(bucket_offset + 1)
        elif (self.entry_index_size == 1):
            bucket_offset = self.base_offset + 2 * bucket
            _start = self.reader.ReadUInt16(bucket_offset)
            _end = self.reader.ReadUInt16(bucket_offset + 2)
        else:
            bucket_offset = self.base_offset + 4 * bucket
            _start = self.reader.ReadUInt32(bucket_offset)
            _end = self.reader.ReadUInt32(bucket_offset + 4)
            
        end_offset = _end + self.base_offset
        parser = NativeParser(self.reader, self.base_offset + _start)
        #print('bucket', hex(bucket), 'start', hex(_start), 'end', hex(_end))
        #print('bucket parser offset', hex(parser.offset), 'addr', hex(parser.GetAddress()), 'bucket', bucket, 'end_offset', hex(end_offset))
        return (parser, end_offset)

    
            
# br will work as our native parser
def parse_hashtable(start, end):
    reader = NativeReader(start, end-start) #create a NativeReader starting from end-start
    enumerator = NativeHashTable.AllEntriesEnumerator(NativeHashTable(NativeParser(reader, 0))) 
    print('base offset',hex(enumerator.table.reader.base + enumerator.table.base_offset))
    entryParser = enumerator.GetNext()
    externalReferences = ExternalReferencesTable(COMMON_FIXUPS_TABLE)
    while (entryParser is not None): 
        #print('New Parser, base:', hex(entryParser.GetAddress()), 'bucket:', enumerator.current_bucket)
        #this code is pulled from here: https://github.com/dotnet/runtime/blob/6ed953a000613e5b02e5ac38d35aa4fef6c38660/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L578
        
        entryFlags = entryParser.GetUnsigned()
        #if entryFlags & int(InvokeTableFlags.HasEntrypoint) == 0:
        #    continue
        entryParser.SkipInteger()
        declaringTypeHandle = externalReferences.GetRuntimeTypeHandleFromIndex(entryParser.GetUnsigned())
        entryMethodEntryPoint = externalReferences.GetFunctionPointerFromIndex(entryParser.GetUnsigned())
        print('entrypoint', hex(entryMethodEntryPoint))
        
        entryParser = enumerator.GetNext() 
        
    return

initialize_types()
initialize_rtr()
(start,end) = find_section_start_end(METHOD_TO_ENTRYPOINT_MAP_SECTION_ID)
print('__method_entrypoint_map start:', hex(start), 'end:', hex(end))
parse_hashtable(start, end)



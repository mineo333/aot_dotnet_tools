from binaryninja import *
import struct
import ctypes
#CONSTANTS 

#pulled from: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/nativeaot/Runtime/inc/ModuleHeaders.h#L10
READY_TO_RUN_SIG = b'\x52\x54\x52\x00'

#pulled from: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/tools/Common/Internal/Runtime/ModuleHeaders.cs#L93
METHOD_TO_ENTRYPOINT_MAP_SECTION_ID = 306

MASK_64 = 0xffffffffffffffff

#END CONSTANTS

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

def p8(val):
    return struct.pack('<B', val)

def p16(val):
    return struct.pack('<H', val)

def p32(val):
    return struct.pack('<I', val)

def p64(val):
    return struct.pack('<Q', val)



def find_hashtable():
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
    
    for section in sections:
        if section['SectionId'] == METHOD_TO_ENTRYPOINT_MAP_SECTION_ID:
            return (section['Start'], section['End'])

# read legnth bytes and don't increment offset
def read_no_inc(br, length):
    ret = br.read(length)
    br.seek_relative(-length)
    return ret

def decode_signed(br):
    pvalue = 0
    val = br.read8()  # Read the byte at the current offset

    if ((val & 1) == 0):
        pvalue = val >> 1
    elif ((val & 2) == 0):
        pvalue = (val >> 2) | br.read8() << 6
    elif ((val & 4) == 0):
        pvalue = (val >> 3) | br.read8() << 5 | br.read8() << 13
    elif ((val & 8) == 0):
        pvalue = (val >> 4) | br.read8() << 4 | br.read8() << 12 | br.read8() << 20
    elif ((val & 16) == 0):
        pvalue = br.read32()
        pvalue = ctypes.c_int(pvalue).value
    else:
        raise ValueError("Fuck you")
    
    return pvalue
   

def get_relative_offset(br):
    off = br.offset
    delta = decode_signed(br)
    br.seek(off + delta)

class NativeHashTable:
    def __init__(self, br):
        header = br.read8()
        self.base_offset = br.offset # should this be virtual base or offset
        self.br = br

        number_of_buckets_shift = header >> 2
        if (number_of_buckets_shift > 31):
            raise ValueError("Bad image format exception") 
        self.bucket_mask = (1 << number_of_buckets_shift) - 1

        entry_index_size = header & 3
        if (entry_index_size > 2):
            raise ValueError("Bad image format exception") 
        self.entry_index_size = entry_index_size
    
    class AllEntriesEnumerator:
        def __init__(self, table, end_offset):
            self.table = table
            self.current_bucket = 0
            self.parser = table.get_parser_for_bucket(self.current_bucket)
            self.end_offset = end_offset

        def get_next(self):
            while (True):
                while (self.parser.offset < self.end_offset):
                    self.parser.read8()
                    #return new binary reader from current binary reader
                    return bv.reader(self.parser.offset)# + get_relative_offset(self.parser))
                if (self.current_bucket >= self.table.bucket_mask):
                    return
                self.current_bucket += 1
                self.parser = self.table.get_parser_for_bucket(self.current_bucket)

    def get_parser_for_bucket(self, bucket):
            if (self.entry_index_size == 0):
                bucket_offset = self.base_offset + bucket
                _start = self.br.read8(bucket_offset)
                _end = self.br.read8(bucket_offset + 1)
            elif (self.entry_index_size == 1):
                bucket_offset = self.base_offset + 2 * bucket
                _start = self.br.read16(bucket_offset)
                _end = self.br.read16(bucket_offset + 2)
            else:
                bucket_offset = self.base_offset + 4 * bucket
                _start = self.br.read32(bucket_offset)
                _end = self.br.read32(bucket_offset + 4)
            
            self.end_offset = _end + self.base_offset
            return bv.reader(self.base_offset + _start) 
            
# br will work as our native parser
def parse_hashtable(start, end):
    br = bv.reader(start)
    print(f'offset: {hex(br.offset)}')
    print(f'virtual base: {hex(br.virtual_base)}')
    enumerator = NativeHashTable.AllEntriesEnumerator(NativeHashTable(br), end)
    _next = enumerator.get_next()
    while (_next is not None):
        print('f')
        _next = enumerator.get_next()
    
    return

initialize_types()
(start, end) = find_hashtable()
print(hex(start), hex(end))
parse_hashtable(start, end)





    


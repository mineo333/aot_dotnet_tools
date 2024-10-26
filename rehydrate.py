from binaryninja import *
import struct
import ctypes

#CONSTANTS 


#pulled from: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/nativeaot/Runtime/inc/ModuleHeaders.h#L10
READY_TO_RUN_SIG = b'\x52\x54\x52\x00'


#pulled from: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/tools/Common/Internal/Runtime/ModuleHeaders.cs#L93
DEHYDRATED_DATA_SECTION_NUM = 207

MASK_64 = 0xffffffffffffffff


#pulled from: https://github.com/dotnet/runtime/blob/d450d9c9ee4dd5a98812981dac06d2f92bdb8213/src/coreclr/tools/Common/Internal/Runtime/DehydratedData.cs#L64

DehydratedDataCommandMask = 0x7
DehydratedDataCommandPayloadShift = 0x3
MaxRawShortPayload = (1 << (8 - DehydratedDataCommandPayloadShift)) - 1
MaxExtraPayloadBytes = 3
MaxShortPayload = MaxRawShortPayload - MaxExtraPayloadBytes

Copy = 0x00
ZeroFill = 0x01
RelPtr32Reloc = 0x02
PtrReloc = 0x03
InlineRelPtr32Reloc = 0x04
InlinePtrReloc = 0x05
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


#find the dehydrated_data 

def find_dehydrated_data():
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
        if section['SectionId'] == DEHYDRATED_DATA_SECTION_NUM:
            return (section['Start'], section['End'])

def parse_command(br):
    b = br.read8()
    command = b & DehydratedDataCommandMask
    payload = b >> DehydratedDataCommandPayloadShift
    extra_bytes = payload - MaxShortPayload
    if extra_bytes > 0:
        payload = br.read8()
        if extra_bytes > 1:
            payload += (br.read8() << 8)
            if extra_bytes > 2:
                payload += (br.read8() << 16)
        payload += MaxShortPayload
    
    return (payload, command)




def ReadRelPtr32(br):
    #print(hex(br.offset))
    return br.offset + ctypes.c_int(br.read32()).value

def WriteRelPtr32(bw, value):
    return bw.write32(value-bw.offset)

#reimplement the following algorithm: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/nativeaot/Common/src/Internal/Runtime/CompilerHelpers/StartupCodeHelpers.cs#L247
def rehydrate_data(start, length):
    
    pEnd = start+length
    br = bv.reader(start) #br.offset is pCurrent
    fixup_br = bv.reader(pEnd) #fixup_br is for reading from pFixups
    bw = bv.writer(ReadRelPtr32(br)) #bw.offset is pDest
    bv.memory_map.remove_memory_region('hydrated_mem')
    assert bv.memory_map.add_memory_region('hydrated_mem', bw.offset, b'\x00'*length)
    print(f'VTable start: {hex(bw.offset)}')
    while br.offset < pEnd:
        (payload, command) = parse_command(br)
        #print(hex(br.offset))
        if command == Copy:
            data = br.read(payload)
            bw.write(data)
        elif command == ZeroFill:
            bw.seek_relative(payload)
        elif command == PtrReloc:
            fixup_br.seek(pEnd + payload*4)
            val = ReadRelPtr32(fixup_br)
            bw.write64(val)
        elif command == RelPtr32Reloc:
            fixup_br.seek(pEnd + payload*4)
            WriteRelPtr32(bw, ReadRelPtr32(fixup_br))
        elif command == InlinePtrReloc:
            for i in range(payload):
                val = ReadRelPtr32(br)
                bw.write64(val)
        elif command == InlineRelPtr32Reloc:
            for i in range(payload):
                WriteRelPtr32(bw, ReadRelPtr32(br))
    
        
def detect_pointers(): #this function works best rebased
    br = bv.reader(bv.sections['hydrated'].start)
    
    while br.offset < bv.sections['hydrated'].end:
        potential_ptr = br.read64()
        if bv.start <= potential_ptr < bv.end:
            bv.define_data_var(br.offset, Type.pointer(bv.arch, Type.void()))




initialize_types()
(start, end) = find_dehydrated_data()
print(hex(start), hex(end))

rehydrate_data(start, end-start)
detect_pointers()




    


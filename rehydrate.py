from binaryninja import *
import struct
import ctypes
from .rtr import *

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
def rehydrate_data(bv, start, length):
    
    pEnd = start+length
    br = bv.reader(start) #br.offset is pCurrent
    fixup_br = bv.reader(pEnd) #fixup_br is for reading from pFixups
    bw = bv.writer(ReadRelPtr32(br)) #bw.offset is pDest
    bv.memory_map.remove_memory_region('hydrated_mem')
    assert bv.memory_map.add_memory_region('hydrated_mem', bw.offset, b'\x00'*length)
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
    
        
def detect_pointers(bv): #this function works best rebased
    br = bv.reader(bv.sections['hydrated'].start)
    
    while br.offset < bv.sections['hydrated'].end:
        potential_ptr = br.read64()
        if bv.start <= potential_ptr < bv.end:
            bv.define_data_var(br.offset, Type.pointer(bv.arch, Type.void()))


def do_rehydration(bv):
    (start, end) = find_section_start_end(ReadyToRunSectionType.DehydratedData)
    rehydrate_data(bv, start, end-start)
    detect_pointers(bv)




    


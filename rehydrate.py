from binaryninja import *
import struct
import ctypes
from .rtr import *

#https://github.com/dotnet/runtime/blob/d450d9c9ee4dd5a98812981dac06d2f92bdb8213/src/coreclr/tools/Common/Internal/Runtime/DehydratedData.cs#L20
class DehydratedDataCommand:
    def __init__(self):
        pass
    
    Copy = 0x00
    ZeroFill = 0x01
    RelPtr32Reloc = 0x02
    PtrReloc = 0x03
    InlineRelPtr32Reloc = 0x04
    InlinePtrReloc = 0x05

    DehydratedDataCommandMask = 0x7
    DehydratedDataCommandPayloadShift = 0x3
    MaxRawShortPayload = (1 << (8 - DehydratedDataCommandPayloadShift)) - 1
    MaxExtraPayloadBytes = 3
    MaxShortPayload = MaxRawShortPayload - MaxExtraPayloadBytes

    def Decode(self, pB):
        b = pB.read8()
        command = b & self.DehydratedDataCommandMask
        payload = b >> self.DehydratedDataCommandPayloadShift
        extra_bytes = payload - self.MaxShortPayload
        if extra_bytes > 0:
            payload = pB.read8()
            if extra_bytes > 1:
                payload += (pB.read8() << 8)
                if extra_bytes > 2:
                    payload += (pB.read8() << 16)
            payload += self.MaxShortPayload
        
        return (payload, command)

def ReadRelPtr32(br):
    #print(hex(br.offset))
    return br.offset + ctypes.c_int(br.read32()).value

def WriteRelPtr32(bw, value):
    return bw.write32(value-bw.offset)

#reimplement the following algorithm: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/nativeaot/Common/src/Internal/Runtime/CompilerHelpers/StartupCodeHelpers.cs#L247
def RehydrateData(bv, start, length):
    pEnd = start+length
    pCurrentReader = bv.reader(start) #pCurrentReader.offset is pCurrent
    FixupBr = bv.reader(pEnd) #FixupBr is for reading from pFixups
    pDestReader = bv.writer(ReadRelPtr32(pCurrentReader)) #pDestReader.offset is pDest

    bv.memory_map.remove_memory_region('hydrated_mem')
    assert bv.memory_map.add_memory_region('hydrated_mem', pDestReader.offset, b'\x00'*length)

    while pCurrentReader.offset < pEnd:
        (payload, command) = DehydratedDataCommand.Decode(DehydratedDataCommand, pCurrentReader)
        #print(hex(br.offset))
        match command:
            case DehydratedDataCommand.Copy:
                data = pCurrentReader.read(payload)
                pDestReader.write(data)

            case DehydratedDataCommand.ZeroFill:
                pDestReader.seek_relative(payload)

            case DehydratedDataCommand.PtrReloc:
                FixupBr.seek(pEnd + payload*4)
                val = ReadRelPtr32(FixupBr)
                pDestReader.write64(val)

            case DehydratedDataCommand.RelPtr32Reloc:
                FixupBr.seek(pEnd + payload*4)
                WriteRelPtr32(pDestReader, ReadRelPtr32(FixupBr))

            case DehydratedDataCommand.InlinePtrReloc:
                for i in range(payload):
                    val = ReadRelPtr32(pCurrentReader)
                    pDestReader.write64(val)

            case DehydratedDataCommand.InlineRelPtr32Reloc:
                for i in range(payload):
                    WriteRelPtr32(pDestReader, ReadRelPtr32(pCurrentReader))
        
def detect_pointers(bv): #this function works best rebased
    br = bv.reader(bv.sections['hydrated'].start)
    
    while br.offset < bv.sections['hydrated'].end:
        potential_ptr = br.read64()
        if bv.start <= potential_ptr < bv.end:
            bv.define_data_var(br.offset, Type.pointer(bv.arch, Type.void()))


def do_rehydration(bv):
    (start, end) = find_section_start_end(ReadyToRunSectionType.DehydratedData)
    RehydrateData(bv, start, end-start)
    detect_pointers(bv)




    


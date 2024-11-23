from binaryninja import *
from .rtr import *
from .utils import *
from .dotnet_enums import *
from .autogen.autogen_nativeformat import *
from .nativeformat import *


def ReadRelPtr32(address):
    return address + s32(read32(address))


#based on this method: https://github.com/dotnet/runtime/blob/55eee324653e01cf28809d02b25a5b0894b58d22/src/coreclr/nativeaot/System.Private.StackTraceMetadata/src/Internal/StackTraceMetadata/StackTraceMetadata.cs#L323
def stacktrace_metadata_dumper():
    currentOwningType = None
    currentSignature = None
    currentName = None
    currentMethodInst = None
    metadata_reader = METADATA_READER()
    (rvaToTokenMapBlob, rvaToTokenMapBlob_end) = find_section_start_end(ReflectionMapBlob.BlobIdStackTraceMethodRvaToTokenMapping)
    
    reader = NativeReader(rvaToTokenMapBlob, rvaToTokenMapBlob_end-rvaToTokenMapBlob)
    parser = NativeParser(reader, 0)
    entryCount = s32(parser.GetUInt32())
    while parser.GetAddress() < rvaToTokenMapBlob_end:
        command = StackTraceDataCommand(parser.GetUInt8())
        
        if StackTraceDataCommand.UpdateOwningType in command:
            currentOwningType = Handle(s32(parser.GetUInt32()))
            assert currentOwningType.hType == HandleType.TypeDefinition or currentOwningType.hType == HandleType.TypeReference or currentOwningType.hType == HandleType.TypeSpecification
            
        if StackTraceDataCommand.UpdateName in command:
            val = s32(parser.GetUnsigned())
            currentName = ConstantStringValueHandle(Handle(val, hType=HandleType.ConstantStringValue))
            
        if StackTraceDataCommand.UpdateSignature in command:
            val = s32(parser.GetUnsigned())
            #val = val | HandleType.MethodSignature << 24 #manually construct handle
            currentSignature = Handle(val, hType=HandleType.MethodSignature)
            currentMethodInst = None
        
        if StackTraceDataCommand.UpdateGenericSignature in command:
            val = s32(parser.GetUnsigned())
            #val = val | HandleType.MethodSignature << 24 #manually construct handle
            currentSignature = Handle(val, hType=HandleType.MethodSignature)
            val = s32(parser.GetUnsigned())
            #val = val | HandleType.ConstantStringArray << 24 #manually construct handle
            currentMethodInst = Handle(val, hType=HandleType.ConstantStringArray)
        
        pMethod = ReadRelPtr32(parser.GetAddress())
        parser.Seek(4)
        nameStr = currentName.GetConstantStringValue(metadata_reader)
        
        print('pMethod:', hex(pMethod))
        print('Name', nameStr)
        
        
        
    
from binaryninja import *
from .rtr import *
from .utils import *
from .dotnet_enums import *
from .autogen.autogen_nativeformat import *
from .nativeformat import *


def ReadRelPtr32(address):
    return address + s32(read32(address))


#based on this method: https://github.com/dotnet/runtime/blob/55eee324653e01cf28809d02b25a5b0894b58d22/src/coreclr/nativeaot/System.Private.StackTraceMetadata/src/Internal/StackTraceMetadata/StackTraceMetadata.cs#L323
def stacktrace_metadata_dumper(bv):
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
            currentSignature = Handle(val, hType=HandleType.MethodSignature)
            val = s32(parser.GetUnsigned())
            currentMethodInst = Handle(val, hType=HandleType.ConstantStringArray)
        
        pMethod = ReadRelPtr32(parser.GetAddress())
        parser.Seek(4)
        nameStr = currentName.GetConstantStringValue(metadata_reader)
        
        print('pMethod:', hex(pMethod))
        print('Name', nameStr)
        if currentOwningType.hType == HandleType.TypeDefinition:
            typeDefinition = TypeDefinitionHandle(currentOwningType).GetTypeDefinition(metadata_reader)
            owning_type = typeDefinition.get_name(metadata_reader)
            print('Owning type', owning_type)
        elif currentOwningType.hType == HandleType.TypeReference:
            typeReference = TypeReferenceHandle(currentOwningType).GetTypeReference(metadata_reader)
            owning_type = typeReference.get_name(metadata_reader)
            print('Owning type', typeReference.get_name(metadata_reader))
        elif currentOwningType.hType == HandleType.TypeSpecification:
            typeSpecifiction = TypeSpecificationHandle(currentOwningType).GetTypeSpecification(metadata_reader)
            owning_type = typeSpecifiction.get_name(metadata_reader)
            print('Type specification', owning_type)
        bv.add_function(pMethod) # add funciton if one doesn't already exist at pMethod
        func = bv.get_function_at(pMethod)
        if func:
            #if func.name.startswith('sub_'):
            func.name = f'{owning_type}::{str(nameStr)}' #don't replace debugging/user generated names
            #print(func.name)
        else:
            print('No function found at address', pMethod)
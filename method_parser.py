from binaryninja import *
import struct
import ctypes
from enum import IntEnum, Flag
from .dotnet_enums import *
from .nativeformat import *
from .rtr import *
from .handles import *
from .misc import *

#this comes from here: https://github.com/dotnet/runtime/blob/c43fc8966036678d8d603bdfbd1afd79f45b420b/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L643
def parse_invokemap(invokeMapStart, invokeMapEnd):
    reader = NativeReader(invokeMapStart, invokeMapEnd-invokeMapStart) #create a NativeReader starting from end-start
    enumerator = NativeHashTable.AllEntriesEnumerator(NativeHashTable(NativeParser(reader, 0))) 
    
    #entryParser = enumerator.GetNext()
    externalReferences = ExternalReferencesTable(ReflectionMapBlob.CommonFixupsTable)
    for entryParser in enumerator: 
        entryFlags = entryParser.GetUnsigned()
        
        if entryFlags & InvokeTableFlags.HasEntrypoint == 0: #its only a method if it has entrypoint
            continue
            
        entryMethodHandleOrNameAndSigRaw = entryParser.GetUnsigned()
        entryDeclaringTypeRaw = entryParser.GetUnsigned()

        entryMethodEntryPoint = externalReferences.GetFunctionPointerFromIndex(entryParser.GetUnsigned())
        print('entryMethodEntryPoint', hex(entryMethodEntryPoint))

        if entryFlags & InvokeTableFlags.NeedsParameterInterpretation == 0:
            entryParser.SkipInteger()



        if entryFlags & InvokeTableFlags.RequiresInstArg == 0:
            declaringTypeHandle = externalReferences.GetRuntimeTypeHandleFromIndex(entryDeclaringTypeRaw)
        else:
            continue
        
        print('declaringTypeHandle', declaringTypeHandle)
        
        if entryFlags & int(InvokeTableFlags.HasMetadataHandle) != 0:
            declaringTypeHandleDefinition = ExecutionEnvironmentImplementation.GetTypeDefinition(declaringTypeHandle)
            if declaringTypeHandle != declaringTypeHandleDefinition:
                print('declaringTypeHandleDefinition', declaringTypeHandleDefinition)
            qTypeDefinition = ExecutionEnvironmentImplementation.GetMetadataForNamedType(declaringTypeHandleDefinition)
            nativeFormatMethodHandle = MethodHandle((HandleType.Method << 24) | entryMethodHandleOrNameAndSigRaw)
            methodHandle = QMethodDefinition(qTypeDefinition.NativeFormatReader, nativeFormatMethodHandle)
            method = methodHandle.handle.GetMethod(METADATA_READER())
            print('name', method.name.GetConstantStringValue(METADATA_READER()))
        
    return


def parse_methods():
    create_metadata_reader()
    (start,end) = find_section_start_end(ReflectionMapBlob.InvokeMap)
    parse_invokemap(start, end)








#pulled from: https://github.com/dotnet/runtime/blob/6ed953a000613e5b02e5ac38d35aa4fef6c38660/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L578, this basically fills _ldftnReverseLookup_InvokeMap
#NOTE: actually setting _ldftnReverseLookup_InvokeMap is done here: https://github.com/dotnet/runtime/blob/6ed953a000613e5b02e5ac38d35aa4fef6c38660/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L498C17-L498C46

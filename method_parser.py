from binaryninja import *
from .dotnet_enums import *
from .nativeformat import *
from .rtr import *
from .autogen.autogen_nativeformat import *
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

def get_all_methods():
    metadata_reader = METADATA_READER()
    scope_definitions = metadata_reader.header.SCOPE_DEFINITIONS
    bfs = list() #list of namespace definition handles
    
    for scope_definition_handle in scope_definitions.GetEnumerator():
        scope_defintion = scope_definition_handle.GetScopeDefinition(metadata_reader)
        print(scope_defintion.name.GetConstantStringValue(metadata_reader))
        #if 'fullspeed' in str(scope_defintion.name.GetConstantStringValue(metadata_reader)):
        bfs.append(scope_defintion.rootNamespaceDefinition)
        
    
    while len(bfs) != 0:
        elem = bfs[0]
        bfs = bfs[1:]
        ns_def = elem.GetNamespaceDefinition(metadata_reader)
        try:
            print(ns_def.name.GetConstantStringValue(metadata_reader))
        except:
            pass
        
        for type_def_handle in ns_def.typeDefinitions.GetEnumerator():
            type_def = type_def_handle.GetTypeDefinition(metadata_reader)
            print('type', type_def.name.GetConstantStringValue(metadata_reader))
            for method_handle in type_def.methods.GetEnumerator():
                method = method_handle.GetMethod(metadata_reader)
                print('method', method.name.GetConstantStringValue(metadata_reader))
            
            for nested_type_handle in type_def.nestedTypes.GetEnumerator():
                nested_type_def = nested_type_handle.GetTypeDefinition(metadata_reader)
                print('nested type', nested_type_def.name.GetConstantStringValue(metadata_reader))
        
        for ns_def_handle in ns_def.namespaceDefinitions.GetEnumerator():
            bfs.append(ns_def_handle)

def get_all_types():
    metadata_reader = METADATA_READER()
    (typeMapStart, typeMapEnd) = find_section_start_end(ReflectionMapBlob.TypeMap)
    typeMapReader = NativeReader(typeMapStart, typeMapEnd-typeMapStart)
    typeMapParser = NativeParser(typeMapReader, 0)
    typeMapHashtable = NativeHashTable(typeMapParser)
    externalReferences = ExternalReferencesTable(ReflectionMapBlob.CommonFixupsTable)
    enumerator = NativeHashTable.AllEntriesEnumerator(typeMapHashtable) 
    for entryParser in enumerator:
        idx = entryParser.GetUnsigned()
        typeHandle = externalReferences.GetRuntimeTypeHandleFromIndex(idx)
        print(typeHandle)
        hVal = entryParser.GetUnsigned()
        entryMetadataHandle = Handle(hVal)
        if entryMetadataHandle.hType == HandleType.TypeDefinition:
            typedef_handle = TypeDefinitionHandle(hVal)
            type_def = typedef_handle.GetTypeDefinition(metadata_reader)
            print('type', type_def.name.GetConstantStringValue(metadata_reader))
            print('num methods', type_def.methods.count)
            
            for method_handle in type_def.methods.GetEnumerator():
                method = method_handle.GetMethod(metadata_reader)
                print('method', method.name.GetConstantStringValue(metadata_reader))
            
            for nested_type_handle in type_def.nestedTypes.GetEnumerator():
                nested_type_def = nested_type_handle.GetTypeDefinition(metadata_reader)
                print('nested type', nested_type_def.name.GetConstantStringValue(metadata_reader))
        


def brute_force(offset, HandleType):
    metadata_reader = METADATA_READER()
    streamReader = metadata_reader.streamReader
    endOffset = streamReader.size
    for i in range(endOffset): #check every possible offset for our target value
        try:
            (_,handle) = Handle.Read(streamReader, i)
        except:
            continue
        if handle.Offset == offset:
            print('found handle at offset', hex(i))
            print('address', hex(streamReader.base + i))
    print('Could find the offset')

def parse_methods():
    create_metadata_reader()
    (start,end) = find_section_start_end(ReflectionMapBlob.InvokeMap)
    #parse_invokemap(start, end)
    #get_all_methods()
    #get_all_types()
    brute_force(0xc9b3, ConstantStringValueHandle)








#pulled from: https://github.com/dotnet/runtime/blob/6ed953a000613e5b02e5ac38d35aa4fef6c38660/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L578, this basically fills _ldftnReverseLookup_InvokeMap
#NOTE: actually setting _ldftnReverseLookup_InvokeMap is done here: https://github.com/dotnet/runtime/blob/6ed953a000613e5b02e5ac38d35aa4fef6c38660/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L498C17-L498C46

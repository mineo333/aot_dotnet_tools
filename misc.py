from binaryninja import *
from .nativeformat import *
from .utils import *
from .rtr import *
from .handles import *
from .flags import *

'''
random, but important classes that don't really have a place
'''

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
        return RuntimeAugments.CreateRuntimeTypeHandle(self.GetIntPtrFromIndex(idx))
    
    def GetAddressFromIndex(self, idx):
        #in this case, we use the relative pointer version
        if idx >= self.elementsCount:
            raise ValueError('Bad Image Format Exception')
        
        pRelPtr32 = self.elements + idx*4
        return pRelPtr32 + s64(s32(read32(pRelPtr32))) 

#https://github.com/dotnet/runtime/blob/main/src/coreclr/nativeaot/System.Private.CoreLib/src/Internal/Runtime/Augments/RuntimeAugments.cs#L37
class RuntimeAugments:
    def CreateRuntimeTypeHandle(ldTokenResult):
        return RuntimeTypeHandle(ldTokenResult)
    
    def IsGenericType(typeHandle):
        m_uFlags = u64(read64(typeHandle.val + 0xb8))
        if not m_uFlags:
            return False
        #print("flags: ", hex(m_uFlags))
        return m_uFlags & 0x02000000 != 0

    def GetGenericDefinition(typeHandle):
        pass

#https://github.com/dotnet/runtime/blob/86d2eaa16d818149c1c2869bf0234c6eba24afac/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L35
class ExecutionEnvironmentImplementation:
    def GetMetadataForNamedType(runtimeTypeHandle):
        (is_val, qTypeDefinition) = TypeLoaderEnvironment.TryGetMetadataForNamedType(runtimeTypeHandle)
        if not is_val:
            raise ValueError('Invalid Operation Exception')
        return qTypeDefinition
        
    def GetTypeDefinition(typeHandle):
        if (RuntimeAugments.IsGenericType(typeHandle)):
            raise ValueError('Cannot handle generic type')
        return typeHandle

    

# pulled from: https://github.com/dotnet/runtime/blob/86d2eaa16d818149c1c2869bf0234c6eba24afac/src/coreclr/nativeaot/System.Private.TypeLoader/src/Internal/Runtime/TypeLoader/TypeLoaderEnvironment.Metadata.cs#L55
class TypeLoaderEnvironment:
    def __init__(self):
        pass

    def TryGetMetadataForNamedType(runtimeTypeHandle): # return QTypeDefinition
        global METADATA_READER
        #note we only use the current module
        hashcode = runtimeTypeHandle.GetHashCode()
        (typeMapStart, typeMapEnd) = find_section_start_end(ReflectionMapBlob.TypeMap)
        typeMapReader = NativeReader(typeMapStart, typeMapEnd-typeMapStart)
        typeMapParser = NativeParser(typeMapReader, 0)
        typeMapHashtable = NativeHashTable(typeMapParser)
        externalReferences = ExternalReferencesTable(ReflectionMapBlob.CommonFixupsTable)
        
        lookup = typeMapHashtable.Lookup(hashcode)
        entryParser = lookup.GetNext()
        while entryParser is not None:
            foundType = externalReferences.GetRuntimeTypeHandleFromIndex(entryParser.GetUnsigned())
            if foundType == runtimeTypeHandle:
                entryMetadataHandle = NativeFormatHandle(entryParser.GetUnsigned())
                if entryMetadataHandle.hType == HandleType.TypeDefinition:
                    metadataReader = METADATA_READER()
                    return (True, QTypeDefinition(metadataReader, entryMetadataHandle))
        return (False, None)
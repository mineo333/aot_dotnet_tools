from binaryninja import *
from .nativeformat import *
from .utils import *
from .rtr import *
from .autogen.autogen_nativeformat import *
from .autogen.autogen_nativeformat_enums import *

'''
random, but important classes that don't really have a place
'''

#https://github.com/dotnet/runtime/blob/9f54e5162a177b8d6ad97ba53c6974fb02d0a47d/src/coreclr/nativeaot/Runtime/inc/MethodTable.h#L144C35-L144C45
IS_GENERIC_FLAG = 0x02000000

#https://github.com/dotnet/runtime/blob/6d23ef4d68bbcdb38fdc22218d1073c5083ac6a1/src/coreclr/nativeaot/Runtime/inc/MethodTable.h#L110C27-L110C45
NUM_VTABLE_SLOTS_OFF = 0x10
NUM_INTERFACES_OFF = 0x12

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
        m_uFlags = u32(read32(typeHandle.val))
        return m_uFlags & IS_GENERIC_FLAG != 0

    # pulled from assembly and https://github.com/dotnet/runtime/blob/6d23ef4d68bbcdb38fdc22218d1073c5083ac6a1/src/coreclr/nativeaot/Common/src/Internal/Runtime/MethodTable.cs#L457
    def GetGenericDefinition(typeHandle):
        flags = u32(read32(typeHandle.val))

        if (flags & 0x80000) == 0:
            off = (read16(typeHandle.val + NUM_INTERFACES_OFF) << 3) + (read16(typeHandle.val + NUM_VTABLE_SLOTS_OFF) << 3) + 0x20

            if (flags & 0x40000) != 0:
                off += 4
            if (flags & 0x100000) != 0:
                off += 4
            if (flags & 0x1000000) != 0:
                off += 4
            if (flags & 0x400000) != 0:
                off += 4
            
            n = typeHandle.val + off
            b = read32(n)

            if (u32(b) & 1) != 0:
                return RuntimeTypeHandle(read32(n + s32(b & 0xfffffffe)))

            return RuntimeTypeHandle(n + s32(b))

        off = (read16(typeHandle.val + NUM_INTERFACES_OFF) << 3) + (read16(typeHandle.val + NUM_VTABLE_SLOTS_OFF) << 3) + 0x28

        if (flags & 0x40000) != 0:
            off += 8
        if (flags & 0x100000) != 0:
            off += 8
        if (flags & 0x1000000) != 0:
            off += 8
        if (flags & 0x400000) != 0:
            off += 8

        n = typeHandle.val + off
        b = read32(n)

        if (u32(b) & 1) != 0:
            return RuntimeTypeHandle(read32(b - 1))

        return RuntimeTypeHandle(b)

#https://github.com/dotnet/runtime/blob/86d2eaa16d818149c1c2869bf0234c6eba24afac/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L35
class ExecutionEnvironmentImplementation:
    def GetMetadataForNamedType(runtimeTypeHandle):
        (is_val, qTypeDefinition) = TypeLoaderEnvironment.TryGetMetadataForNamedType(runtimeTypeHandle)
        if not is_val:
            raise ValueError('Invalid Operation Exception')
        return qTypeDefinition
        
    def GetTypeDefinition(typeHandle):
        if (RuntimeAugments.IsGenericType(typeHandle)):
            return RuntimeAugments.GetGenericDefinition(typeHandle)
        return typeHandle

# pulled from: https://github.com/dotnet/runtime/blob/86d2eaa16d818149c1c2869bf0234c6eba24afac/src/coreclr/nativeaot/System.Private.TypeLoader/src/Internal/Runtime/TypeLoader/TypeLoaderEnvironment.Metadata.cs#L55
class TypeLoaderEnvironment:
    def __init__(self):
        pass

    def TryGetMetadataForNamedType(runtimeTypeHandle): # return QTypeDefinition
        #note we only use the current module
        hashcode = runtimeTypeHandle.GetHashCode()
        #print('hashcode', hex(hashcode))
        (typeMapStart, typeMapEnd) = find_section_start_end(ReflectionMapBlob.TypeMap)
        typeMapReader = NativeReader(typeMapStart, typeMapEnd-typeMapStart)
        typeMapParser = NativeParser(typeMapReader, 0)
        typeMapHashtable = NativeHashTable(typeMapParser)
        externalReferences = ExternalReferencesTable(ReflectionMapBlob.CommonFixupsTable)
        
        lookup = typeMapHashtable.Lookup(hashcode)
        
        for entryParser in lookup:
            idx = entryParser.GetUnsigned()
            foundType = externalReferences.GetRuntimeTypeHandleFromIndex(idx)
            if foundType == runtimeTypeHandle:
                entryMetadataHandle = Handle(entryParser.GetUnsigned())
                if entryMetadataHandle.hType == HandleType.TypeDefinition:
                    metadataReader = METADATA_READER()
                    return (True, QTypeDefinition(metadataReader, entryMetadataHandle))
        return (False, None)
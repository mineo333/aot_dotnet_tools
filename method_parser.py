from binaryninja import *
import struct
import ctypes
from enum import IntEnum, Flag
from .dotnet_enums import *
from .nativeformat import *
from .rtr import *
#CONSTANTS 

class MethodAttributes(Flag):
    # Member access mask
    MemberAccessMask = 0x0007
    PrivateScope = 0x0000  # Member not referenceable.
    Private = 0x0001       # Accessible only by the parent type.
    FamANDAssem = 0x0002   # Accessible by sub-types only in this Assembly.
    Assembly = 0x0003      # Accessible by anyone in the Assembly.
    Family = 0x0004        # Accessible only by type and sub-types.
    FamORAssem = 0x0005    # Accessible by sub-types anywhere, plus anyone in assembly.
    Public = 0x0006        # Accessible by anyone who has visibility to this scope.

    # Method contract attributes
    Static = 0x0010        # Defined on type, else per instance.
    Final = 0x0020        # Method may not be overridden.
    Virtual = 0x0040      # Method virtual.
    HideBySig = 0x0080    # Method hides by name+sig, else just by name.
    CheckAccessOnOverride = 0x0200

    # Vtable layout mask
    VtableLayoutMask = 0x0100
    ReuseSlot = 0x0000     # The default.
    NewSlot = 0x0100       # Method always gets a new slot in the vtable.

    # Method implementation attributes
    Abstract = 0x0400      # Method does not provide an implementation.
    SpecialName = 0x0800   # Method is special. Name describes how.

    # Interop attributes
    PinvokeImpl = 0x2000   # Implementation is forwarded through pinvoke.
    UnmanagedExport = 0x0008  # Managed method exported via thunk to unmanaged code.
    RTSpecialName = 0x1000  # Runtime should check name encoding.

    HasSecurity = 0x4000    # Method has security associated with it.
    RequireSecObject = 0x8000  # Method calls another method containing security code.

    ReservedMask = 0xd000

    def Read(reader, offset):
        (offset, value) = reader.DecodeUnsigned(offset)
        return (offset, MethodAttributes(value))
    
class MethodImplAttributes(Flag):
    # Code impl mask
    CodeTypeMask = 0x0003   # Flags about code type.
    IL = 0x0000             # Method impl is IL.
    Native = 0x0001          # Method impl is native.
    OPTIL = 0x0002          # Method impl is OPTIL.
    Runtime = 0x0003        # Method impl is provided by the runtime.

    # Managed mask
    ManagedMask = 0x0004    # Flags specifying whether the code is managed or unmanaged.
    Unmanaged = 0x0004      # Method impl is unmanaged, otherwise managed.
    Managed = 0x0000        # Method impl is managed.

    # Implementation info and interop
    ForwardRef = 0x0010     # Indicates method is not defined; used primarily in merge scenarios.
    PreserveSig = 0x0080    # Indicates method sig is exported exactly as declared.

    InternalCall = 0x1000   # Internal Call...

    Synchronized = 0x0020    # Method is single threaded through the body.
    NoInlining = 0x0008      # Method may not be inlined.
    AggressiveInlining = 0x0100  # Method should be inlined if possible.
    NoOptimization = 0x0040  # Method may not be optimized.
    AggressiveOptimization = 0x0200  # Method may contain hot code and should be aggressively optimized.

    MaxMethodImplVal = 0xffff

    def Read(reader, offset):
        (offset, value) = reader.DecodeUnsigned(offset)
        return (offset, MethodAttributes(value))

#END CONSTANTS

METADATA_READER = None
    

#BELOW THIS ARE THE NATIVE FORMAT HELPERS

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



class Handle:
    def __init__(self, value):
        self.value = value
    
    @property
    def HandleType(self):
        return HandleType(self.value >> 24)
    
    @property
    def Offset(self):
        return self.value & 0xffffff   
    
    def AsInt(self):
        return self.value

#https://github.com/dotnet/runtime/blob/87fea60432fb34a2537a3a593c80042d8230b986/src/mono/System.Private.CoreLib/src/System/RuntimeTypeHandle.cs#L41
class RuntimeTypeHandle:
    def __init__(self, value):
        self.val = value #the value is the vtable for that object
        
    # may need to get updated
    # see: https://github.com/dotnet/runtime/blob/f11dfc95e67ca5ccb52426feda922fe9bcd7adf4/src/libraries/System.Private.CoreLib/src/System/IntPtr.cs#L90
    
    def GetHashCode(self):
        return self.__hash__()

    def __str__(self):
        return hex(self.val)
    
    def __eq__(self, other):
        if isinstance(other, RuntimeTypeHandle):
            return self.val == other.val
        return False
    
    def __hash__(self):
        return read32(self.val + 0x14)
    

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

#https://github.com/dotnet/runtime/blob/6c83e0d2f0fbc40a78f7b570127f686767ea5d9f/src/coreclr/nativeaot/System.Private.CoreLib/src/System/Reflection/Runtime/General/QHandles.NativeFormat.cs#L17
class QMethodDefinition:
    def __init__(self, reader, handle):
        self.reader = reader
        self.handle = handle
    
    @property
    def NativeFormatReader(self):
        return self.reader
    
    @property
    def NativeFormatHandle(self):
        MethodHandle(self.handle)
    

# pulled from: https://github.com/dotnet/runtime/blob/86d2eaa16d818149c1c2869bf0234c6eba24afac/src/coreclr/nativeaot/System.Private.TypeLoader/src/Internal/Runtime/TypeLoader/TypeLoaderEnvironment.Metadata.cs#L55
class TypeLoaderEnvironment:
    def __init__(self):
        pass

    def TryGetMetadataForNamedType(runtimeTypeHandle): # return QTypeDefinition
        #note we only use the current module
        hashcode = runtimeTypeHandle.GetHashCode()
        (typeMapStart, typeMapEnd) = find_section_start_end(ReflectionMapBlob.TypeMap)
        typeMapReader = NativeReader(typeMapStart, typeMapEnd-typeMapStart)
        typeMapParser = NativeParser(typeMapReader, 0)
        typeMapHashtable = NativeHashTable(typeMapParser)
        externalReferences = ExternalReferencesTable(ReflectionMapBlob.CommonFixupsTable)
        
        print('hashcode', hex(hashcode))
        lookup = typeMapHashtable.Lookup(hashcode)
        entryParser = lookup.GetNext()
        while entryParser is not None:
            foundType = externalReferences.GetRuntimeTypeHandleFromIndex(entryParser.GetUnsigned())
            if foundType == runtimeTypeHandle:
                entryMetadataHandle = Handle(entryParser.GetUnsigned())
                if entryMetadataHandle.HandleType == HandleType.TypeDefinition:
                    metadataReader = METADATA_READER 
                    return (True, QTypeDefinition(metadataReader, entryMetadataHandle))

        
        return (False, None)

                    
# pulled from: https://github.com/dotnet/runtime/blob/6ac8d055a200ccca0d6fa8604c18578234dffa94/src/coreclr/nativeaot/System.Private.CoreLib/src/System/Reflection/Runtime/General/QHandles.NativeFormat.cs#L39
class QTypeDefinition:
    def __init__(self, reader, handle):
        self.reader = reader
        self.handle = handle.AsInt()
        
    @property
    def NativeFormatReader(self):
        return self.reader
    

# pulled from: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L3175
class Method:
    def __init__(self, reader, handle):
        self.reader = reader
        self.handle = handle
        offset = u32(handle.Offset)
        streamReader = reader.streamReader
        (offset, self.flags) = MethodAttributes.Read(streamReader, offset)
        (offset, self.implFlags) = MethodImplAttributes.Read(streamReader, offset)
        (offset, self.name) = NativeFormatHandle.Read(streamReader, offset) # can update this later
        print(hex(streamReader.base + self.name.Offset))
        (offset, self.signature) = NativeFormatHandle.Read(streamReader, offset) # can update this later
        (offset, self.parameters) = NativeFormatCollection.Read(streamReader, offset)
        (offset, self.genericParamters) = NativeFormatCollection.Read(streamReader, offset)
        (offset, self.customAttributes) = NativeFormatCollection.Read(streamReader, offset)

# pulled from: https://github.com/dotnet/runtime/blob/a72cfb0ee2669abab031c5095a670678fd0b7861/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L3221
class MethodHandle:
    def __init__(self, value):
        self._hType = HandleType(value >> 24)
        assert self._hType == 0 or self._hType == HandleType.Method or self._hType == HandleType.Null
        self._value = (value & 0x00FFFFFF) | (HandleType.Method << 24)

    @property
    def value(self):
        return self._value

    @property
    def hType(self):
        return self._hType

    @property
    def Offset(self):
        return self._value & 0xffffff
    
    def GetMethod(self, reader):
        return Method(reader, self)
    
# used here: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L2025 
# used here: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L3484
class NativeFormatHandle:
    def __init__(self, value):
        self._hType = HandleType(value >> 24)
        assert self._hType == 0 or self._hType == HandleType.Method or self._hType == HandleType.Null
        self._value = (value & 0x00FFFFFF) | (HandleType.Method << 24)

    @property
    def value(self):
        return self._value

    @property
    def hType(self):
        return self._hType

    @property
    def Offset(self):
        return self._value & 0xffffff
    
    def Read(reader, offset):
        (offset, value) = reader.DecodeUnsigned(offset)
        return (offset, NativeFormatHandle(value))

# used here: https://github.com/dotnet/runtime/blob/6fa9cfcdd9179a33a10c096c06150c4a11ccc93e/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L6193
# used here: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L5572
# used here: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L5641
# used here: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L5503
class NativeFormatCollection:
    def __init__(self, reader, offset):
        self.reader = reader
        self.offset = offset

    # pulled from: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator/ReaderGen.cs#L62
    def Read(reader, offset):
        (offset, count) = reader.DecodeUnsigned(offset)
        for _ in range(count):
            offset = reader.SkipInteger(offset)
        return (offset, NativeFormatCollection(reader, offset))

# pulled from: https://github.com/dotnet/runtime/blob/6ac8d055a200ccca0d6fa8604c18578234dffa94/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeMetadataReader.cs#L225
class MetadataHeader:
    SIGNATURE = u32(0xDEADDFFD)

    SCOPE_DEFINITIONS = None
    
    # Decode defintion was found in the assembly
    def Decode(self, reader):
        if reader.ReadUInt32(0) != self.SIGNATURE:
            raise ValueError("Bad Image Format Exception")
        self.SCOPE_DEFINITIONS = NativeFormatCollection.Read(reader, 4)


# pulled from: https://github.com/dotnet/runtime/blob/95bae2b141e5d1b8528b1f8620f3e9d459abe640/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeMetadataReader.cs#L162
class MetadataReader:
    def __init__(self, pBuffer, cbBuffer):
        self.streamReader = NativeReader(pBuffer, u32(cbBuffer))
        self.header = MetadataHeader()
        self.header.Decode(self.streamReader)

        @property
        def ScopeDefinitions():
            return self.header.SCOPE_DEFINITIONS
        
        @property
        def NullHandle():
            return Handle(HandleType.Null << 24)

        def isNull(self, handle):
            return handle.value == NullHandle.value


# MAIN PARSING CODE STARTS HERE
            
            
#The metadata reader is created here: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/nativeaot/System.Private.TypeLoader/src/Internal/Runtime/TypeLoader/ModuleList.cs#L273
def create_metadata_reader(): 
    global METADATA_READER
    (metadata_start, metadata_end) = find_section_start_end(ReflectionMapBlob.EmbeddedMetadata)  
    #metadataNativeReader = NativeReader(metadata_start, metadata_end-metadata_start)
    METADATA_READER = MetadataReader(metadata_start, metadata_end-metadata_start)
    

#this comes from here: https://github.com/dotnet/runtime/blob/c43fc8966036678d8d603bdfbd1afd79f45b420b/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L643
def parse_hashtable(invokeMapStart, invokeMapEnd):
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
        
        if entryFlags & InvokeTableFlags.IsGenericMethod:
            continue
        
        if entryFlags & int(InvokeTableFlags.HasMetadataHandle) != 0:
            declaringTypeHandleDefinition = ExecutionEnvironmentImplementation.GetTypeDefinition(declaringTypeHandle)
            qTypeDefinition = ExecutionEnvironmentImplementation.GetMetadataForNamedType(declaringTypeHandleDefinition)
            nativeFormatMethodHandle = MethodHandle((HandleType.Method << 24) | entryMethodHandleOrNameAndSigRaw)
            methodHandle = QMethodDefinition(qTypeDefinition.NativeFormatReader, nativeFormatMethodHandle)
            method = methodHandle.handle.GetMethod(METADATA_READER)
        
    return


def parse_methods():
    create_metadata_reader()
    (start,end) = find_section_start_end(ReflectionMapBlob.InvokeMap)
    parse_hashtable(start, end)








#pulled from: https://github.com/dotnet/runtime/blob/6ed953a000613e5b02e5ac38d35aa4fef6c38660/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L578, this basically fills _ldftnReverseLookup_InvokeMap
#NOTE: actually setting _ldftnReverseLookup_InvokeMap is done here: https://github.com/dotnet/runtime/blob/6ed953a000613e5b02e5ac38d35aa4fef6c38660/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L498C17-L498C46

from binaryninja import *
import struct
import ctypes
from enum import IntEnum
#CONSTANTS 

#pulled from: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/nativeaot/Runtime/inc/ModuleHeaders.h#L10
READY_TO_RUN_SIG = b'\x52\x54\x52\x00'

#pulled from: https://github.com/dotnet/runtime/blob/cca022b6212f33adc982630ab91469882250256c/src/coreclr/tools/Common/Internal/Runtime/MetadataBlob.cs#L6 - Note that 300 is added to all these numbers

class ReflectionMapBlob(IntEnum):
    TypeMap                                     = 301
    ArrayMap                                    = 302
    PointerTypeMap                              = 303
    FunctionPointerTypeMap                      = 304
#    // unused                                   = 5,
#__method_to_entrypoint_map
    InvokeMap                                   = 306
    VirtualInvokeMap                            = 307
    CommonFixupsTable                           = 308
    FieldAccessMap                              = 39
    CCtorContextMap                             = 310
    ByRefTypeMap                                = 311
#   unused                                   = 12,
    EmbeddedMetadata                            = 313
#    // Unused                                   = 14,
    UnboxingAndInstantiatingStubMap             = 315
    StructMarshallingStubMap                    = 316
    DelegateMarshallingStubMap                  = 317
    GenericVirtualMethodTable                   = 318
    InterfaceGenericVirtualMethodTable          = 319

#    // Reflection template types/methods blobs:
    TypeTemplateMap                             = 321
    GenericMethodsTemplateMap                   = 322
#    // unused                                   = 23,
    BlobIdResourceIndex                         = 324
    BlobIdResourceData                          = 325
    BlobIdStackTraceEmbeddedMetadata            = 326
    BlobIdStackTraceMethodRvaToTokenMapping     = 327

#    //Native layout blobs:
    NativeLayoutInfo                            = 330
    NativeReferences                            = 331
    GenericsHashtable                           = 332
    NativeStatics                               = 333
    StaticsInfoHashtable                        = 334
    GenericMethodsHashtable                     = 335
    ExactMethodInstantiationsHashtable          = 336


MASK_64 = 0xffffffffffffffff

# pulled from: https://github.com/dotnet/runtime/blob/f11dfc95e67ca5ccb52426feda922fe9bcd7adf4/src/coreclr/nativeaot/Runtime/inc/MethodTable.h#L103
M_UFLAGS_OFF = 8

# Pulled from: https://github.com/dotnet/runtime/blob/main/src/coreclr/tools/Common/Internal/Runtime/MappingTableFlags.cs#L21
class InvokeTableFlags(IntEnum):
    HasVirtualInvoke = 0x00000001
    IsGenericMethod = 0x00000002
    HasMetadataHandle = 0x00000004
    IsDefaultConstructor = 0x00000008
    RequiresInstArg = 0x00000010
    HasEntrypoint = 0x00000020
    IsUniversalCanonicalEntry = 0x00000040
    NeedsParameterInterpretation = 0x00000080
    CallingConventionDefault = 0x00000000
    Cdecl = 0x00001000
    Winapi = 0x00002000
    StdCall = 0x00003000
    ThisCall = 0x00004000
    FastCall = 0x00005000
    CallingConventionMask = 0x00007000


class HandleType(IntEnum):
    Null = 0x0
    ArraySignature = 0x1
    ByReferenceSignature = 0x2
    ConstantBooleanArray = 0x3
    ConstantBooleanValue = 0x4
    ConstantByteArray = 0x5
    ConstantByteValue = 0x6
    ConstantCharArray = 0x7
    ConstantCharValue = 0x8
    ConstantDoubleArray = 0x9
    ConstantDoubleValue = 0xa
    ConstantEnumArray = 0xb
    ConstantEnumValue = 0xc
    ConstantHandleArray = 0xd
    ConstantInt16Array = 0xe
    ConstantInt16Value = 0xf
    ConstantInt32Array = 0x10
    ConstantInt32Value = 0x11
    ConstantInt64Array = 0x12
    ConstantInt64Value = 0x13
    ConstantReferenceValue = 0x14
    ConstantSByteArray = 0x15
    ConstantSByteValue = 0x16
    ConstantSingleArray = 0x17
    ConstantSingleValue = 0x18
    ConstantStringArray = 0x19
    ConstantStringValue = 0x1a
    ConstantUInt16Array = 0x1b
    ConstantUInt16Value = 0x1c
    ConstantUInt32Array = 0x1d
    ConstantUInt32Value = 0x1e
    ConstantUInt64Array = 0x1f
    ConstantUInt64Value = 0x20
    CustomAttribute = 0x21
    Event = 0x22
    Field = 0x23
    FieldSignature = 0x24
    FunctionPointerSignature = 0x25
    GenericParameter = 0x26
    MemberReference = 0x27
    Method = 0x28
    MethodInstantiation = 0x29
    MethodSemantics = 0x2a
    MethodSignature = 0x2b
    MethodTypeVariableSignature = 0x2c
    ModifiedType = 0x2d
    NamedArgument = 0x2e
    NamespaceDefinition = 0x2f
    NamespaceReference = 0x30
    Parameter = 0x31
    PointerSignature = 0x32
    Property = 0x33
    PropertySignature = 0x34
    QualifiedField = 0x35
    QualifiedMethod = 0x36
    SZArraySignature = 0x37
    ScopeDefinition = 0x38
    ScopeReference = 0x39
    TypeDefinition = 0x3a
    TypeForwarder = 0x3b
    TypeInstantiationSignature = 0x3c
    TypeReference = 0x3d
    TypeSpecification = 0x3e
    TypeVariableSignature = 0x3f

#END CONSTANTS
sections = None
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

#THIS READER IS ALWAYS USED TO READ ABSOLUTE ADDRESSES
READER = bv.reader(0)

#TODO: Change this so that we are not allocating objects every time 
def read8(address): 
    global READER
    return READER.read8(address)  

def read16(address):
    global READER
    return READER.read16(address)

def read32(address):
    global READER
    return READER.read32(address)

def read64(address):
    global READER
    return READER.read64(address)

#convert an unsigned byte to a signed byte
def s8(val): 
    return ctypes.c_byte(val & 0xff).value

def u8(val):
    return ctypes.c_ubyte(val & 0xff).value

def s32(val):
    return ctypes.c_int(val & 0xffffffff).value

def u32(val):
    return ctypes.c_uint(val & 0xffffffff).value

def s64(val):
    return ctypes.c_long(val).value

def u64(val):
    return ctypes.c_ulong(val).value


def initialize_rtr():
    global sections
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
    
    

def find_section_start_end(section_id):
    global sections
    for section in sections:
        if section['SectionId'] == section_id:
            return (section['Start'], section['End'])
    raise ValueError('Could not find section', section_id)
        

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
        return self.GetAddressFromIndex(idx) #update this impl if needed
    
    def GetRuntimeTypeHandleFromIndex(self, idx):
        return RuntimeAugments.CreateRuntimeTypeHandle(self.GetIntPtrFromIndex(idx))
    
    def GetAddressFromIndex(self, idx):
        #in this case, we use the relative pointer version
        if idx >= self.elementsCount:
            raise ValueError('Bad Image Format Exception')
        
        pRelPtr32 = self.elements + idx*4
        return pRelPtr32 + s64(s32(read32(pRelPtr32))) 


#pulled from: https://github.com/dotnet/runtime/blob/cca022b6212f33adc982630ab91469882250256c/src/coreclr/tools/Common/Internal/NativeFormat/NativeFormatReader.cs#L217
#This also integrates the functionality of NativePrimitiveDecoder: https://github.com/dotnet/runtime/blob/cca022b6212f33adc982630ab91469882250256c/src/coreclr/tools/Common/Internal/NativeFormat/NativeFormatReader.Primitives.cs#L16C36-L16C58
class NativeReader:
    def __init__(self, base, size):
        self.base = base
        self.size = size
    
    def EnsureOffsetInRange(self, offset, lookAhead):
        if(s32(offset) < 0 or (offset + lookAhead) >= self.size):
            raise ValueError('Offset out of range')
    
    def ReadUInt8(self, offset):
        self.EnsureOffsetInRange(offset, 0)
        return read8(self.base + offset)
    
    def ReadUInt16(self, offset):
        self.EnsureOffsetInRange(offset, 1)
        return read16(self.base + offset)
    
    def ReadUInt32(self, offset):
        self.EnsureOffsetInRange(offset, 3)
        return read32(self.base + offset)
    
    def ReadUInt64(self, offset):
        self.EnsureOffsetInRange(offset, 7)
        return read64(self.base + offset)
    
    def DecodeUnsigned(self, offset):
        stream = self.base + offset
        val = read8(stream)
        
        if ((val & 1) == 0):
            pvalue = val >> 1
            stream += 1
        elif ((val & 2) == 0):
            pvalue = (val >> 2) | (u32(read8(stream+1)) << 6)
            stream += 2
        elif ((val & 4) == 0):
            pvalue = (val >> 3) | (u32(read8(stream+1)) << 5) | (u32(read8(stream+2)) << 13)
            stream += 3
        elif ((val & 8) == 0):
            pvalue = (val >> 4) | (u32(read8(stream+1)) << 4) | (u32(read8(stream+2)) << 12) | (u32(read8(stream+3)) << 20)
            stream += 4
        elif ((val & 16) == 0):
            stream += 1
            pvalue = u32(read32(stream))
            stream += 4 #this 4 is from the increment in ReadUInt32
        else:
            raise ValueError("Fuck you")
        return (stream-self.base, pvalue)
    
    #returns the new offset as well as the value
    def DecodeSigned(self, offset):
        stream = self.base + offset
        #try to make the casting as deliberate as possible
        val = s32(read8(stream))  # Read the byte at the current offset

        if ((val & 1) == 0):
            pvalue = s32(s8(val) >> 1)
            stream += 1
        elif ((val & 2) == 0):
            pvalue = (val >> 2) | s32(s8(read8(stream+1)) << 6)
            stream += 2
        elif ((val & 4) == 0):
            pvalue = (s32(val) >> 3) | (s32(read8(stream+1)) << 5) | (s32(s8(read8(stream+2))) << 13)
            stream += 3
        elif ((val & 8) == 0):
            pvalue = (val >> 4) | s32(read8(stream+1)) << 4 | s32(read8(stream+2)) << 12 | s32(s8(read8(stream+3)) << 20)
            stream += 4
        elif ((val & 16) == 0):
            stream += 1
            pvalue = s32(br.read32())
            stream += 4 #this 4 is to account for the 4 bytes incremented in ReadUInt32
        else:
            raise ValueError("Fuck you")
        return (stream - self.base, pvalue)
    
    def SkipInteger(self, offset):
        val = read8(self.base + offset)
        
        if (val & 1) == 0:
            return offset + 1
        elif (val & 2) == 0:
            return offset + 2
        elif (val & 4) == 0:
            return offset + 3
        elif (val & 8) == 0:
            return offset + 4
        elif (val & 16) == 0:
            return offset + 5
        elif (val & 32) == 0:
            return offset + 9
        else:
            raise ValueError('Bad Image Format Exception')

class NativeParser:
    def __init__(self, reader, offset):
        self.offset = offset
        self.reader = reader
    
    def GetUInt8(self):
        val = self.reader.ReadUInt8(self.offset)
        self.offset += 1
        return val
    
    def GetUnsigned(self):
        (self.offset, val) = self.reader.DecodeUnsigned(self.offset)
        return val
    
    def GetSigned(self):
        (self.offset, val) = self.reader.DecodeSigned(self.offset)
        return val
    
    def GetRelativeOffset(self):
        pos = self.offset 
        (self.offset, delta) = self.reader.DecodeSigned(self.offset)
        rel_offset = u32(pos + delta)
        #print('pos', hex(pos), 'delta', delta, 'rel offset', hex(rel_offset))
        return rel_offset #reader._base + _offset + delta - this offset is associated with pos
    
    def GetParserFromRelativeOffset(self):
        return NativeParser(self.reader, self.GetRelativeOffset())

    def SkipInteger(self):
        print('skip', hex(self.reader.base + self.offset))
        self.offset = self.reader.SkipInteger(self.offset)
    
    def GetAddress(self):
        return self.reader.base + self.offset


#https://github.com/dotnet/runtime/blob/main/src/coreclr/tools/Common/Internal/NativeFormat/NativeFormatReader.cs#L456

'''
The rough structure of a NativeHashTable is as follows:

[header][bucket offsets][data]

The header is essentially contains core data including number of buckets and the size of bucket offsets.

In a NativeHashtable, an important constant is: base_offset. base_offset is always the offset of the first byte of [bucket offsets]

The number of buckets is 2**number_of_buckets_shift in the header 

Each bucket offset can either be 1, 2, or 4 bytes (In the case of Flare-On it is 2). This is determined by the entry_index_size in the header.

The [bucket offsets] section is an array of bucket offsets. We essentially use a sliding window to determine the start and end of each bucket. For example, support bucket offsets is: {0x0, 0x10, 0x20, 0x30}

Then, the start/end of bucket 0 is (0, 0x10), the start/end of bucket 1 is (0x10, 0x20), etc.


We then add the start of the bucket to base_offset and that serves as the array of offsets for each element in that bucket. Each offset in that array is a relative offset (Meaning it is calculated with DecodeSigned + offset). Each offset is seperated by the "low hashcode" of that object (First byte of the hashcode)

This is where AllEntriesEnumerator::parser comes in. The parser, is the NativeParser is the thing that decodes all those relative offsets and generates a new parser (Using GetParserFromRelativeOffset) that can then be used to view that specific element. 

The high level description of NativeHashtable can be seen below

                  +--------+                                                          
                  |        |                                                          
                  |        |<------|                                                  
                  |        |       |                                                  
                  +--------+       |<------ Each element offset points to an element. New parser is created  
                  |        |       |                                                  
                  |        |       |                                                  
                  |        |-------+                                                  
                  |        |                                                          
                  |--------|<----------|                                              
                  |        |           |                                              
                  |        |           |                                              
                  |        |           |<------Bucket offset points to element offsets. New parser is created
                  |        |           |                                              
     Data  -----> +--------+           |                                              
                  |        |           |                                              
                  |        |-----------+                                              
                  |        |                                                          
                  |        |                                                          
                  |        |                                                          
                  +--------+<-----Bucket offsets                                      
                  +--------+<-----Header Byte                                         
'''
class NativeHashTable:
    def __init__(self, parser): #the parser should point to the header byte of the NativeHashtable
        header = parser.GetUInt8()
        self.base_offset = parser.offset #base offset is the offset where the NativeHashtable starts (header+1)
        self.reader = parser.reader #reader associated with this section
        
        
        number_of_buckets_shift = header >> 2
        if (number_of_buckets_shift > 31):
            raise ValueError("Bad image format exception") 
        self.bucket_mask = (1 << number_of_buckets_shift) - 1

        entry_index_size = header & 3
        
        if (entry_index_size > 2):
            raise ValueError("Bad image format exception") 
        self.entry_index_size = entry_index_size
        
    class AllEntriesEnumerator:
        def __init__(self, table):
            self.table = table
            self.current_bucket = 0
            #self.parser is the parser for the bucket
            #end_offset is the end of the the current bucket
            (self.parser, self.end_offset) = table.GetParserForBucket(self.current_bucket)

        #get next basically 
        def GetNext(self):
            while (True):
                while (self.parser.offset < self.end_offset):
                    
                    self.parser.GetUInt8() #skip hashcode
                    return self.parser.GetParserFromRelativeOffset()
                if (self.current_bucket >= self.table.bucket_mask):
                    return #the default value for an object is null
                self.current_bucket += 1
                (self.parser, self.end_offset) = self.table.GetParserForBucket(self.current_bucket)
    
    class Enumerator:
        def __init__(self, parser, end_offset, low_hashcode):
            self.parser = parser
            self.end_offset = end_offset
            self.low_hashcode = low_hashcode
        
        def GetNext(self):
            while(parser.offset < self.end_offset):
                low_hashcode = parser.GetUInt8()
                
                if low_hashcode == self.low_hashcode:
                    return parser.GetParserFromRelativeOffset()
                
                if low_hashcode > self.low_hashcode:
                    self.end_offset = parser.offset
                    break
            
                parser.SkipInteger() #skip past the current offset
            return None
        
    
    def GetParserForBucket(self, bucket): #returns the NativeParser and the endOffset
        if (self.entry_index_size == 0):
            bucket_offset = self.base_offset + bucket
            _start = self.reader.ReadUInt8(bucket_offset)
            _end = self.reader.ReadUInt8(bucket_offset + 1)
        elif (self.entry_index_size == 1):
            bucket_offset = self.base_offset + 2 * bucket
            _start = self.reader.ReadUInt16(bucket_offset)
            _end = self.reader.ReadUInt16(bucket_offset + 2)
        else:
            bucket_offset = self.base_offset + 4 * bucket
            _start = self.reader.ReadUInt32(bucket_offset)
            _end = self.reader.ReadUInt32(bucket_offset + 4)
            
        end_offset = _end + self.base_offset
        parser = NativeParser(self.reader, self.base_offset + _start)
        #print('bucket', hex(bucket), 'start', hex(_start), 'end', hex(_end))
        #print('bucket parser offset', hex(parser.offset), 'addr', hex(parser.GetAddress()), 'bucket', bucket, 'end_offset', hex(end_offset))
        return (parser, end_offset)

    def Lookup(self, hashcode):
        bucket = (u32(hashcode) >> 8) & self.bucket_mask
        (parser, end_offset) = self.GetParserForBucket(bucket)
        
        return Enumerator(parser, end_offset, u8(bucket))

class Handle:
    def __init__(self, value):
        self.value = value
    
    @property
    def HandleType(self):
        return HandleType(self.value >> 24)
    
    @property
    def Offset(self):
        return self.value & 0xffffff     

#https://github.com/dotnet/runtime/blob/87fea60432fb34a2537a3a593c80042d8230b986/src/mono/System.Private.CoreLib/src/System/RuntimeTypeHandle.cs#L41
class RuntimeTypeHandle:
    def __init__(self, value):
        self.val = value
        
    # may need to get updated
    # see: https://github.com/dotnet/runtime/blob/f11dfc95e67ca5ccb52426feda922fe9bcd7adf4/src/libraries/System.Private.CoreLib/src/System/IntPtr.cs#L90
    
    def GetHashCode(self):
        return self.__hash__()

    def __str__(self):
        return hex(self.val)
    
    def __eq__(self, other):
        if isinstance(other, RuntimeTypeHandle):
            return self.value == other.value
        return False
    #you can see this in the disassembly for #TryGetMetadataForNamedType
    def __hash__(self):
        return read32(self.val + 20)

#https://github.com/dotnet/runtime/blob/main/src/coreclr/nativeaot/System.Private.CoreLib/src/Internal/Runtime/Augments/RuntimeAugments.cs#L37
class RuntimeAugments:
    
    def CreateRuntimeTypeHandle(ldTokenResult):
        return RuntimeTypeHandle(ldTokenResult)
    
    def IsGenericType(typeHandle):
        m_uFlags = u32(read32(typeHandle + M_UFLAGS_OFF))
        #print("flags: ", m_uFlags)
        # check for generic type
        return m_uFlags & 0x02000000 != 0

    def GetGenericDefinition(typeHandle):
        pass

#https://github.com/dotnet/runtime/blob/86d2eaa16d818149c1c2869bf0234c6eba24afac/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L35
class ExecutionEnvironmentImplementation:
    def GetMetadataForNamedType(runtimeTypeHandle):
        #calls TryGetMetadataForNamedType
        pass
    
    def GetTypeDefinition(typeHandle):
        if (RuntimeAugments.IsGenericType(typeHandle)):
            raise ValueError('Cannot handle generic type')
        return typeHandle
    

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
        
        lookup = typeMapHashtable.Lookup(hashcode)
        entryParser = lookup.GetNext()
        while entryParser is not None:
            foundType = externalReferences.GetRuntimeTypeHandleFromIndex(entryParser.GetUnsigned())
            if foundType == runtimeTypeHandle:
                entryMetadataHandle = Handle(entryParser.GetUnsigned())
                # I think we can just pass entryMetadataHandle directly into HandleType
                # https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeMetadataReader.cs#L107
                if entryMetadataHandle.HandleTyp == HandleType.TypeDefinition:
                    metadataReader = NativeReader() # TODO: find offsets for this NativeReader
                    return QTypeDefinition(metadataReader, entryMetadataHandle)
                    

class QTypeDefinition:
    def __init__(self, reader, handle):
        self.reader = reader
        self.handle = handle #int

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


# MAIN PARSING CODE STARTS HERE
            

# br will work as our native parser

#this comes from here: https://github.com/dotnet/runtime/blob/c43fc8966036678d8d603bdfbd1afd79f45b420b/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L643
def parse_hashtable(invokeMapStart, invokeMapEnd):
    reader = NativeReader(invokeMapStart, invokeMapEnd-invokeMapStart) #create a NativeReader starting from end-start
    enumerator = NativeHashTable.AllEntriesEnumerator(NativeHashTable(NativeParser(reader, 0))) 
    
    entryParser = enumerator.GetNext()
    externalReferences = ExternalReferencesTable(ReflectionMapBlob.CommonFixupsTable)
    while (entryParser is not None): 
        entryFlags = entryParser.GetUnsigned()
        if entryFlags & InvokeTableFlags.HasEntrypoint != 0:
            #entryParser.SkipInteger()

            entryMethodHandleOrNameAndSigRaw = entryParser.GetUnsigned()
            entryDeclaringTypeRaw = entryParser.GetUnsigned()

            entryMethodEntryPoint = externalReferences.GetFunctionPointerFromIndex(entryParser.GetUnsigned())
            print('entryMethodEntryPoint', hex(entryMethodEntryPoint))

            if entryFlags & InvokeTableFlags.NeedsParameterInterpretation != 0:
                entryParser.SkipInteger()

            declaringTypeHandle = externalReferences.GetRuntimeTypeHandleFromIndex(entryDeclaringTypeRaw)
            print('declaringTypeHandle', declaringTypeHandle)
           
            if entryFlags & int(InvokeTableFlags.HasMetadataHandle) != 0:
                #declaringTypeHandleDefinition = GetTypeDefinition(declaringTypeHandle)
                #qTypeDefinition = None
                nativeFormatMethodHandle = MethodHandle((HandleType.Method << 24) | entryMethodHandleOrNameAndSigRaw)

        entryParser = enumerator.GetNext() 
        
    return

initialize_types()
initialize_rtr()
(start,end) = find_section_start_end(ReflectionMapBlob.InvokeMap)
print('__method_entrypoint_map start:', hex(start), 'end:', hex(end))
parse_hashtable(start, end)





#pulled from: https://github.com/dotnet/runtime/blob/6ed953a000613e5b02e5ac38d35aa4fef6c38660/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L578, this basically fills _ldftnReverseLookup_InvokeMap
#NOTE: actually setting _ldftnReverseLookup_InvokeMap is done here: https://github.com/dotnet/runtime/blob/6ed953a000613e5b02e5ac38d35aa4fef6c38660/src/coreclr/nativeaot/System.Private.Reflection.Execution/src/Internal/Reflection/Execution/ExecutionEnvironmentImplementation.MappingTables.cs#L498C17-L498C46




'''
# pulled from: https://github.com/dotnet/runtime/blob/95bae2b141e5d1b8528b1f8620f3e9d459abe640/src/coreclr/nativeaot/System.Private.TypeLoader/src/Internal/Runtime/TypeLoader/ModuleList.cs#L36
class NativeFormatModuleInfo:
    def __init__(self, moduleHandle, pBlob, cbBlob):
        self.MetadataReader = MetadataReader(pBlob, cbBlob)

# pulled from: https://github.com/dotnet/runtime/blob/6fa9cfcdd9179a33a10c096c06150c4a11ccc93e/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L6193
class ScopeDefinitionHandleCollection:
    def __init__(self, reader, offset):
        self.reader = reader
        self.offset = offset

    def Count(self):
        pass

    def GetEnumerator(self):
        pass

pulled from: https://github.com/dotnet/runtime/blob/6fa9cfcdd9179a33a10c096c06150c4a11ccc93e/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeMetadataReader.cs#L162
class MetadataHeader:
    def __init__(self):
        self.signature = u32(0xDEADDFFD)

    def decode(self, reader):
        pass

# pulled from: https://github.com/dotnet/runtime/blob/95bae2b141e5d1b8528b1f8620f3e9d459abe640/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeMetadataReader.cs#L162
class MetadataReader:
    def __init__(self, pBuffer, cbBuffer):
        # should pBuffer be cast to s8 ?
        # see: https://github.com/dotnet/runtime/blob/95bae2b141e5d1b8528b1f8620f3e9d459abe640/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeMetadataReader.cs#L171
        self.streamReader = NativeReader(s8(pBuffer), u32(cbBuffer))
        self.header = MetadataHeader()

# pulled from: https://github.com/dotnet/runtime/blob/6fa9cfcdd9179a33a10c096c06150c4a11ccc93e/src/coreclr/nativeaot/System.Private.TypeLoader/src/Internal/Runtime/TypeLoader/TypeLoaderEnvironment.GVMResolution.cs#L164
def GetTypeDefinition(typeHandle):
    if (RuntimeAugments.IsGenericType(typeHandle)):
        print("generic type found")
        # would return RuntimeAugments.GetGenericDefinition(typeHandle)
    return typeHandle

'''
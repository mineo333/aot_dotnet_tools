from binaryninja import *
from .utils import *
from .rtr import *
from .dotnet_enums import *


'''
This file constitutes all the native format parsers

This includes objects such as NativeReader, NativeParser, and, most importantly, NativeHashtable
'''

METADATA_READER = None



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
        #print('skip', hex(self.reader.base + self.offset))
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
                  +--------+<-----Bucket offsets/base_offset                                      
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

        def __iter__(self):
            return self
        
        #get next basically 
        def __next__(self):
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
            while(self.parser.offset < self.end_offset):
                low_hashcode = self.parser.GetUInt8()
                
                if low_hashcode == self.low_hashcode:
                    return self.parser.GetParserFromRelativeOffset()
                
                if low_hashcode > self.low_hashcode:
                    self.end_offset = self.parser.offset
                    break
            
                self.parser.SkipInteger() #skip past the current offset
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
        
        return NativeHashTable.Enumerator(parser, end_offset, u8(hashcode))
    

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

            
            
#The metadata reader is created here: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/nativeaot/System.Private.TypeLoader/src/Internal/Runtime/TypeLoader/ModuleList.cs#L273
def create_metadata_reader(): 
    global METADATA_READER
    (metadata_start, metadata_end) = find_section_start_end(ReflectionMapBlob.EmbeddedMetadata)  
    #metadataNativeReader = NativeReader(metadata_start, metadata_end-metadata_start)
    METADATA_READER = MetadataReader(metadata_start, metadata_end-metadata_start)
    
    

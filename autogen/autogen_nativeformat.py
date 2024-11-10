from binaryninja import *
from ..utils import *
from ..dotnet_enums import *
from .autogen_nativeformat_enums import *
from .autogen_nativeformat_primitives import *

#https://github.com/dotnet/runtime/blob/ecd5ee7277b1eb33bed4cc91ce7abee609bbbd71/src/coreclr/nativeaot/System.Private.CoreLib/src/System/RuntimeTypeHandle.cs#L17

#the RuntimeTypeHandle is basically a shitty wrapper around MethodTable

#TODO: This needs to be moved to its own class as this si not part of the 
class RuntimeTypeHandle:
    def __init__(self, value):  
        self.val = value #the value is the vtable for that object
    
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
    


'''
Below this are anything related to the autogenerated NativeFormat

In the NativeFormat, there are many types that can exist. These types can all be found in NativeFormatReaderGen:
https://github.com/dotnet/runtime/blob/main/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs

In the constructors for all these types, they call a mysterious Read() function. This Read() is not actually hand written, but rather, autogenerated. The autogen code can be found here: https://github.com/dotnet/runtime/tree/6fa9cfcdd9179a33a10c096c06150c4a11ccc93e/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator

AUTOGEN PROCESS:

The autogen process is fairly simple. Each type is looked over and is assigned a schema here: https://github.com/dotnet/runtime/blob/6fa9cfcdd9179a33a10c096c06150c4a11ccc93e/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator/SchemaDef.cs. The naming in NativeFormatReaderGen is fairly convient. All things that end in Collection are collections, all things that end in Handle are handle, etc. 

Using the Schema, we output the source code for every read here: https://github.com/dotnet/runtime/blob/e133fe4f5311c0397f8cc153bada693c48eb7a9f/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator/MdBinaryReaderGen.cs#L19

Looking in the ReaderGen, there are a few "classes" of reads that exist. Firstly, there exists a single read for all Handles, a single read for all Collections, etc. We seek to emulate that in the following code. We have a NativeFormatHandle which is a top-level class for Handles and implements the read for all handle classes. Any handles extend NativeFormatHandle as a subclass. We also have NativeFormatCollection which all collections extend.

On top of that most Handles and Collections have shared handling of data as well as, for the most part, the same members. For example, all handles will always have the top 8 bits be the hType and the bottom 24 bits be the offset. In addition, all types of a certain "class" have the same constructor. 
'''


class NativeFormatHandle:
    def __init__(self, value):
        self._hType = HandleType(value >> 24)
        self._value = (value & 0x00FFFFFF) | (HandleType.Method << 24)

    @property
    def value(self):
        return self._value
    
    def AsInt(self):
        return self._value

    @property
    def hType(self):
        return self._hType

    @property
    def Offset(self):
        return self._value & 0xffffff
    
    #This method should NEVER be called directly. Instead, it should be called by a subclass
    #Pulled from https://github.com/dotnet/runtime/blob/e133fe4f5311c0397f8cc153bada693c48eb7a9f/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator/MdBinaryReaderGen.cs#L101
    #returns the new offset as well as the newly created handle. All handles have the same read. The only difference is the returned object - the underlying value is read the same way
    def Read(reader, offset, handle_type):
        (offset, value) = reader.DecodeUnsigned(offset)
        handle = handle_type(value)
        return (offset, handle)

#This class is intended for Handle collections. Evidence for this can be seen here: 
class NativeFormatCollection:
    def __init__(self, reader, offset):
        self.reader = reader
        self.offset = offset

    # pulled from: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator/MdBinaryReaderGen.cs#L62
    #returns the new offset and the newly created collection
    #All collections have the same Read. The only difference is the actual type of the collection that is returned
    def Read(reader, offset, subclass):
        values = subclass(reader, offset) 
        (offset, count) = reader.DecodeUnsigned(offset)
        for _ in range(count):
            offset = reader.SkipInteger(offset)
        return (offset, values)
    
    
    #The rest of the NativeFormatCollection stuff was pulled from: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator/ReaderGen.cs#L184
    @property
    def count(self):
        (_, count) = self.reader.DecodeUnsigned(self.offset)
        return s32(count)
    
    #All enumerators are the same except the type that is read upon going next
    class Enumerator:
        def __init__(self, reader, offset, elem_type):
            self.reader = reader
            self.offset = offset
            (self.offset, self.remaining) = reader.DecodeUnsigned(self.offset)
            self.elem_type = elem_type #elem_type is a custom type that denotes the element that this is a collection of
        
        def __iter__(self):
            return self
        
        def __next__(self):
            if self.remaining == 0:
                raise StopIteration
            self.remaining -= 1
            (self.offset, current) = self.elem_type.Read(self.reader, self.offset)
            return current
    


'''
Generic Handle

This is used in cases where handles are overloaded such as https://github.com/dotnet/runtime/blob/d8208737f8b1ede2c6673a89769dc29fb7a7f6af/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L3814
'''

class Handle(NativeFormatHandle):
    def __init__(self, value):
        super().__init__(value)

    def Read(reader, offset):
        return NativeFormatHandle.Read(reader, offset, __class__)


'''
------ScopeDefinition------
'''

#https://github.com/dotnet/runtime/blob/a72cfb0ee2669abab031c5095a670678fd0b7861/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L6193
class ScopeDefinitionHandleCollection(NativeFormatCollection):
    def __init__(self,reader, offset):
        super().__init__(reader, offset)
        
    def Read(reader, offset):
        return NativeFormatCollection.Read(reader, offset, __class__)
    
    def GetEnumerator(self):
        return NativeFormatCollection.Enumerator(self.reader, self.offset, ScopeDefinitionHandle)
    
#https://github.com/dotnet/runtime/blob/main/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L4575
class ScopeDefinition:
    def __init__(self, reader, handle):
        self.reader = reader
        self.handle = handle
        offset = handle.Offset
        streamReader = reader.streamReader
        (offset, self.flags) = AssemblyFlags.Read(streamReader, offset)
        (offset, self.name) = ConstantStringValueHandle.Read(streamReader, offset)
        (offset, self.hashAlgorithm) = AssemblyHashAlgorithm.Read(streamReader, offset)
        (offset, self.majorVersion) = UInt16.Read(streamReader, offset)
        (offset, self.minorVersion) = UInt16.Read(streamReader, offset)
        (offset, self.buildNumber) = UInt16.Read(streamReader, offset)
        (offset, self.revisionNumber) = UInt16.Read(streamReader, offset)
        (offset, self.publicKey) =  ByteCollection.Read(streamReader, offset)
        (offset, self.culture) = ConstantStringValueHandle.Read(streamReader, offset)
        (offset, self.rootNamespaceDefinition) = NamespaceDefinitionHandle.Read(streamReader, offset)
        (offset, self.entryPoint) = QualifiedMethodHandle.Read(streamReader, offset)
        (offset, self.globalModuleType) = TypeDefinitionHandle.Read(streamReader, offset)
        (offset, self.customAttributes) = CustomAttributeHandleCollection.Read(streamReader, offset)
        (offset, self.moduleName) = ConstantStringValueHandle.Read(streamReader, offset)
        (offset, self.mvid) = ByteCollection.Read(streamReader, offset)
        (offset, self.moduleCustomAttributes) = CustomAttributeHandleCollection.Read(streamReader, offset)
        
#https://github.com/dotnet/runtime/blob/main/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L4658
class ScopeDefinitionHandle(NativeFormatHandle):
    def __init__(self, value):
        super().__init__(value)
        assert self._hType == 0 or self._hType == HandleType.ScopeDefinition or self._hType == HandleType.Null

    def Read(reader, offset):
        return NativeFormatHandle.Read(reader, offset, __class__)
    
    def GetScopeDefinition(self, reader):
        return ScopeDefinition(reader, self)
    
'''
NamespaceDefinition
'''

#https://github.com/dotnet/runtime/blob/main/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L3833
class NamespaceDefinitionHandle(NativeFormatHandle):
    def __init__(self, value):
        super().__init__(value)
        assert self._hType == 0 or self._hType == HandleType.NamespaceDefinition or self._hType == HandleType.Null

    def Read(reader, offset):
        return NativeFormatHandle.Read(reader, offset, __class__)

#https://github.com/dotnet/runtime/blob/main/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L3793
class NamespaceDefinition:
    def __init__(self, reader, handle):
        self.reader = reader
        self.handle = handle
        offset = handle.Offset
        streamReader = reader.streamReader
        (offset, self.parentScopeOrNamespace) = Handle.Read(streamReader, offset)
        (offset, self.name) = ConstantStringValueHandle.Read(streamReader, offset)
        (offset, self.typeDefinitions) = TypeDefinitionHandleCollection.Read(streamReader, offset)
        #(offset, self.)

    
'''
QualifiedMethod
'''

class QualifiedMethodHandle(NativeFormatHandle):
    def __init__(self, value):
        super().__init__(value)
        assert self._hType == 0 or self._hType == HandleType.QualifiedMethod or self._hType == HandleType.Null

    def Read(reader, offset):
        return NativeFormatHandle.Read(reader, offset, __class__)
    
'''
TypeDefinition
'''

#https://github.com/dotnet/runtime/blob/main/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L4900
class TypeDefinitionHandle(NativeFormatHandle):
    def __init__(self, value):
        super().__init__(value)
        assert self._hType == 0 or self._hType == HandleType.TypeDefinition or self._hType == HandleType.Null

    def Read(reader, offset):
        return NativeFormatHandle.Read(reader, offset, __class__)
    
    def GetTypeDefinition(self, reader):
        return TypeDefinition(reader, self)
    
    
class TypeDefinitionHandleCollection(NativeFormatCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
    
    def Read(reader, offset):
        return NativeFormatCollection.Read(reader, offset, __class__)
    
    def GetEnumerator(self):
        return NativeFormatCollection.Enumerator(self.reader, self.offset, TypeDefinitionHandle)
    

#https://github.com/dotnet/runtime/blob/d8208737f8b1ede2c6673a89769dc29fb7a7f6af/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L4819
class TypeDefinition:
    def __init__(self, reader, handle):
        self.reader = reader
        self.handle = handle
        offset = handle.Offset
        streamReader = reader.streamReader
        (offset, self.flags) = streamReader.DecodeUnsigned(offset)#TypeAttributes.Read(streamReader, offset)
        (offset, self.baseType) = Handle.Read(streamReader, offset)
        (offset, self.namespaceDefinition) = NamespaceDefinitionHandle.Read(streamReader, offset)
        (offset, self.name) = ConstantStringValueHandle.Read(streamReader, offset)
        
    

    
'''
Parameter
'''

#https://github.com/dotnet/runtime/blob/a72cfb0ee2669abab031c5095a670678fd0b7861/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L5572
class ParameterHandleCollection(NativeFormatCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
    
    def Read(reader, offset):
        return NativeFormatCollection.Read(reader, offset, __class__)

'''
Generic Parameter
'''
        
#https://github.com/dotnet/runtime/blob/a72cfb0ee2669abab031c5095a670678fd0b7861/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L5641
class GenericParameterHandleCollection(NativeFormatCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
    
    def Read(reader, offset):
        return NativeFormatCollection.Read(reader, offset, __class__)


'''
CustomAttribute
'''

#https://github.com/dotnet/runtime/blob/a72cfb0ee2669abab031c5095a670678fd0b7861/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L5503
class CustomAttributeHandleCollection(NativeFormatCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
    
    def Read(reader, offset):
        return NativeFormatCollection.Read(reader, offset, __class__)
        


'''
------Method------
'''    

# pulled from: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L3175
class Method:
    def __init__(self, reader, handle):
        self.reader = reader
        self.handle = handle
        offset = u32(handle.Offset)
        streamReader = reader.streamReader
        (offset, self.flags) = MethodAttributes.Read(streamReader, offset)
        (offset, self.implFlags) = MethodImplAttributes.Read(streamReader, offset)
        (offset, self.name) = ConstantStringValueHandle.Read(streamReader, offset) 
        (offset, self.signature) = MethodSignatureHandle.Read(streamReader, offset) 
        (offset, self.parameters) = ParameterHandleCollection.Read(streamReader, offset)
        (offset, self.genericParameters) = GenericParameterHandleCollection.Read(streamReader, offset)
        (offset, self.customAttributes) = CustomAttributeHandleCollection.Read(streamReader, offset)
        

# pulled from: https://github.com/dotnet/runtime/blob/a72cfb0ee2669abab031c5095a670678fd0b7861/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L3221
class MethodHandle(NativeFormatHandle):
    def __init__(self, value):
        super().__init__(value)
        assert self._hType == 0 or self._hType == HandleType.Method or self._hType == HandleType.Null

    def GetMethod(self, reader):
        return Method(reader, self)
    
    def Read(reader, offset):
        (offset, value) = NativeFormatHandle.Read(reader, offset, __class__)


'''
------ConstantString------
'''
#this was retrieved from the disassembly
class ConstantStringValue:
    def __init__(self, reader, handle):
        self.reader = reader
        streamReader = reader.streamReader
        (_, self.value) = String.Read(streamReader, handle.Offset)
    def __str__(self):
        return self.value
    
# pulled from: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L2029
class ConstantStringValueHandle(NativeFormatHandle):
    def __init__(self, value):
        super().__init__(value)
        assert self._hType == 0 or self._hType == HandleType.ConstantStringValue or self._hType == HandleType.Null

    def Read(reader, offset):
        return NativeFormatHandle.Read(reader, offset, __class__)
    
    def GetConstantStringValue(self, metadataReader):
        return ConstantStringValue(metadataReader, self)
    

'''
------MethodSignature------
'''

# pulled from: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L3480
class MethodSignatureHandle(NativeFormatHandle):
    def __init__(self, value):
        super().__init__(value)
        assert self._hType == 0 or self._hType == HandleType.MethodSignature or self._hType == HandleType.Null
    
    def Read(reader, offset):
        return NativeFormatHandle.Read(reader, offset, __class__)


'''
------Primitive Collections------

These are output here: https://github.com/dotnet/runtime/blob/e133fe4f5311c0397f8cc153bada693c48eb7a9f/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator/ReaderGen.cs#L55
'''
    
#The difference between this and a normal NativeCollection is that a NativePrimitiveCollection
class NativePrimitiveCollection:
    def __init__(self, reader, offset):
        self.reader = reader
        self.offset = offset
    
    #This Read comes from here: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator/MdBinaryReaderGen.cs#L78
    def Read(reader, offset, subclass, elem):
        values = subclass(reader, offset)
        (offset, count) = reader.DecodeUnsigned(offset)
        offset = offset + count * elem.SIZE
        return (offset, values)

    #The enumerator is exactly the same between NativeFormatCollection and NativePrimitiveCollection
    #This is evidenced by the fact that you use the same method to emit stuff for Handle collections and primitive collections: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator/ReaderGen.cs#L48
    
class CharCollection(NativePrimitiveCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
        
    def Read(reader, offset):
        return NativePrimitiveCollection.Read(reader, offset, __class__, Char)
    
    def GetEnumerator(self):
        
        return NativeFormatCollection.Enumerator(self.reader, self.offset, Char)
    
class Int16Collection(NativePrimitiveCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
        
    def Read(reader, offset):
        return NativePrimitiveCollection.Read(reader, offset, __class__, Int16)
    
    def GetEnumerator(self):
        return NativeFormatCollection.Enumerator(self.reader, self.offset, Int16)
    
class SByteCollection(NativePrimitiveCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
        
    def Read(reader, offset):
        return NativePrimitiveCollection.Read(reader, offset, __class__, SByte)
    
    def GetEnumerator(self):
        return NativeFormatCollection.Enumerator(self.reader, self.offset, SByte)


class UInt64Collection(NativePrimitiveCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
        
    def Read(reader, offset):
        return NativePrimitiveCollection.Read(reader, offset, __class__, UInt64)
    
    def GetEnumerator(self):
        return NativeFormatCollection.Enumerator(self.reader, self.offset, UInt64)
    
class Int32Collection(NativePrimitiveCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
        
    def Read(reader, offset):
        return NativePrimitiveCollection.Read(reader, offset, __class__, Int32)
    
    def GetEnumerator(self):
        return NativeFormatCollection.Enumerator(self.reader, self.offset, Int32)
    
class UInt32Collection(NativePrimitiveCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
        
    def Read(reader, offset):
        return NativePrimitiveCollection.Read(reader, offset, __class__, UInt32)
    
    def GetEnumerator(self):
        return NativeFormatCollection.Enumerator(self.reader, self.offset, UInt32)
    
class ByteCollection(NativePrimitiveCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
        
    def Read(reader, offset):
        return NativePrimitiveCollection.Read(reader, offset, __class__, Byte)
    
    def GetEnumerator(self):
        return NativeFormatCollection.Enumerator(self.reader, self.offset, Byte)

class UInt16Collection(NativePrimitiveCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
        
    def Read(reader, offset):
        return NativePrimitiveCollection.Read(reader, offset, __class__, UInt16)
    
    def GetEnumerator(self):
        return NativeFormatCollection.Enumerator(self.reader, self.offset, UInt16)
    
class Int16Collection(NativePrimitiveCollection):
    def __init__(self, reader, offset):
        super().__init__(reader, offset)
        
    def Read(reader, offset):
        return NativePrimitiveCollection.Read(reader, offset, __class__, Int16)
    
    def GetEnumerator(self):
        return NativeFormatCollection.Enumerator(self.reader, self.offset, Int16)



'''
----------------------- Below this are QHandles -----------------------
'''

# pulled from: https://github.com/dotnet/runtime/blob/6ac8d055a200ccca0d6fa8604c18578234dffa94/src/coreclr/nativeaot/System.Private.CoreLib/src/System/Reflection/Runtime/General/QHandles.NativeFormat.cs#L39
class QTypeDefinition:
    def __init__(self, reader, handle):
        self.reader = reader
        self.handle = handle.AsInt()
        
    @property
    def NativeFormatReader(self):
        return self.reader
    

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

   
from binaryninja import *
from .utils import *
from .dotnet_enums import *
from .flags import *

#this contains the various handle types in


#https://github.com/dotnet/runtime/blob/87fea60432fb34a2537a3a593c80042d8230b986/src/mono/System.Private.CoreLib/src/System/RuntimeTypeHandle.cs#L41

#the RuntimeTypeHandle is a special case

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
    


'''
----------------------- Below this are NativeFormatHandles as well as all the classes associated with those Handles -----------------------

NativeFormatHandles are any Handles from: https://github.com/dotnet/runtime/tree/6fa9cfcdd9179a33a10c096c06150c4a11ccc93e/src/coreclr/tools/Common/Internal/Metadata/NativeFormat

as well as 

https://github.com/dotnet/runtime/blob/6fa9cfcdd9179a33a10c096c06150c4a11ccc93e/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs

They all have the same read as seen here: 
https://github.com/dotnet/runtime/blob/6fa9cfcdd9179a33a10c096c06150c4a11ccc93e/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator/MdBinaryReaderGen.cs#L50

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
    def Read(reader, offset):
        (offset, value) = reader.DecodeUnsigned(offset)
        return (offset, value)
    
    
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
        print('name',hex(streamReader.base + self.name.Offset))
        (offset, self.signature) = MethodSignatureHandle.Read(streamReader, offset) 
        (offset, self.parameters) = NativeFormatCollection.Read(streamReader, offset)
        (offset, self.genericParamters) = NativeFormatCollection.Read(streamReader, offset)
        (offset, self.customAttributes) = NativeFormatCollection.Read(streamReader, offset)

# pulled from: https://github.com/dotnet/runtime/blob/a72cfb0ee2669abab031c5095a670678fd0b7861/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L3221
class MethodHandle(NativeFormatHandle):
    def __init__(self, value):
        super().__init__(value)
        assert self._hType == 0 or self._hType == HandleType.Method or self._hType == HandleType.Null

    def GetMethod(self, reader):
        return Method(reader, self)
    
    def Read(reader, offset):
        (offset, value) = super().Read(reader, offset)
        return (offset, MethodHandle(value))
    
# pulled from: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L2029
class ConstantStringValueHandle(NativeFormatHandle):
    def __init__(self, value):
        super().__init__(value)
        assert self._hType == 0 or self._hType == HandleType.ConstantStringValue or self._hType == HandleType.Null

    def Read(reader, offset):
        (offset, value) = NativeFormatHandle.Read(reader, offset)
        return (offset, ConstantStringValueHandle(value))
    
# pulled from: https://github.com/dotnet/runtime/blob/f72784faa641a52eebf25d8212cc719f41e02143/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderGen.cs#L3480
class MethodSignatureHandle(NativeFormatHandle):
    def __init__(self, value):
        super().__init__(value)
        assert self._hType == 0 or self._hType == HandleType.MethodSignature or self._hType == HandleType.Null
    
    def Read(reader, offset):
        (offset, value) = NativeFormatHandle.Read(reader, offset)
        return (offset, MethodSignatureHandle(value))
    






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

   
from binaryninja import *
from ..nativeformat import *





#Many of these are NativeFormatEnums
#The read associated with all of these is https://github.com/dotnet/runtime/blob/e133fe4f5311c0397f8cc153bada693c48eb7a9f/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/Generator/MdBinaryReaderGen.cs#L91

#https://github.com/dotnet/runtime/blob/main/src/libraries/System.Private.CoreLib/src/System/Reflection/MethodAttributes.cs#L7
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
        return (offset, __class__(value))
    
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
        return (offset, __class__(value))
    
#https://github.com/dotnet/runtime/blob/main/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderCommonGen.cs#L22
class AssemblyFlags(Flag):
    PublicKey = 0x1
    Retargetable = 0x100
    ContentTypeMask = 0x00000e00
    def Read(reader, offset):
        (offset, value) = reader.DecodeUnsigned(offset)
        return (offset, __class__(value))
    
class AssemblyHashAlgorithm(Flag):
    none = 0x0 
    Reserved = 0x8003
    SHA1 = 0x8004
    def Read(reader, offset):
        (offset, value) = reader.DecodeUnsigned(offset)
        return (offset, __class__(value))

class TypeAttributes(Flag):
    VisibilityMask = 0x00000007
    NotPublic = 0x00000000
    Public = 0x00000001
    NestedPublic = 0x00000002
    NestedPrivate = 0x00000003
    NestedFamily = 0x00000004
    NestedAssembly = 0x00000005
    NestedFamANDAssem = 0x00000006
    NestedFamORAssem = 0x00000007

    LayoutMask = 0x00000018,
    AutoLayout = 0x00000000
    SequentialLayout = 0x00000008
    ExplicitLayout = 0x00000010

    ClassSemanticsMask = 0x00000020,
    Class = 0x00000000
    Interface = 0x00000020

    Abstract = 0x00000080
    Sealed = 0x00000100
    SpecialName = 0x00000400
    Import = 0x00001000
    Serializable = 0x00002000
    WindowsRuntime = 0x00004000

    StringFormatMask = 0x00030000,
    AnsiClass = 0x00000000
    UnicodeClass = 0x00010000
    AutoClass = 0x00020000
    CustomFormatClass = 0x00030000
    CustomFormatMask = 0x00C00000


    BeforeFieldInit = 0x00100000

    RTSpecialName = 0x00000800
    HasSecurity = 0x00040000

    ReservedMask = 0x00040800
    
    def Read(reader, offset):
        (offset, value) = reader.DecodeUnsigned(offset)
        return (offset, __class__(value))
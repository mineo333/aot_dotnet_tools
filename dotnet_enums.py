from enum import IntEnum, Flag

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
    
#https://github.com/dotnet/runtime/blob/e52cfdbea428e65307c40586e3e308aeed385e86/src/coreclr/tools/Common/Internal/Metadata/NativeFormat/NativeFormatReaderCommonGen.cs#L87
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
    

class StackTraceDataCommand(Flag):
    UpdateOwningType = 0x01
    UpdateName = 0x02
    UpdateSignature = 0x04
    UpdateGenericSignature = 0x08
    IsStackTraceHidden = 0x10
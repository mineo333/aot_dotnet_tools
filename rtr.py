from binaryninja import *
from enum import IntEnum

SECTIONS = list()


#pulled from: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/tools/Common/Internal/Runtime/ModuleHeaders.cs#L93

#pulled from: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/nativeaot/Runtime/inc/ModuleHeaders.h#L10
READY_TO_RUN_SIG = b'\x52\x54\x52\x00'

class ReadyToRunSectionType(IntEnum):
        #
        # CoreCLR ReadyToRun sections
        #
        CompilerIdentifier = 100
        ImportSections = 101
        RuntimeFunctions = 102
        MethodDefEntryPoints = 103
        ExceptionInfo = 104
        DebugInfo = 105
        DelayLoadMethodCallThunks = 106
        # 107 is deprecated - it was used by an older format of AvailableTypes
        AvailableTypes = 108
        InstanceMethodEntryPoints = 109
        InliningInfo = 110
        ProfileDataInfo = 111
        ManifestMetadata = 112
        AttributePresence = 113
        InliningInfo2 = 114
        ComponentAssemblies = 115
        OwnerCompositeExecutable = 116
        PgoInstrumentationData = 117
        ManifestAssemblyMvids = 118
        CrossModuleInlineInfo = 119
        HotColdMap = 120
        MethodIsGenericMap = 121
        EnclosingTypeMap = 122
        TypeGenericInfoMap = 123

        #
        # NativeAOT ReadyToRun sections
        #
        StringTable = 200
        GCStaticRegion = 201
        ThreadStaticRegion = 202
        TypeManagerIndirection = 204
        EagerCctor = 205
        FrozenObjectRegion = 206
        DehydratedData = 207
        ThreadStaticOffsetRegion = 208
        # 209 is unused - it was used by ThreadStaticGCDescRegion
        # 210 is unused - it was used by ThreadStaticIndex
        # 211 is unused - it was used by LoopHijackFlag
        ImportAddressTables = 212
        ModuleInitializerList = 213

        # Sections 300 - 399 are reserved for RhFindBlob backwards compatibility
        ReadonlyBlobRegionStart = 300
        ReadonlyBlobRegionEnd = 399

#define needed types
def initialize_types(bv):
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
        
#This is similar to this code: https://github.com/dotnet/runtime/blob/a3fe47ef1a8def24e8d64c305172199ae5a4ed07/src/coreclr/tools/aot/ILCompiler.Reflection.ReadyToRun/ReadyToRunHeader.cs#L93
def populate_sections(bv):
    global SECTIONS
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
    SECTIONS = bv.get_data_var_at(section_header_start).value
    
def find_section_start_end(section_id):
    global SECTIONS
    for section in SECTIONS:
        if section['SectionId'] == section_id:
            return (section['Start'], section['End'])
    raise ValueError('Could not find section', section_id)
        

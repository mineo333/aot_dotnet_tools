Extracting Reflection Data From AOT .NET binaries
-------------------------------------------------------------------

Reflection data in standard .NET binaries is well known. Through software such as dnSpy (Or, now, dnSpyEx), this reflection data as well as the associated bytecode can be extracted, analyzed, and reverse engineered.

Relatively recently, the .NET developers have introduced a new operating mode: AOT or Ahead-Of-Time.

In this operating mode, instead of JIT-compiling the bytecode, the binary is outputted as a proper executable with machine code.

However, the binary must still be a functioning .NET binary. As a result, features such as stacktrace generation and reflection must still function. To facilitate this, the data must somehow exist in the binary.

The objective of this is to lay out exactly how this reflection data is laid out and how it can be extracted for use. 

ReadyToRun Header
-------------------------------------------------------------------

AOT Reflection starts at the ReadyToRun header. The ReadyToRun header is top level structure for the AOT. The ReadyToRun header is structured as follows:


struct ReadyToRunHeader
{
    uint32_t                Signature;      // ReadyToRunHeaderConstants.Signature
    uint16_t                MajorVersion;
    uint16_t                MinorVersion;

    uint32_t                Flags;

    uint16_t                NumberOfSections;
    uint8_t                 EntrySize;
    uint8_t                 EntryType;

    // Array of sections follows.
};
Source: https://github.com/dotnet/runtime/blob/58b068bea2c150d19ff642d751e6111a50f05c33/src/coreclr/nativeaot/Runtime/inc/ModuleHeaders.h#L18

The Signature is always 0x00525452 ('\x00RTR')

Immediately following the RTR header, is an array of section headers that represent each the start of each section. The length of the array is denoted by the NumberOfSections field in the header. 

A section header looks like so:

struct ModuleInfoRow
{
    int32_t SectionId;
    int32_t Flags;
    void * Start;
    void * End;
}
Source: https://github.com/dotnet/runtime/blob/e334a1a48403dd3727ade32590fa6a6b2b400cc6/src/coreclr/nativeaot/Runtime/TypeManager.h#L27

There are two kinds of SectionIDs: ReadyToRunSectionType and ReflectionMapBlob types. The ReadyToRunSectionType are typically for sections that are key to the operation of the actual binary. The ReflectionMapBlobs are used for reflection. We primarily care about the latter. The Start and End are virtual addresses.

The first question is how do you find the ReadyToRun header? The ReadyToRun header can be determined using the call to StartupCodeHelpers::InitializeModules. The function call is typically located in wmain and the second argument is a pointer to an array of ReadyToRunHeader pointers. 

The first index in this array is the address of the header. 

ReHydration
-------------------------------------------------------------------

A key component of the .NET AOT startup process is the rehydration process. In the rehydration process, a binary is 


Reflection Blobs
-------------------------------------------------------------------


Disabling Reflection and StackTrace 
-------------------------------------------------------------------

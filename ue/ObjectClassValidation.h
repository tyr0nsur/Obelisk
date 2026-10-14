#pragma once

namespace Obelisk::UE::ObjectClassValidation
{
    // Private UE layout: UObject.ClassPrivate +0x10, UStruct.SuperStruct +0x30.
    // The caller must establish this layout for its exact executable profile
    // and supply borrowed pointers within an engine callback. Each call copies
    // the complete ancestry through SafeMemoryRead; nothing is cached or kept.
    // A matching class does not establish object lifetime or session identity.
    // Rejects unreadable, cyclic, unterminated or longer-than-32-node chains.
    bool HasClassInAncestry(void* object, void* expectedClass) noexcept;

    // For a borrowed UClass itself, traverse its SuperStruct directly. Calling
    // HasClassInAncestry on a UClass would instead follow its metaclass.
    bool ClassHasAncestor(void* currentClass, void* expectedClass) noexcept;
}

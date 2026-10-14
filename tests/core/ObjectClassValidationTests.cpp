#include "ue/ObjectClassValidation.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <new>
#include <stdexcept>
#include <sys/mman.h>
#include <unistd.h>

namespace
{
    using Obelisk::UE::ObjectClassValidation::HasClassInAncestry;
    using Obelisk::UE::ObjectClassValidation::ClassHasAncestor;

    struct ClassNode
    {
        std::array<std::byte, 0x30> Padding{};
        ClassNode* SuperStruct = nullptr;
    };
    struct Object
    {
        std::array<std::byte, 0x10> Padding{};
        ClassNode* ClassPrivate = nullptr;
    };
    static_assert(offsetof(ClassNode, SuperStruct) == 0x30);
    static_assert(offsetof(Object, ClassPrivate) == 0x10);

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    void TestActualChainAndUnrelatedClasses()
    {
        ClassNode base;
        ClassNode native;
        native.SuperStruct = &base;
        ClassNode derived;
        derived.SuperStruct = &native;
        ClassNode unrelated;
        Object object;
        object.ClassPrivate = &derived;
        Require(HasClassInAncestry(&object, &derived), "direct class rejected");
        Require(HasClassInAncestry(&object, &native), "native ancestor rejected");
        Require(HasClassInAncestry(&object, &base), "base ancestor rejected");
        Require(!HasClassInAncestry(&object, &unrelated), "unrelated class accepted");
        Require(!HasClassInAncestry(&object, nullptr), "null expected class accepted");
        Require(!HasClassInAncestry(nullptr, &native), "null object accepted");
        object.ClassPrivate = nullptr;
        Require(!HasClassInAncestry(&object, &native), "null class slot accepted");
    }

    void TestCorruptionCyclesAndDepth()
    {
        ClassNode base;
        ClassNode derived;
        derived.SuperStruct = &base;
        Object object;
        object.ClassPrivate = &derived;
        base.SuperStruct = &derived;
        Require(!HasClassInAncestry(&object, &base), "cycle accepted after finding matching class");
        derived.SuperStruct = &derived;
        Require(!HasClassInAncestry(&object, &derived), "self cycle accepted");
        derived.SuperStruct = reinterpret_cast<ClassNode*>(uintptr_t{1});
        Require(!HasClassInAncestry(&object, &derived), "unreadable ancestor accepted after match");
        object.ClassPrivate = reinterpret_cast<ClassNode*>(UINTPTR_MAX - 0x20);
        Require(!HasClassInAncestry(&object, object.ClassPrivate), "superclass offset overflow accepted");
        Require(!HasClassInAncestry(reinterpret_cast<void*>(UINTPTR_MAX - 8), &base),
                "object class offset overflow accepted");
        Require(!HasClassInAncestry(reinterpret_cast<void*>(UINTPTR_MAX - 0x10), &base),
                "pointer-field exclusive-end overflow accepted");

        std::array<ClassNode, 33> chain{};
        for (size_t i = 0; i + 1 < chain.size(); ++i)
            chain[i].SuperStruct = &chain[i + 1];
        object.ClassPrivate = &chain[0];
        chain[31].SuperStruct = nullptr;
        Require(HasClassInAncestry(&object, &chain[31]), "valid32-node ancestry rejected");
        Require(ClassHasAncestor(&chain[0], &chain[31]), "valid32-node owner ancestry rejected");
        chain[31].SuperStruct = &chain[32];
        Require(!HasClassInAncestry(&object, &chain[0]), "33-node chain accepted after early match");
        Require(!ClassHasAncestor(&chain[0], &chain[0]), "33-node owner chain accepted after early match");
    }

    void TestRawClassOwnerAncestry()
    {
        ClassNode gameMode;
        ClassNode shooterGameMode;
        shooterGameMode.SuperStruct = &gameMode;
        ClassNode blueprintGameMode;
        blueprintGameMode.SuperStruct = &shooterGameMode;
        ClassNode unrelated;
        Require(ClassHasAncestor(&blueprintGameMode, &blueprintGameMode), "direct declaring owner rejected");
        Require(ClassHasAncestor(&blueprintGameMode, &shooterGameMode), "derived owner rejected");
        Require(ClassHasAncestor(&blueprintGameMode, &gameMode), "engine declaration base rejected");
        Require(!ClassHasAncestor(&gameMode, &shooterGameMode), "owner below native declaration accepted");
        Require(!ClassHasAncestor(&blueprintGameMode, &unrelated), "unrelated declaring owner accepted");
        Require(!ClassHasAncestor(nullptr, &gameMode), "null class accepted");
        Require(!ClassHasAncestor(&gameMode, nullptr), "null ancestor accepted");
        // UClass.ClassPrivate describes its metaclass. The raw-chain helper
        // must ignore that slot and walk the class's own SuperStruct instead.
        void* metaclass = &unrelated;
        std::memcpy(blueprintGameMode.Padding.data() + 0x10, &metaclass, sizeof(metaclass));
        Require(!HasClassInAncestry(&blueprintGameMode, &gameMode), "metaclass confused with owner inheritance");
        Require(ClassHasAncestor(&blueprintGameMode, &gameMode), "raw owner chain followed metaclass");
        gameMode.SuperStruct = &blueprintGameMode;
        Require(!ClassHasAncestor(&blueprintGameMode, &shooterGameMode), "cyclic owner accepted after match");
        gameMode.SuperStruct = reinterpret_cast<ClassNode*>(uintptr_t{1});
        Require(!ClassHasAncestor(&blueprintGameMode, &shooterGameMode), "inaccessible owner ancestor accepted");
        Require(!ClassHasAncestor(reinterpret_cast<void*>(UINTPTR_MAX - 0x20), &gameMode),
                "raw owner offset overflow accepted");
    }

    void TestProtectionChangesAndIncompleteFields()
    {
        const long pageSizeResult = sysconf(_SC_PAGESIZE);
        Require(pageSizeResult > 0, "page size unavailable");
        const auto pageSize = static_cast<size_t>(pageSizeResult);
        void* mapping = mmap(nullptr, pageSize * 2, PROT_READ | PROT_WRITE,
                             MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        Require(mapping != MAP_FAILED, "mmap failed");
        auto* node = new (mapping) ClassNode;
        Object object;
        object.ClassPrivate = node;
        Require(HasClassInAncestry(&object, node), "mapped class rejected");
        Require(mprotect(mapping, pageSize, PROT_NONE) == 0, "mprotect none failed");
        Require(!HasClassInAncestry(&object, node), "old readable class accepted after mprotect");
        Require(!ClassHasAncestor(node, node), "protected raw owner accepted after match");
        Require(mprotect(mapping, pageSize, PROT_READ | PROT_WRITE) == 0,
                "mprotect restore failed");
        Require(HasClassInAncestry(&object, node), "restored readable class rejected");

        ClassNode base;
        // The class-pointer field straddles the page boundary. Kernel copying
        // must reject the whole validation if only half the field is readable.
        auto* incompleteObject = static_cast<std::byte*>(mapping) + pageSize - 0x10 - 4;
        ClassNode* classPointer = &base;
        std::memcpy(incompleteObject + 0x10, &classPointer, sizeof(classPointer));
        auto* incompleteClass = static_cast<std::byte*>(mapping) + pageSize - 0x30 - 4;
        Require(ClassHasAncestor(incompleteClass, &base), "readable page-crossing owner field rejected");
        Require(mprotect(static_cast<std::byte*>(mapping) + pageSize, pageSize, PROT_NONE) == 0,
                "second page protection failed");
        Require(!HasClassInAncestry(incompleteObject, &base), "partial class-pointer copy accepted");
        Require(!ClassHasAncestor(incompleteClass, incompleteClass), "partial owner-super copy accepted after match");
        Require(munmap(mapping, pageSize * 2) == 0, "munmap failed");
        Require(!HasClassInAncestry(&object, node), "unmapped matched class accepted");
        Require(!ClassHasAncestor(node, node), "unmapped raw owner accepted");
    }

    void TestReusedAddressDoesNotReuseValidation()
    {
        ClassNode playerClass;
        ClassNode unrelatedClass;
        alignas(Object) std::array<std::byte, sizeof(Object)> storage{};
        auto* first = new (storage.data()) Object;
        first->ClassPrivate = &playerClass;
        void* sameAddress = first;
        Require(HasClassInAncestry(sameAddress, &playerClass), "initial class rejected");
        first->~Object();
        auto* replacement = new (storage.data()) Object;
        replacement->ClassPrivate = &unrelatedClass;
        Require(sameAddress == replacement, "replacement did not reuse same address");
        Require(!HasClassInAncestry(sameAddress, &playerClass), "old validation cached for reused address");
        Require(HasClassInAncestry(sameAddress, &unrelatedClass), "replacement class context rejected");
        replacement->~Object();
        // This proves re-reading class context, not lifetime/session validity.
    }
}

int main()
{
    TestActualChainAndUnrelatedClasses();
    TestCorruptionCyclesAndDepth();
    TestRawClassOwnerAncestry();
    TestProtectionChangesAndIncompleteFields();
    TestReusedAddressDoesNotReuseValidation();
    std::cout << "ObjectClassValidationTests passed\n";
    return 0;
}

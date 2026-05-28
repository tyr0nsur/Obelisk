#include "hooks/ProcessEventCallGuard.h"

#include <iostream>
#include <stdexcept>

namespace
{
    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    void TestMarkOutsidePreCallbackIsIgnored()
    {
        Require(!Obelisk::Hooks::ProcessEventCallGuard::IsInsidePreCallback(),
                "test started inside a pre-callback scope");
        Obelisk::Hooks::ProcessEventCallGuard::MarkOriginalCalledFromPublicApi();
        Require(!Obelisk::Hooks::ProcessEventCallGuard::IsInsidePreCallback(),
                "mark outside scope created a pre-callback scope");
    }

    void TestScopeRecordsOriginalCall()
    {
        Obelisk::Hooks::ProcessEventCallGuard::PreCallbackScope scope;
        Require(Obelisk::Hooks::ProcessEventCallGuard::IsInsidePreCallback(),
                "pre-callback scope was not active");
        Require(!scope.OriginalCalled(), "new pre-callback scope started dirty");

        Obelisk::Hooks::ProcessEventCallGuard::MarkOriginalCalledFromPublicApi();
        Require(scope.OriginalCalled(), "manual original call was not recorded");
    }

    void TestNestedScopesDoNotClobberOuterState()
    {
        Obelisk::Hooks::ProcessEventCallGuard::PreCallbackScope outer;
        Obelisk::Hooks::ProcessEventCallGuard::MarkOriginalCalledFromPublicApi();

        {
            Obelisk::Hooks::ProcessEventCallGuard::PreCallbackScope inner;
            Require(!inner.OriginalCalled(), "nested pre-callback scope inherited outer state");
            Obelisk::Hooks::ProcessEventCallGuard::MarkOriginalCalledFromPublicApi();
            Require(inner.OriginalCalled(), "nested manual original call was not recorded");
        }

        Require(outer.OriginalCalled(), "nested pre-callback scope clobbered outer state");
    }

    void TestSiblingScopesAreIndependent()
    {
        {
            Obelisk::Hooks::ProcessEventCallGuard::PreCallbackScope first;
            Obelisk::Hooks::ProcessEventCallGuard::MarkOriginalCalledFromPublicApi();
            Require(first.OriginalCalled(), "first sibling did not record manual original call");
        }

        Obelisk::Hooks::ProcessEventCallGuard::PreCallbackScope second;
        Require(!second.OriginalCalled(), "second sibling inherited stale state");
    }
}

int main()
{
    TestMarkOutsidePreCallbackIsIgnored();
    TestScopeRecordsOriginalCall();
    TestNestedScopesDoNotClobberOuterState();
    TestSiblingScopesAreIndependent();

    std::cout << "ProcessEventCallGuardTests passed\n";
    return 0;
}

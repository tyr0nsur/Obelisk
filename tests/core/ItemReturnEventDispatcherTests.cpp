#include "core/ItemReturnEventDispatcher.h"

#include <cstdint>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace
{
    struct Capture
    {
        int Calls = 0;
        Obelisk::Core::ItemReturnEventKind Kind = Obelisk::Core::ItemReturnEventKind::AllowEquipItem;
        std::vector<Obelisk::Core::ItemReturnScalarValue> Scalars;
        const Obelisk::Core::ItemReturnScalarValue* ScalarPointer = nullptr;
    };

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    std::vector<Obelisk::Core::ItemReturnScalarValue> MakeScalars(bool returnValue = true)
    {
        return {{
            .Field = Obelisk::Core::ItemReturnScalarField::ReturnValue,
            .BoolValue = returnValue,
        }};
    }

    Obelisk::Core::ItemReturnEventView MakeEvent(
        Obelisk::Core::ItemReturnEventKind kind,
        const std::vector<Obelisk::Core::ItemReturnScalarValue>& scalars)
    {
        return {
            .Kind = kind,
            .Scalars = scalars,
        };
    }

    Obelisk::Core::ItemReturnEventView MakeEvent(
        const std::vector<Obelisk::Core::ItemReturnScalarValue>& scalars)
    {
        return MakeEvent(Obelisk::Core::ItemReturnEventKind::AllowEquipItem, scalars);
    }

    void CaptureCallback(const Obelisk::Core::ItemReturnEventView& event, void* userData)
    {
        auto* capture = static_cast<Capture*>(userData);
        ++capture->Calls;
        capture->Kind = event.Kind;
        capture->Scalars.assign(event.Scalars.begin(), event.Scalars.end());
        capture->ScalarPointer = event.Scalars.data();
    }

    void ThrowingCallback(const Obelisk::Core::ItemReturnEventView&, void*)
    {
        throw std::runtime_error("expected item return dispatcher test exception");
    }

    void TestDispatchCopiesScalarInputForCallbackDuration()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars(false);
        const auto* sourcePointer = scalars.data();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(dispatcher.Dispatch(MakeEvent(Obelisk::Core::ItemReturnEventKind::UseItemOntoItem, scalars)) == 1,
                "dispatch count was wrong");

        Require(capture.Calls == 1, "callback did not run");
        Require(capture.Kind == Obelisk::Core::ItemReturnEventKind::UseItemOntoItem,
                "event kind changed");
        Require(capture.Scalars.size() == 1, "scalar count mismatch");
        Require(capture.Scalars[0].Field == Obelisk::Core::ItemReturnScalarField::ReturnValue,
                "return scalar field mismatch");
        Require(!capture.Scalars[0].BoolValue, "return scalar value mismatch");
        Require(capture.ScalarPointer != sourcePointer, "dispatcher passed borrowed scalar storage");
    }

    void TestRegisterRejectsInvalidInput()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;

        Require(dispatcher.Register(nullptr, {CaptureCallback, &capture}) == 0,
                "registration without owner was accepted");
        Require(dispatcher.Register(&owner, {nullptr, &capture}) == 0,
                "registration without callback was accepted");
        Require(dispatcher.SubscriptionCount() == 0, "invalid registrations were stored");
    }

    void TestDispatchRejectsUnknownEventShape()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        Obelisk::Core::ItemReturnEventView unknownKind = MakeEvent(scalars);
        unknownKind.Kind = static_cast<Obelisk::Core::ItemReturnEventKind>(99);
        Require(dispatcher.Dispatch(unknownKind) == 0, "unknown item return event kind was dispatched");

        Obelisk::Core::ItemReturnEventView unknownScalar = MakeEvent(scalars);
        scalars[0].Field = static_cast<Obelisk::Core::ItemReturnScalarField>(99);
        unknownScalar.Scalars = scalars;
        Require(dispatcher.Dispatch(unknownScalar) == 0, "unknown item return scalar was dispatched");
        Require(capture.Calls == 0, "invalid item return event reached callback");
    }

    void TestDispatchRejectsUnexpectedScalarShape()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        scalars.clear();
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0,
                "missing item return scalar was dispatched");

        scalars = MakeScalars();
        scalars.push_back({
            .Field = Obelisk::Core::ItemReturnScalarField::ReturnValue,
            .BoolValue = false,
        });
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0,
                "extra item return scalar was dispatched");
        Require(capture.Calls == 0, "invalid scalar shapes reached callback");

        scalars = MakeScalars();
        Require(dispatcher.Dispatch(MakeEvent(Obelisk::Core::ItemReturnEventKind::AllowEquipItem, scalars)) == 1,
                "valid AllowEquipItem item return shape was rejected");
        Require(dispatcher.Dispatch(MakeEvent(Obelisk::Core::ItemReturnEventKind::CanRepair, scalars)) == 1,
                "valid CanRepair item return shape was rejected");
        Require(dispatcher.Dispatch(MakeEvent(Obelisk::Core::ItemReturnEventKind::UseItemOntoItem, scalars)) == 1,
                "valid UseItemOntoItem item return shape was rejected");
        Require(capture.Calls == 3, "valid item return events did not reach callback");
    }

    void TestUnregisterForOwnerRequiresMatchingOwner()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        int otherOwner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(!dispatcher.UnregisterCallbackForOwner(&otherOwner, id),
                "wrong owner unregistered an item return callback");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "callback was removed by wrong owner");
        Require(dispatcher.UnregisterCallbackForOwner(&owner, id),
                "matching owner could not unregister item return callback");
        Require(!dispatcher.UnregisterCallbackForOwner(&owner, id),
                "matching owner unregister succeeded twice");
        Require(!dispatcher.UnregisterCallbackForOwner(&owner, 0),
                "zero registration id unregistered an item return callback");
        Require(!dispatcher.UnregisterCallbackForOwner(nullptr, id),
                "null owner unregistered an item return callback");
        Require(dispatcher.SubscriptionCount() == 0, "owner-scoped unregister left callback behind");
    }

    void TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;

        const uint64_t firstId = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(firstId == 1, "first registration id was not one");

        dispatcher.SetNextRegistrationIdForTesting(std::numeric_limits<uint64_t>::max());
        const uint64_t lastId = dispatcher.Register(&owner, {CaptureCallback, &capture});
        const uint64_t wrappedId = dispatcher.Register(&owner, {CaptureCallback, &capture});

        Require(lastId == std::numeric_limits<uint64_t>::max(), "last registration id was not preserved");
        Require(wrappedId == 2, "wrapped registration id did not skip zero or live ids");
        Require(wrappedId != firstId, "wrapped registration reused a live registration id");
        Require(!dispatcher.Unregister(0), "zero registration id unregistered a callback after wrap");
        Require(dispatcher.Unregister(firstId), "first registration id could not unregister");
        Require(dispatcher.Unregister(lastId), "last registration id could not unregister");
        Require(dispatcher.Unregister(wrappedId), "wrapped registration id could not unregister");
        Require(dispatcher.SubscriptionCount() == 0, "wrapped registrations survived unregister");
    }

    struct SelfUnregisterDestroyCapture
    {
        Obelisk::Core::ItemReturnEventDispatcher* Dispatcher = nullptr;
        uint64_t RegistrationId = 0;
        int Calls = 0;
        int Destroyed = 0;
    };

    void SelfUnregisterWithDestroyCallback(const Obelisk::Core::ItemReturnEventView&, void* userData)
    {
        auto* capture = static_cast<SelfUnregisterDestroyCapture*>(userData);
        ++capture->Calls;
        Require(capture->Destroyed == 0, "item return user data was destroyed before callback body");
        Require(capture->Dispatcher != nullptr, "self-unregister destroy callback had no dispatcher");
        Require(capture->Dispatcher->Unregister(capture->RegistrationId),
                "self-unregister with destroy from item return callback failed");
        Require(capture->Destroyed == 0, "item return user data was destroyed before callback returned");
    }

    void CountSelfUnregisterDestroyed(void* userData)
    {
        auto* capture = static_cast<SelfUnregisterDestroyCapture*>(userData);
        ++capture->Destroyed;
    }

    void TestSelfUnregisterDefersUserDataDestroyUntilCallbackReturns()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        SelfUnregisterDestroyCapture capture{&dispatcher, 0, 0, 0};
        const std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();

        capture.RegistrationId = dispatcher.Register(
            &owner,
            {SelfUnregisterWithDestroyCallback, &capture, CountSelfUnregisterDestroyed});
        Require(capture.RegistrationId != 0, "self-unregister destroy registration id was not assigned");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "self-unregister destroy item return callback did not run");
        Require(capture.Calls == 1, "self-unregister destroy item return callback ran wrong number of times");
        Require(capture.Destroyed == 1, "item return user data was not destroyed after callback returned");
        Require(dispatcher.SubscriptionCount() == 0,
                "self-unregister destroy item return callback remained registered");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0, "self-unregistered callback ran twice");
    }

    void TestCallbackExceptionDoesNotStopDispatch()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();

        Require(dispatcher.Register(&owner, {ThrowingCallback, nullptr}) != 0,
                "throwing callback registration failed");
        Require(dispatcher.Register(&owner, {CaptureCallback, &capture}) != 0,
                "capture callback registration failed");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "throwing callback counted as successful dispatch or stopped later callback");
        Require(capture.Calls == 1, "callback after throwing item return callback did not run");
        Require(dispatcher.SubscriptionCount() == 2, "exception changed item return registrations");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 2,
                "owner cleanup after exception removed wrong callback count");
    }
}

int main()
{
    try
    {
        TestDispatchCopiesScalarInputForCallbackDuration();
        TestRegisterRejectsInvalidInput();
        TestDispatchRejectsUnknownEventShape();
        TestDispatchRejectsUnexpectedScalarShape();
        TestUnregisterForOwnerRequiresMatchingOwner();
        TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap();
        TestSelfUnregisterDefersUserDataDestroyUntilCallbackReturns();
        TestCallbackExceptionDoesNotStopDispatch();
    }
    catch (const std::exception& e)
    {
        std::cerr << "ItemReturnEventDispatcherTests failed: " << e.what() << "\n";
        return 1;
    }

    std::cout << "ItemReturnEventDispatcherTests passed\n";
    return 0;
}

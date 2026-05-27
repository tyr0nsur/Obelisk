#include "core/ChatEventDispatcher.h"

#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

namespace
{
    struct Capture
    {
        int calls = 0;
        std::string message;
        std::string senderName;
        std::string senderPlatformId;
        Obelisk::Core::ChatSendMode sendMode = Obelisk::Core::ChatSendMode::Global;
        int32_t senderNameIndex = -1;
        const char* messagePointer = nullptr;
    };

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    void CaptureCallback(const Obelisk::Core::ChatMessageView& message, void* userData)
    {
        auto* capture = static_cast<Capture*>(userData);
        ++capture->calls;
        capture->message = std::string(message.Message);
        capture->senderName = std::string(message.SenderName);
        capture->senderPlatformId = std::string(message.SenderPlatformId);
        capture->sendMode = message.SendMode;
        capture->senderNameIndex = message.SenderNameIndex;
        capture->messagePointer = message.Message.data();
    }

    void ThrowingCallback(const Obelisk::Core::ChatMessageView&, void*)
    {
        throw std::runtime_error("expected test exception");
    }

    Obelisk::Core::ChatMessageView MakeMessage(std::string_view text = "hello from copied chat")
    {
        return {
            .Message = text,
            .SenderName = "PlayerOne",
            .SenderPlatformId = "123456789",
            .SendMode = Obelisk::Core::ChatSendMode::Global,
            .SenderNameIndex = 42,
        };
    }

    void TestDispatchCopiesInputForCallbackDuration()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::string source = "message that should be copied before callbacks";
        const char* sourcePointer = source.data();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(dispatcher.Dispatch(MakeMessage(source)) == 1, "dispatch count was wrong");

        Require(capture.calls == 1, "callback did not run");
        Require(capture.message == source, "message text was not copied through callback");
        Require(capture.senderName == "PlayerOne", "sender name was not copied");
        Require(capture.senderPlatformId == "123456789", "sender platform id was not copied");
        Require(capture.sendMode == Obelisk::Core::ChatSendMode::Global, "send mode changed");
        Require(capture.senderNameIndex == 42, "sender name index changed");
        Require(capture.messagePointer != sourcePointer, "dispatcher passed borrowed input text");
    }

    void TestRegisterRejectsInvalidInput()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;

        Require(dispatcher.Register(nullptr, {CaptureCallback, &capture}) == 0,
                "registration without owner was accepted");
        Require(dispatcher.Register(&owner, {nullptr, &capture}) == 0,
                "registration without callback was accepted");
        Require(dispatcher.SubscriptionCount() == 0, "invalid registrations were stored");
    }

    void TestUnregisterIsIdempotent()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(dispatcher.Unregister(id), "first unregister failed");
        Require(!dispatcher.Unregister(id), "second unregister was not idempotent");
        Require(dispatcher.Dispatch(MakeMessage()) == 0, "unregistered callback ran");
    }

    void TestOwnerCleanup()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int ownerA = 0;
        int ownerB = 0;
        Capture captureA;
        Capture captureB;

        dispatcher.Register(&ownerA, {CaptureCallback, &captureA});
        dispatcher.Register(&ownerA, {CaptureCallback, &captureA});
        dispatcher.Register(&ownerB, {CaptureCallback, &captureB});

        Require(dispatcher.UnregisterCallbacksForOwner(&ownerA) == 2, "owner cleanup removed wrong count");
        Require(dispatcher.Dispatch(MakeMessage()) == 1, "wrong number of callbacks after owner cleanup");
        Require(captureA.calls == 0, "owner A callback survived cleanup");
        Require(captureB.calls == 1, "owner B callback did not run");
    }

    void TestRejectsUnknownSendMode()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        Obelisk::Core::ChatMessageView message = MakeMessage();
        message.SendMode = static_cast<Obelisk::Core::ChatSendMode>(4);
        Require(dispatcher.Dispatch(message) == 0, "unknown send mode was dispatched");
        Require(capture.calls == 0, "unknown send mode reached callback");
    }

    void TestExceptionsDoNotStopDispatch()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        dispatcher.Register(&owner, {ThrowingCallback, nullptr});
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        Require(dispatcher.Dispatch(MakeMessage()) == 1, "successful dispatch count ignored exception");
        Require(capture.calls == 1, "callback after exception did not run");
    }
}

int main()
{
    TestDispatchCopiesInputForCallbackDuration();
    TestRegisterRejectsInvalidInput();
    TestUnregisterIsIdempotent();
    TestOwnerCleanup();
    TestRejectsUnknownSendMode();
    TestExceptionsDoNotStopDispatch();

    std::cout << "ChatEventDispatcherTests passed\n";
    return 0;
}

---
name: obelisk-ue4-reflection
description: Guidelines on how to use ProcessEvent and UE4 reflection instead of hardcoded offsets for the Obelisk runtime.
---

# Obelisk UE4 Reflection Skill

**Context:** Obelisk relies on UE4's reflection system (`UObject`, `UFunction`, `ProcessEvent`) rather than hardcoded memory offsets. This ensures the runtime remains robust across ARK server updates.

**When to use this skill:**
- When needing to access game data (Player, Dino, World).
- When searching for a function to hook or call.
- When creating SDK wrappers.

## Principles: Reflection over Offsets

### 1. Intercepting and Calling Gameplay Functions
The primary artery for UE4 gameplay logic is `UObject::ProcessEvent`.
Instead of searching for offsets for every function (e.g., `AddExperience`, `BroadcastMessage`), we:
1. Locate `UObject::ProcessEvent`.
2. Find the specific `UFunction` by name using the Global Objects Array (GObjects) or `FindObject<UFunction>("Function Name")`.
3. Intercept it using our central `ProcessEvent` hook, or call it directly by allocating the parameters struct.

### 2. FName Handling
UE4 relies heavily on `FName` for identifying objects and properties.
- When implementing reflection tools, ensure you locate the `FName::ToString` or `FNamePool` logic.

### 3. Creating SDK Wrappers
When building the `sdk/` wrappers (e.g., `Player`, `Dino`), abstract the `ProcessEvent` calls away from the user.

**SDK Wrapper Pattern:**
```cpp
// Inside sdk/Player.cpp
void Player::GiveItem(const char* blueprint_path, int quantity) {
    // 1. Get the target UFunction from reflection
    UFunction* func = FindFunctionByName("Function ShooterGame.ShooterPlayerController.GiveItem");
    
    // 2. Setup the struct mimicking the UE4 parameters
    struct GiveItemParams {
        FString BlueprintPath;
        int Quantity;
    } params;
    
    // ... Initialize params ...
    
    // 3. Call ProcessEvent
    this->internal_uobject->ProcessEvent(func, &params);
}
```

## Checklist for Reflection Usage
- [ ] Is the data accessible via `UProperty` reflection rather than a hardcoded struct offset?
- [ ] Have you verified the `UFunction` signature using a recent Dumper-7 or UE4SS output?
- [ ] Are we using `ProcessEvent` instead of a direct function call offset when possible?

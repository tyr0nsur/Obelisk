#include "runtime/RuntimeMarkers.h"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace
{
    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    std::filesystem::path MakeTempRoot()
    {
        std::filesystem::path pattern =
            std::filesystem::temp_directory_path() / "obelisk-runtime-markers-XXXXXX";
        std::string path = pattern.string();
        char* result = mkdtemp(path.data());
        if (!result)
            throw std::runtime_error("mkdtemp failed");
        return result;
    }

    void Touch(const std::filesystem::path& path)
    {
        std::filesystem::create_directories(path.parent_path());
        std::ofstream file(path);
        if (!file)
            throw std::runtime_error("failed to create marker file");
    }

    void TestSafeMarkerComponents()
    {
        using Obelisk::Runtime::IsSafeMarkerComponent;

        Require(IsSafeMarkerComponent("arkserver2"), "normal instance id was rejected");
        Require(IsSafeMarkerComponent("arkserver-obelisk_debug"), "safe punctuation was rejected");
        Require(!IsSafeMarkerComponent(""), "empty component was accepted");
        Require(!IsSafeMarkerComponent("../arkserver"), "path traversal component was accepted");
        Require(!IsSafeMarkerComponent("ark/server"), "slash component was accepted");
        Require(!IsSafeMarkerComponent("ark.server"), "dot component was accepted");
        Require(!IsSafeMarkerComponent("ark server"), "space component was accepted");
    }

    void TestInstanceMarkerEnabled()
    {
        const std::filesystem::path root = MakeTempRoot();

        Require(!Obelisk::Runtime::IsInstanceMarkerEnabled(nullptr, "arkserver2", "enable-inventory-reflection"),
                "null root was accepted");
        Require(!Obelisk::Runtime::IsInstanceMarkerEnabled(root.c_str(), nullptr, "enable-inventory-reflection"),
                "null instance was accepted");
        Require(!Obelisk::Runtime::IsInstanceMarkerEnabled(root.c_str(), "arkserver2", nullptr),
                "null marker was accepted");
        Require(!Obelisk::Runtime::IsInstanceMarkerEnabled(root.c_str(), "ark/server2", "enable-inventory-reflection"),
                "unsafe instance id was accepted");
        Require(!Obelisk::Runtime::IsInstanceMarkerEnabled(root.c_str(), "arkserver2", "../enable-inventory-reflection"),
                "unsafe marker name was accepted");

        const std::filesystem::path marker =
            root / "state" / "instances" / "arkserver2" / "enable-inventory-reflection";
        Require(!Obelisk::Runtime::IsInstanceMarkerEnabled(root.c_str(), "arkserver2", "enable-inventory-reflection"),
                "missing marker was accepted");

        std::filesystem::create_directories(marker);
        Require(!Obelisk::Runtime::IsInstanceMarkerEnabled(root.c_str(), "arkserver2", "enable-inventory-reflection"),
                "directory marker was accepted");
        std::filesystem::remove(marker);

        Touch(marker);
        Require(Obelisk::Runtime::IsInstanceMarkerEnabled(root.c_str(), "arkserver2", "enable-inventory-reflection"),
                "regular marker file was rejected");

        std::filesystem::remove(marker);
        const std::filesystem::path target = root / "target-marker";
        Touch(target);
        std::filesystem::create_symlink(target, marker);
        Require(!Obelisk::Runtime::IsInstanceMarkerEnabled(root.c_str(), "arkserver2", "enable-inventory-reflection"),
                "symlink marker was accepted");

        std::filesystem::remove(marker);
        const std::filesystem::path instanceDir = root / "state" / "instances" / "arkserver2";
        std::filesystem::remove_all(instanceDir);
        const std::filesystem::path realInstanceDir = root / "real-instance";
        std::filesystem::create_directories(realInstanceDir);
        Touch(realInstanceDir / "enable-inventory-reflection");
        std::filesystem::create_symlink(realInstanceDir, instanceDir);
        Require(!Obelisk::Runtime::IsInstanceMarkerEnabled(root.c_str(), "arkserver2", "enable-inventory-reflection"),
                "symlink instance directory was accepted");

        std::filesystem::remove_all(root);
    }
}

int main()
{
    TestSafeMarkerComponents();
    TestInstanceMarkerEnabled();

    std::cout << "RuntimeMarkerTests passed\n";
    return 0;
}

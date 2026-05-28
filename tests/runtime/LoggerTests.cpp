#include "runtime/Logger.h"

#include <cstdlib>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

namespace
{
    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    fs::path MakeTempRoot(const char* name)
    {
        const auto now = std::chrono::steady_clock::now().time_since_epoch().count();
        fs::path root = fs::temp_directory_path() / (std::string(name) + "_" + std::to_string(now));
        fs::create_directories(root);
        return root;
    }

    void ResetEnv()
    {
        Obelisk::Logger::Shutdown();
        unsetenv("OBELISK_LOG_DIR");
        unsetenv("OBELISK_ROOT");
        unsetenv("OBELISK_INSTANCE_ID");
    }

    void ExpectInitThrowsContaining(const std::string& expected)
    {
        bool threw = false;
        try
        {
            Obelisk::Logger::Init();
        }
        catch (const std::exception& e)
        {
            threw = true;
            Require(std::string(e.what()).find(expected) != std::string::npos,
                    "logger init error did not contain expected text");
        }
        Require(threw, "logger init unexpectedly succeeded");
        Require(!Obelisk::Logger::IsInitialized(), "logger stayed initialized after failed init");
    }

    void TestExplicitLogDirCreatesInstanceLogs()
    {
        ResetEnv();
        const fs::path root = MakeTempRoot("obelisk_logger_explicit");
        setenv("OBELISK_LOG_DIR", (root / "logs").string().c_str(), 1);
        setenv("OBELISK_INSTANCE_ID", "arkserver", 1);

        Obelisk::Logger::Init();
        Require(Obelisk::Logger::IsInitialized(), "logger did not initialize");
        OBELISK_INFO("logger test message");
        Obelisk::Logger::Shutdown();

        Require(fs::is_regular_file(root / "logs" / "arkserver" / "Obelisk.log"),
                "shared instance log was not created");
        Require(fs::is_regular_file(root / "logs" / "arkserver" / "Obelisk-unknown.log"),
                "map-specific instance log was not created");
        fs::remove_all(root);
    }

    void TestRejectsRelativeExplicitLogDir()
    {
        ResetEnv();
        setenv("OBELISK_LOG_DIR", "relative-logs", 1);

        ExpectInitThrowsContaining("absolute");
    }

    void TestRejectsSymlinkExplicitLogDir()
    {
        ResetEnv();
        const fs::path root = MakeTempRoot("obelisk_logger_symlink_log_dir");
        const fs::path external = root / "external-logs";
        fs::create_directories(external);
        fs::create_symlink(external, root / "log-link");
        setenv("OBELISK_LOG_DIR", (root / "log-link").string().c_str(), 1);

        ExpectInitThrowsContaining("symlink");
        fs::remove_all(root);
    }

    void TestRejectsSymlinkInstanceLogDir()
    {
        ResetEnv();
        const fs::path root = MakeTempRoot("obelisk_logger_symlink_instance");
        fs::create_directories(root / "logs");
        const fs::path external = root / "external-instance-logs";
        fs::create_directories(external);
        fs::create_symlink(external, root / "logs" / "arkserver");
        setenv("OBELISK_LOG_DIR", (root / "logs").string().c_str(), 1);
        setenv("OBELISK_INSTANCE_ID", "arkserver", 1);

        ExpectInitThrowsContaining("symlink");
        fs::remove_all(root);
    }

    void TestRejectsRootDerivedSymlinkLogDir()
    {
        ResetEnv();
        const fs::path root = MakeTempRoot("obelisk_logger_root_symlink");
        const fs::path external = root / "external-logs";
        fs::create_directories(external);
        fs::create_symlink(external, root / "logs");
        setenv("OBELISK_ROOT", root.string().c_str(), 1);

        ExpectInitThrowsContaining("symlink");
        fs::remove_all(root);
    }
}

int main()
{
    try
    {
        TestExplicitLogDirCreatesInstanceLogs();
        TestRejectsRelativeExplicitLogDir();
        TestRejectsSymlinkExplicitLogDir();
        TestRejectsSymlinkInstanceLogDir();
        TestRejectsRootDerivedSymlinkLogDir();
        ResetEnv();
        std::cout << "LoggerTests passed\n";
        return 0;
    }
    catch (const std::exception& e)
    {
        ResetEnv();
        std::cerr << "LoggerTests failed: " << e.what() << '\n';
        return 1;
    }
}

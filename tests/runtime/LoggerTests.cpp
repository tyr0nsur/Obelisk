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

    void TestRejectsMissingLogRoot()
    {
        ResetEnv();

        ExpectInitThrowsContaining("OBELISK_LOG_DIR or OBELISK_ROOT");
    }

    void TestRejectsRelativeExplicitLogDir()
    {
        ResetEnv();
        setenv("OBELISK_LOG_DIR", "relative-logs", 1);

        ExpectInitThrowsContaining("absolute");
    }

    void TestRejectsRelativeRootDerivedLogDir()
    {
        ResetEnv();
        const auto now = std::chrono::steady_clock::now().time_since_epoch().count();
        const fs::path relativeRoot = std::string("obelisk_logger_relative_root_") + std::to_string(now);
        fs::remove_all(relativeRoot);
        setenv("OBELISK_ROOT", relativeRoot.string().c_str(), 1);

        ExpectInitThrowsContaining("absolute");
        Require(!fs::exists(relativeRoot / "logs"), "logger created logs from a relative OBELISK_ROOT");
        fs::remove_all(relativeRoot);
    }

    void TestRejectsExplicitLogDirWithParentAlias()
    {
        ResetEnv();
        const fs::path root = MakeTempRoot("obelisk_logger_parent_alias_log_dir");
        setenv("OBELISK_LOG_DIR", (root / "missing-parent" / ".." / "escaped-logs").string().c_str(), 1);

        ExpectInitThrowsContaining("path alias");
        Require(!fs::exists(root / "missing-parent"), "logger created a parent-alias log component");
        Require(!fs::exists(root / "escaped-logs"), "logger created logs through a parent-directory alias");
        fs::remove_all(root);
    }

    void TestRejectsExplicitLogDirWithCurrentAlias()
    {
        ResetEnv();
        const fs::path root = MakeTempRoot("obelisk_logger_current_alias_log_dir");
        setenv("OBELISK_LOG_DIR", (root / "." / "logs").string().c_str(), 1);

        ExpectInitThrowsContaining("path alias");
        Require(!fs::exists(root / "logs"), "logger created logs through a current-directory alias");
        fs::remove_all(root);
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

    void TestRejectsSymlinkExplicitLogDirAncestor()
    {
        ResetEnv();
        const fs::path root = MakeTempRoot("obelisk_logger_symlink_log_dir_ancestor");
        const fs::path external = root / "external-parent";
        fs::create_directories(external);
        fs::create_symlink(external, root / "log-parent-link");
        setenv("OBELISK_LOG_DIR", (root / "log-parent-link" / "logs").string().c_str(), 1);

        ExpectInitThrowsContaining("symlink");
        Require(!fs::exists(external / "logs"), "logger created logs through a symlinked log parent");
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

    void TestRejectsRootDerivedSymlinkAncestor()
    {
        ResetEnv();
        const fs::path root = MakeTempRoot("obelisk_logger_root_symlink_ancestor");
        const fs::path external = root / "external-parent";
        fs::create_directories(external);
        fs::create_symlink(external, root / "root-parent-link");
        setenv("OBELISK_ROOT", (root / "root-parent-link" / "obelisk").string().c_str(), 1);

        ExpectInitThrowsContaining("symlink");
        Require(!fs::exists(external / "obelisk" / "logs"),
                "logger created root-derived logs through a symlinked root parent");
        fs::remove_all(root);
    }

    void TestRejectsRootDerivedLogDirWithParentAlias()
    {
        ResetEnv();
        const fs::path root = MakeTempRoot("obelisk_logger_root_parent_alias");
        setenv("OBELISK_ROOT", (root / "missing-root" / ".." / "obelisk").string().c_str(), 1);

        ExpectInitThrowsContaining("path alias");
        Require(!fs::exists(root / "missing-root"), "logger created a parent-alias root component");
        Require(!fs::exists(root / "obelisk" / "logs"), "logger created root-derived logs through a parent alias");
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
        TestRejectsMissingLogRoot();
        TestRejectsRelativeExplicitLogDir();
        TestRejectsRelativeRootDerivedLogDir();
        TestRejectsExplicitLogDirWithParentAlias();
        TestRejectsExplicitLogDirWithCurrentAlias();
        TestRejectsSymlinkExplicitLogDir();
        TestRejectsSymlinkExplicitLogDirAncestor();
        TestRejectsSymlinkInstanceLogDir();
        TestRejectsRootDerivedSymlinkAncestor();
        TestRejectsRootDerivedLogDirWithParentAlias();
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

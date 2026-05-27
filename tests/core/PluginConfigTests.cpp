#include "core/PluginConfig.h"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <sstream>
#include <string>

namespace fs = std::filesystem;

namespace
{
    constexpr const char* kSafeDefaultConfig =
        R"({"enabled":false,"instance_allowlist":["arkserver"]})";

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    ObeliskPluginMetadata Metadata(const char* pluginId = "test_plugin",
                                   const char* configFile = "config.json",
                                   const char* defaultConfig = kSafeDefaultConfig)
    {
        return ObeliskPluginMetadata{
            OBELISK_PLUGIN_METADATA_ABI_VERSION,
            sizeof(ObeliskPluginMetadata),
            pluginId,
            "Test Plugin",
            "1.0.0",
            configFile,
            defaultConfig,
        };
    }

    fs::path MakeTempRoot()
    {
        const auto now = std::chrono::steady_clock::now().time_since_epoch().count();
        fs::path root = fs::temp_directory_path() / ("obelisk_plugin_config_tests_" + std::to_string(now));
        fs::create_directories(root);
        return root;
    }

    void WriteFile(const fs::path& path, const std::string& contents)
    {
        fs::create_directories(path.parent_path());
        std::ofstream out(path);
        Require(out.is_open(), "failed to open file for writing");
        out << contents;
        out.close();
        Require(static_cast<bool>(out), "failed to write file");
    }

    std::string ReadFile(const fs::path& path)
    {
        std::ifstream in(path);
        Require(in.is_open(), "failed to open file for reading");
        std::ostringstream buffer;
        buffer << in.rdbuf();
        return buffer.str();
    }

    bool Prepare(const ObeliskPluginMetadata& metadata,
                 const fs::path& configRoot,
                 Obelisk::Core::PreparedPluginConfig& prepared,
                 std::string& error)
    {
        error.clear();
        prepared = {};
        return Obelisk::Core::PreparePluginConfig(metadata, configRoot, prepared, error);
    }

    void TestCreatesSafeDisabledDefault(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        Require(Prepare(Metadata(), root, prepared, error), "safe default config was rejected");
        Require(error.empty(), "successful prepare returned an error");
        Require(prepared.directory == root / "test_plugin", "prepared directory mismatch");
        Require(prepared.path == root / "test_plugin" / "config.json", "prepared path mismatch");
        Require(fs::exists(prepared.path), "default config was not created");

        const std::string created = ReadFile(prepared.path);
        Require(created.find("\"enabled\": false") != std::string::npos,
                "created default config is not safe-disabled");
        Require(created.find("\"instance_allowlist\"") != std::string::npos,
                "created default config is missing instance_allowlist");
    }

    void TestRejectsUnsafePluginId(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        Require(!Prepare(Metadata("../escape"), root, prepared, error), "unsafe plugin_id was accepted");
        Require(error.find("plugin_id") != std::string::npos, "unsafe plugin_id error was unclear");
        Require(!fs::exists(root / ".." / "escape" / "config.json"), "unsafe plugin_id wrote outside root");
    }

    void TestRejectsNonConfigJsonFile(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        Require(!Prepare(Metadata("bad_config_file", "settings.json"), root, prepared, error),
                "non-config.json file was accepted");
        Require(error.find("config.json") != std::string::npos, "non-config.json error was unclear");
        Require(!fs::exists(root / "bad_config_file"), "non-config.json case created a directory");
    }

    void TestRejectsEnabledDefaultConfig(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        Require(!Prepare(Metadata("enabled_default", "config.json", R"({"enabled":true})"), root, prepared, error),
                "enabled default config was accepted");
        Require(error.find("enabled=false") != std::string::npos, "enabled default error was unclear");
        Require(!fs::exists(root / "enabled_default"), "enabled default case created a directory");
    }

    void TestRejectsCorruptDefaultJson(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        Require(!Prepare(Metadata("corrupt_default", "config.json", "{ \"enabled\": false,"), root, prepared, error),
                "corrupt default JSON was accepted");
        Require(error.find("parse failed") != std::string::npos, "corrupt default JSON error was unclear");
        Require(!fs::exists(root / "corrupt_default"), "corrupt default JSON case created a directory");
    }

    void TestRejectsMistypedDefaultAllowlist(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        Require(!Prepare(Metadata("bad_default_allowlist",
                                  "config.json",
                                  R"({"enabled":false,"instance_allowlist":"arkserver"})"),
                         root,
                         prepared,
                         error),
                "mistyped default instance_allowlist was accepted");
        Require(error.find("instance_allowlist") != std::string::npos,
                "mistyped default instance_allowlist error was unclear");
        Require(!fs::exists(root / "bad_default_allowlist"),
                "mistyped default instance_allowlist case created a directory");
    }

    void TestAcceptsExistingValidConfigWithoutOverwrite(const fs::path& root)
    {
        const fs::path configPath = root / "existing_valid" / "config.json";
        const std::string original = "{\n  \"enabled\": true,\n  \"instance_allowlist\": [\"arkserver\"]\n}\n";
        WriteFile(configPath, original);

        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        Require(Prepare(Metadata("existing_valid"), root, prepared, error), "existing valid config was rejected");
        Require(error.empty(), "existing valid config returned an error");
        Require(prepared.path == configPath, "existing valid config path mismatch");
        Require(ReadFile(configPath) == original, "existing valid config was overwritten");
    }

    void TestRejectsCorruptExistingJson(const fs::path& root)
    {
        WriteFile(root / "corrupt_existing" / "config.json", "{ \"enabled\": false,");

        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        Require(!Prepare(Metadata("corrupt_existing"), root, prepared, error), "corrupt existing JSON was accepted");
        Require(error.find("parse failed") != std::string::npos, "corrupt JSON error was unclear");
    }

    void TestRejectsMistypedExistingAllowlist(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        WriteFile(root / "allowlist_not_array" / "config.json",
                  R"({"enabled":false,"instance_allowlist":"arkserver"})");
        Require(!Prepare(Metadata("allowlist_not_array"), root, prepared, error),
                "non-array instance_allowlist was accepted");
        Require(error.find("instance_allowlist") != std::string::npos, "non-array allowlist error was unclear");

        WriteFile(root / "allowlist_entry_not_string" / "config.json",
                  R"({"enabled":false,"instance_allowlist":[42]})");
        Require(!Prepare(Metadata("allowlist_entry_not_string"), root, prepared, error),
                "non-string instance_allowlist entry was accepted");
        Require(error.find("instance_allowlist") != std::string::npos, "non-string allowlist error was unclear");
    }
}

int main()
{
    const fs::path root = MakeTempRoot();

    try
    {
        TestCreatesSafeDisabledDefault(root);
        TestRejectsUnsafePluginId(root);
        TestRejectsNonConfigJsonFile(root);
        TestRejectsEnabledDefaultConfig(root);
        TestRejectsCorruptDefaultJson(root);
        TestRejectsMistypedDefaultAllowlist(root);
        TestAcceptsExistingValidConfigWithoutOverwrite(root);
        TestRejectsCorruptExistingJson(root);
        TestRejectsMistypedExistingAllowlist(root);
        fs::remove_all(root);
    }
    catch (...)
    {
        std::cerr << "PluginConfigTests failed; temp root retained at " << root << '\n';
        throw;
    }

    std::cout << "PluginConfigTests passed\n";
    return 0;
}

#include "core/PluginConfig.h"

#include <atomic>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

namespace fs = std::filesystem;

namespace
{
    constexpr const char* kSafeDefaultConfig =
        R"({"enabled":false,"allow_all_instances":false,"instance_allowlist":["arkserver"]})";

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
        return Obelisk::Core::PreparePluginConfig(metadata, configRoot, "arkserver", prepared, error);
    }

    void TestCreatesSafeDisabledDefault(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        Require(Prepare(Metadata(), root, prepared, error), "safe default config was rejected");
        Require(error.empty(), "successful prepare returned an error");
        Require(prepared.directory == root / "test_plugin", "prepared directory mismatch");
        Require(prepared.path == root / "test_plugin" / "config.json", "prepared path mismatch");
        Require(!prepared.enabled, "safe default should be disabled");
        Require(prepared.instance_allowed, "safe default should allow configured instance");
        Require(fs::exists(prepared.path), "default config was not created");

        const std::string created = ReadFile(prepared.path);
        Require(created.find("\"enabled\": false") != std::string::npos,
                "created default config is not safe-disabled");
        Require(created.find("\"instance_allowlist\"") != std::string::npos,
                "created default config is missing instance_allowlist");
        Require(!fs::exists(prepared.path.string() + ".tmp"), "temporary config file survived successful write");
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

        Require(!Prepare(Metadata("enabled_default",
                                  "config.json",
                                  R"({"enabled":true,"allow_all_instances":false,"instance_allowlist":[]})"),
                         root,
                         prepared,
                         error),
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

    void TestRejectsDefaultWithoutExplicitInstanceEnvelope(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        Require(!Prepare(Metadata("missing_default_allowlist",
                                  "config.json",
                                  R"({"enabled":false,"allow_all_instances":false})"),
                         root,
                         prepared,
                         error),
                "default config without instance_allowlist was accepted");
        Require(error.find("instance_allowlist") != std::string::npos,
                "missing default instance_allowlist error was unclear");
        Require(!fs::exists(root / "missing_default_allowlist"),
                "missing default instance_allowlist case created a directory");

        Require(!Prepare(Metadata("missing_default_allow_all",
                                  "config.json",
                                  R"({"enabled":false,"instance_allowlist":[]})"),
                         root,
                         prepared,
                         error),
                "default config without allow_all_instances was accepted");
        Require(error.find("allow_all_instances") != std::string::npos,
                "missing default allow_all_instances error was unclear");
        Require(!fs::exists(root / "missing_default_allow_all"),
                "missing default allow_all_instances case created a directory");

        Require(!Prepare(Metadata("unsafe_default_allow_all",
                                  "config.json",
                                  R"({"enabled":false,"allow_all_instances":true,"instance_allowlist":[]})"),
                         root,
                         prepared,
                         error),
                "default config with allow_all_instances=true was accepted");
        Require(error.find("allow_all_instances=false") != std::string::npos,
                "unsafe default allow_all_instances error was unclear");
        Require(!fs::exists(root / "unsafe_default_allow_all"),
                "unsafe default allow_all_instances case created a directory");
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
        Require(prepared.enabled, "existing enabled config did not set prepared enabled");
        Require(prepared.instance_allowed, "existing allowlisted config did not allow instance");
        Require(ReadFile(configPath) == original, "existing valid config was overwritten");
    }

    void TestConcurrentDefaultCreation(const fs::path& root)
    {
        constexpr int kThreadCount = 8;
        std::atomic<int> successes{0};
        std::vector<std::thread> workers;
        workers.reserve(kThreadCount);

        for (int i = 0; i < kThreadCount; ++i)
        {
            workers.emplace_back([&]() {
                Obelisk::Core::PreparedPluginConfig prepared;
                std::string error;
                if (Prepare(Metadata("concurrent_default"), root, prepared, error))
                    successes.fetch_add(1, std::memory_order_relaxed);
            });
        }

        for (auto& worker : workers)
            worker.join();

        const fs::path configPath = root / "concurrent_default" / "config.json";
        Require(successes.load(std::memory_order_relaxed) == kThreadCount,
                "concurrent default config creation rejected a caller");
        Require(fs::exists(configPath), "concurrent default config was not created");
        Require(ReadFile(configPath).find("\"enabled\": false") != std::string::npos,
                "concurrent default config was not safe-disabled");

        for (const auto& entry : fs::directory_iterator(configPath.parent_path()))
        {
            Require(entry.path().filename().string().find("config.json.tmp.") != 0,
                    "temporary config file survived concurrent creation");
        }
    }

    void TestExistingConfigCanDisallowInstance(const fs::path& root)
    {
        WriteFile(root / "other_instance" / "config.json",
                  "{\n  \"enabled\": true,\n  \"instance_allowlist\": [\"arkserver2\"]\n}\n");

        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        Require(Prepare(Metadata("other_instance"), root, prepared, error),
                "existing config for another instance was rejected");
        Require(prepared.enabled, "enabled config for another instance did not set prepared enabled");
        Require(!prepared.instance_allowed, "non-matching instance_allowlist was allowed");
    }

    void TestEnabledConfigRequiresExplicitInstanceScope(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        WriteFile(root / "missing_allowlist" / "config.json", R"({"enabled":true})");
        Require(Prepare(Metadata("missing_allowlist"), root, prepared, error),
                "enabled config without instance scope was rejected instead of skipped");
        Require(prepared.enabled, "enabled config without instance scope did not set prepared enabled");
        Require(!prepared.instance_allowed, "enabled config without instance scope was allowed");

        WriteFile(root / "empty_allowlist" / "config.json",
                  R"({"enabled":true,"instance_allowlist":[]})");
        Require(Prepare(Metadata("empty_allowlist"), root, prepared, error),
                "enabled config with empty instance_allowlist was rejected instead of skipped");
        Require(prepared.enabled, "enabled config with empty allowlist did not set prepared enabled");
        Require(!prepared.instance_allowed, "enabled config with empty instance_allowlist was allowed");
    }

    void TestAllowAllInstancesIsExplicitOptIn(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        WriteFile(root / "allow_all_instances" / "config.json",
                  R"({"enabled":true,"allow_all_instances":true,"instance_allowlist":[]})");
        Require(Prepare(Metadata("allow_all_instances"), root, prepared, error),
                "allow_all_instances config was rejected");
        Require(prepared.enabled, "allow_all_instances config did not set prepared enabled");
        Require(prepared.instance_allowed, "allow_all_instances did not allow the instance");

        WriteFile(root / "bad_allow_all_instances" / "config.json",
                  R"({"enabled":true,"allow_all_instances":"yes","instance_allowlist":["arkserver"]})");
        Require(!Prepare(Metadata("bad_allow_all_instances"), root, prepared, error),
                "non-boolean allow_all_instances was accepted");
        Require(error.find("allow_all_instances") != std::string::npos,
                "allow_all_instances error was unclear");
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

        WriteFile(root / "allowlist_entry_empty" / "config.json",
                  R"({"enabled":false,"instance_allowlist":[""]})");
        Require(!Prepare(Metadata("allowlist_entry_empty"), root, prepared, error),
                "empty instance_allowlist entry was accepted");
        Require(error.find("safe instance ids") != std::string::npos,
                "empty instance_allowlist error was unclear");

        WriteFile(root / "allowlist_entry_path" / "config.json",
                  R"({"enabled":false,"instance_allowlist":["../arkserver"]})");
        Require(!Prepare(Metadata("allowlist_entry_path"), root, prepared, error),
                "unsafe instance_allowlist entry was accepted");
        Require(error.find("safe instance ids") != std::string::npos,
                "unsafe instance_allowlist error was unclear");
    }

    void TestRejectsConfigSymlinkEscape(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        const fs::path external = root / "external-config.json";
        WriteFile(external, R"({"enabled":true,"allow_all_instances":true})");
        fs::create_directories(root / "config_symlink");
        fs::create_symlink(external, root / "config_symlink" / "config.json");

        Require(!Prepare(Metadata("config_symlink"), root, prepared, error),
                "symlink config file was accepted");
        Require(error.find("symlink") != std::string::npos, "symlink config file error was unclear");
    }

    void TestRejectsConfigDirectorySymlinkEscape(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        const fs::path externalDir = root / "external-config-dir";
        WriteFile(externalDir / "config.json", R"({"enabled":true,"allow_all_instances":true})");
        fs::create_symlink(externalDir, root / "directory_symlink");

        Require(!Prepare(Metadata("directory_symlink"), root, prepared, error),
                "symlink config directory was accepted");
        Require(error.find("symlink") != std::string::npos, "symlink config directory error was unclear");
    }

    void TestRejectsNonRegularConfigFile(const fs::path& root)
    {
        Obelisk::Core::PreparedPluginConfig prepared;
        std::string error;

        fs::create_directories(root / "directory_config" / "config.json");

        Require(!Prepare(Metadata("directory_config"), root, prepared, error),
                "directory config file was accepted");
        Require(error.find("regular file") != std::string::npos, "non-regular config error was unclear");
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
        TestRejectsDefaultWithoutExplicitInstanceEnvelope(root);
        TestAcceptsExistingValidConfigWithoutOverwrite(root);
        TestConcurrentDefaultCreation(root);
        TestExistingConfigCanDisallowInstance(root);
        TestEnabledConfigRequiresExplicitInstanceScope(root);
        TestAllowAllInstancesIsExplicitOptIn(root);
        TestRejectsCorruptExistingJson(root);
        TestRejectsMistypedExistingAllowlist(root);
        TestRejectsConfigSymlinkEscape(root);
        TestRejectsConfigDirectorySymlinkEscape(root);
        TestRejectsNonRegularConfigFile(root);
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

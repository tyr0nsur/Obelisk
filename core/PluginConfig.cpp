#include "PluginConfig.h"

#include "extern/nlohmann/json.hpp"

#include <atomic>
#include <cctype>
#include <cstring>
#include <fstream>
#include <string>
#include <system_error>
#include <unistd.h>

namespace fs = std::filesystem;
using json = nlohmann::json;

namespace Obelisk::Core
{
    namespace
    {
        bool IsSafePluginId(const char* value)
        {
            if (!value || value[0] == '\0')
                return false;

            const std::string token(value);
            for (const unsigned char ch : token)
            {
                if (std::isalnum(ch) || ch == '_' || ch == '-')
                    continue;
                return false;
            }

            return true;
        }

        bool IsSafeToken(const std::string& token)
        {
            if (token.empty())
                return false;

            for (const unsigned char ch : token)
            {
                if (std::isalnum(ch) || ch == '_' || ch == '-')
                    continue;
                return false;
            }

            return true;
        }

        bool IsSafeConfigFile(const char* value)
        {
            return value && std::strcmp(value, "config.json") == 0;
        }

        bool IsSafeDisabledConfig(const json& config, std::string& error)
        {
            if (!config.is_object())
            {
                error = "config root must be a JSON object";
                return false;
            }

            const auto enabled = config.find("enabled");
            if (enabled == config.end() || !enabled->is_boolean())
            {
                error = "config must include boolean field 'enabled'";
                return false;
            }

            if (enabled->get<bool>())
            {
                error = "default config must be safe-disabled with enabled=false";
                return false;
            }

            const auto allowlist = config.find("instance_allowlist");
            if (allowlist == config.end())
            {
                error = "default config must include array field 'instance_allowlist'";
                return false;
            }

            if (!allowlist->is_array())
            {
                error = "instance_allowlist must be an array";
                return false;
            }

            for (const auto& entry : *allowlist)
            {
                if (!entry.is_string())
                {
                    error = "instance_allowlist entries must be strings";
                    return false;
                }

                if (!IsSafeToken(entry.get<std::string>()))
                {
                    error = "instance_allowlist entries must be non-empty safe instance ids";
                    return false;
                }
            }

            const auto allowAllInstances = config.find("allow_all_instances");
            if (allowAllInstances == config.end())
            {
                error = "default config must include boolean field 'allow_all_instances'";
                return false;
            }

            if (!allowAllInstances->is_boolean())
            {
                error = "allow_all_instances must be a boolean";
                return false;
            }

            if (allowAllInstances->get<bool>())
            {
                error = "default config must set allow_all_instances=false";
                return false;
            }

            return true;
        }

        bool LoadJsonFile(const fs::path& path, json& out, std::string& error)
        {
            std::ifstream in(path);
            if (!in.is_open())
            {
                error = "config file is not readable";
                return false;
            }

            try
            {
                out = json::parse(in);
            }
            catch (const std::exception& e)
            {
                error = std::string("config JSON parse failed: ") + e.what();
                return false;
            }

            return true;
        }

        bool ValidateExistingConfigPath(const fs::path& directory, const fs::path& path, std::string& error)
        {
            std::error_code ec;
            const fs::file_status directorySymlinkStatus = fs::symlink_status(directory, ec);
            if (ec)
            {
                error = "plugin config directory is not accessible: " + ec.message();
                return false;
            }

            if (fs::is_symlink(directorySymlinkStatus))
            {
                error = "plugin config directory must not be a symlink";
                return false;
            }

            if (!fs::is_directory(directorySymlinkStatus))
            {
                error = "plugin config directory must be a directory";
                return false;
            }

            const fs::file_status configSymlinkStatus = fs::symlink_status(path, ec);
            if (ec)
            {
                error = "plugin config file is not accessible: " + ec.message();
                return false;
            }

            if (fs::is_symlink(configSymlinkStatus))
            {
                error = "plugin config file must not be a symlink";
                return false;
            }

            const fs::file_status configStatus = fs::status(path, ec);
            if (ec)
            {
                error = "plugin config file status failed: " + ec.message();
                return false;
            }

            if (!fs::is_regular_file(configStatus))
            {
                error = "plugin config file must be a regular file";
                return false;
            }

            return true;
        }

        bool ValidateConfigDirectoryForWrite(const fs::path& directory,
                                             const char* label,
                                             bool allowMissing,
                                             std::string& error)
        {
            std::error_code ec;
            const fs::file_status directorySymlinkStatus = fs::symlink_status(directory, ec);
            if (directorySymlinkStatus.type() == fs::file_type::not_found)
            {
                if (allowMissing)
                    return true;
                error = std::string(label) + " must exist";
                return false;
            }
            if (ec)
            {
                error = std::string(label) + " is not accessible: " + ec.message();
                return false;
            }

            if (fs::is_symlink(directorySymlinkStatus))
            {
                error = std::string(label) + " must not be a symlink";
                return false;
            }

            if (fs::exists(directorySymlinkStatus))
            {
                if (!fs::is_directory(directorySymlinkStatus))
                {
                    error = std::string(label) + " must be a directory";
                    return false;
                }
                return true;
            }

            if (!allowMissing)
            {
                error = std::string(label) + " must exist";
                return false;
            }

            return true;
        }

        bool InstanceAllowed(const json& config, const std::string& instanceId, bool enabled)
        {
            if (!enabled)
                return true;

            const auto allowAllInstances = config.find("allow_all_instances");
            if (allowAllInstances != config.end() && allowAllInstances->is_boolean() &&
                allowAllInstances->get<bool>())
                return true;

            const auto allowlist = config.find("instance_allowlist");
            if (allowlist == config.end() || allowlist->empty())
                return false;

            for (const auto& entry : *allowlist)
            {
                if (entry.is_string() && entry.get<std::string>() == instanceId)
                    return true;
            }

            return false;
        }

        fs::path MakeUniqueTempConfigPath(const fs::path& path)
        {
            static std::atomic<uint64_t> counter{0};
            const uint64_t id = counter.fetch_add(1, std::memory_order_relaxed);
            return path.string() + ".tmp." + std::to_string(static_cast<long long>(getpid())) +
                "." + std::to_string(id);
        }

        bool WriteDefaultConfigAtomically(const fs::path& path, const json& config, std::string& error)
        {
            const fs::path tempPath = MakeUniqueTempConfigPath(path);
            std::ofstream out(tempPath, std::ios::trunc);
            if (!out.is_open())
            {
                error = "failed to create default plugin config";
                return false;
            }

            out << config.dump(4) << '\n';
            out.close();
            if (!out)
            {
                error = "failed to write default plugin config";
                std::error_code removeEc;
                fs::remove(tempPath, removeEc);
                return false;
            }

            std::error_code ec;
            fs::create_hard_link(tempPath, path, ec);
            if (ec)
            {
                std::error_code removeEc;
                fs::remove(tempPath, removeEc);
                if (fs::exists(path))
                    return true;

                error = "failed to install default plugin config: " + ec.message();
                return false;
            }

            std::error_code removeEc;
            fs::remove(tempPath, removeEc);
            return true;
        }
    }

    bool PreparePluginConfig(const ObeliskPluginMetadata& metadata,
                             const fs::path& configRoot,
                             const std::string& instanceId,
                             PreparedPluginConfig& prepared,
                             std::string& error)
    {
        if (metadata.abi_version != OBELISK_PLUGIN_METADATA_ABI_VERSION ||
            metadata.struct_size < sizeof(ObeliskPluginMetadata))
        {
            error = "unsupported plugin metadata ABI";
            return false;
        }

        if (!IsSafePluginId(metadata.plugin_id))
        {
            error = "plugin_id is empty or contains unsafe path characters";
            return false;
        }

        if (!metadata.name || metadata.name[0] == '\0')
        {
            error = "plugin name is empty";
            return false;
        }

        if (!metadata.version || metadata.version[0] == '\0')
        {
            error = "plugin version is empty";
            return false;
        }

        if (!IsSafeConfigFile(metadata.config_file))
        {
            error = "config_file must be config.json";
            return false;
        }

        if (!metadata.default_config_json || metadata.default_config_json[0] == '\0')
        {
            error = "default_config_json is empty";
            return false;
        }

        json defaultConfig;
        try
        {
            defaultConfig = json::parse(metadata.default_config_json);
        }
        catch (const std::exception& e)
        {
            error = std::string("default_config_json parse failed: ") + e.what();
            return false;
        }

        if (!IsSafeDisabledConfig(defaultConfig, error))
            return false;

        prepared.directory = configRoot / metadata.plugin_id;
        prepared.path = prepared.directory / metadata.config_file;

        std::error_code ec;
        if (!fs::exists(prepared.path, ec))
        {
            if (!ValidateConfigDirectoryForWrite(configRoot, "plugin config root", true, error))
                return false;
            if (!ValidateConfigDirectoryForWrite(prepared.directory, "plugin config directory", true, error))
                return false;

            fs::create_directories(prepared.directory, ec);
            if (ec)
            {
                error = "failed to create plugin config directory: " + ec.message();
                return false;
            }

            if (!ValidateConfigDirectoryForWrite(prepared.directory, "plugin config directory", false, error))
                return false;

            if (!WriteDefaultConfigAtomically(prepared.path, defaultConfig, error))
                return false;
        }

        if (!ValidateExistingConfigPath(prepared.directory, prepared.path, error))
            return false;

        json existingConfig;
        if (!LoadJsonFile(prepared.path, existingConfig, error))
            return false;

        if (!existingConfig.is_object())
        {
            error = "config root must be a JSON object";
            return false;
        }

        const auto enabled = existingConfig.find("enabled");
        if (enabled == existingConfig.end() || !enabled->is_boolean())
        {
            error = "config must include boolean field 'enabled'";
            return false;
        }

        const auto allowlist = existingConfig.find("instance_allowlist");
        if (allowlist != existingConfig.end() && !allowlist->is_array())
        {
            error = "instance_allowlist must be an array";
            return false;
        }

        if (allowlist != existingConfig.end())
        {
            for (const auto& entry : *allowlist)
            {
                if (!entry.is_string())
                {
                    error = "instance_allowlist entries must be strings";
                    return false;
                }

                if (!IsSafeInstanceId(entry.get<std::string>()))
                {
                    error = "instance_allowlist entries must be non-empty safe instance ids";
                    return false;
                }
            }
        }

        const auto allowAllInstances = existingConfig.find("allow_all_instances");
        if (allowAllInstances != existingConfig.end() && !allowAllInstances->is_boolean())
        {
            error = "allow_all_instances must be a boolean";
            return false;
        }

        prepared.enabled = enabled->get<bool>();
        prepared.instance_allowed = InstanceAllowed(existingConfig, instanceId, prepared.enabled);

        return true;
    }

    bool IsSafeInstanceId(const std::string& value)
    {
        return IsSafeToken(value);
    }
}

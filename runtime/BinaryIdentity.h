#pragma once

#include <optional>
#include <string>
#include <string_view>

namespace Obelisk::Runtime
{
    // Read the actual file. Environment variables never select a binary profile.
    std::optional<std::string> Sha256File(const char* path) noexcept;
    bool CurrentExecutableMatches(std::string_view expectedSha256) noexcept;
}

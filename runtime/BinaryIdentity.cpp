#include "BinaryIdentity.h"

#include <array>
#include <fstream>
#include <memory>
#include <openssl/evp.h>

namespace Obelisk::Runtime
{
    std::optional<std::string> Sha256File(const char* path) noexcept
    {
        try
        {
            if (!path)
                return std::nullopt;
            std::ifstream file(path, std::ios::binary);
            if (!file)
                return std::nullopt;
            std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)> context(
                EVP_MD_CTX_new(), EVP_MD_CTX_free);
            if (!context || EVP_DigestInit_ex(context.get(), EVP_sha256(), nullptr) != 1)
                return std::nullopt;
            std::array<char, 64 * 1024> buffer;
            while (file)
            {
                file.read(buffer.data(), buffer.size());
                const auto count = file.gcount();
                if (count > 0 && EVP_DigestUpdate(context.get(), buffer.data(), count) != 1)
                    return std::nullopt;
            }
            if (!file.eof())
                return std::nullopt;
            std::array<unsigned char, EVP_MAX_MD_SIZE> digest{};
            unsigned int length = 0;
            if (EVP_DigestFinal_ex(context.get(), digest.data(), &length) != 1 || length != 32)
                return std::nullopt;
            constexpr char hex[] = "0123456789abcdef";
            std::string result;
            result.reserve(64);
            for (unsigned int i = 0; i < length; ++i)
            {
                result.push_back(hex[digest[i] >> 4]);
                result.push_back(hex[digest[i] & 15]);
            }
            return result;
        }
        catch (...)
        {
            return std::nullopt;
        }
    }

    bool CurrentExecutableMatches(std::string_view expectedSha256) noexcept
    {
        const auto actual = Sha256File("/proc/self/exe");
        return actual && *actual == expectedSha256;
    }
}

#include "ue/NativeChatText.h"
#include <iostream>
#include <sys/mman.h>
#include <unistd.h>

int main()
{
    using namespace Obelisk::UE::NativeChatText;
    const std::string input = "ping \xc3\xb1 \xf0\x9f\xa4\x96";
    std::vector<char32_t> owned;
    if (!Encode(input, owned) || owned.back() != U'\0')
        return 1;
    FString value{owned.data(), static_cast<int32_t>(owned.size()), static_cast<int32_t>(owned.size())};
    std::string decoded;
    if (!Decode(&value, decoded) || decoded != input)
        return 2;
    if (Encode(std::string("\xc0\xaf", 2), owned) ||
        Encode(std::string("\xed\xa0\x80", 3), owned) ||
        Encode(std::string("\xf4\x90\x80\x80", 4), owned) ||
        Encode(std::string("x\0y", 3), owned))
        return 3;
    const char32_t invalid[] = {0xd800, U'\0'};
    value = FString{invalid, 2, 2};
    if (Decode(&value, decoded))
        return 4;
    value = FString{invalid, 2, 1};
    if (Decode(&value, decoded))
        return 5;
    value = FString{invalid, 3000, 3000};
    if (Decode(&value, decoded) || Decode(nullptr, decoded))
        return 6;
    const long pageSize = sysconf(_SC_PAGESIZE);
    void* page = mmap(nullptr, pageSize, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (page == MAP_FAILED)
        return 7;
    auto* text = static_cast<char32_t*>(page);
    text[0] = U'p'; text[1] = U'\0';
    value = FString{text, 2, 2};
    if (!Decode(&value, decoded) || decoded != "p")
        return 8;
    if (mprotect(page, pageSize, PROT_NONE) || Decode(&value, decoded))
        return 9;
    munmap(page, pageSize);
    if (Decode(&value, decoded))
        return 10;
    std::cout << "Linux UTF-32 FString roundtrip, malformed text and inaccessible memory checks passed.\n";
}

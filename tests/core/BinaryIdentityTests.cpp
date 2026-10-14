#include "runtime/BinaryIdentity.h"
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <unistd.h>

int main()
{
    namespace fs = std::filesystem;
    const auto path = fs::temp_directory_path() / ("obelisk-sha-" + std::to_string(getpid()));
    { std::ofstream file(path); file << "abc"; }
    const auto hash = Obelisk::Runtime::Sha256File(path.c_str());
    fs::remove(path);
    if (!hash || *hash != "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        return 1;
    if (Obelisk::Runtime::Sha256File(path.c_str()) ||
        Obelisk::Runtime::Sha256File(nullptr))
        return 2;
    const auto current = Obelisk::Runtime::Sha256File("/proc/self/exe");
    if (!current || !Obelisk::Runtime::CurrentExecutableMatches(*current) ||
        Obelisk::Runtime::CurrentExecutableMatches(std::string(64, '0')))
        return 3;
    std::cout << "Binary identity is verified against file bytes, including this executable.\n";
}

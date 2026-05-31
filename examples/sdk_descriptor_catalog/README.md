# Descriptor Catalog SDK Plugin

This creator-facing example builds outside the Obelisk source tree and uses only the
installed SDK package:

Support tier: release-supported seed.

- `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)`
- `Obelisk::obelisk_sdk`
- `OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS`
- `OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS`
- `DescribeResourceKind`
- `DescribeGameplayPolicyEventKind`

It demonstrates metadata-only descriptor discovery for the current release-supported SDK
seed. Resource descriptors are category data only. They are not identity, lookup handles,
persistent IDs, mutable resources, or proof that two events refer to the same object.
Gameplay policy event descriptors are discovery data only. They do not expose raw UE
state, return override authority, mutation, or object lookup.

The example does not use private headers, raw UE pointers, `ProcessEvent`, gameplay
module APIs, identity, lookup, mutation, return overrides, chat replies/send-chat, ArkApi
compatibility, Windows/MSVC portability, or implementation patterns from other
frameworks.

The `find_package` version is a compatibility floor for the current pre-release SDK line,
not a complete SDK claim and not a claim that a stable `v0.1.0` release tag exists.
This example is a foundation/contributor-readiness sample, not ArkApi portability
guidance and not Obelisk SDK v1 evidence.

## Build

Install Obelisk into a test root first, then point CMake at that install:

```bash
cmake -S examples/sdk_descriptor_catalog -B /tmp/obelisk-sdk-descriptor-catalog-build \
  -DCMAKE_PREFIX_PATH=/path/to/obelisk-install-root
cmake --build /tmp/obelisk-sdk-descriptor-catalog-build -j"$(nproc)"
```

The output is `obelisk_sdk_descriptor_catalog.so`. Publish plugins with
`scripts/install_obelisk_plugin.sh`; do not copy a partially built `.so` into a shared
runtime `plugins/` directory.

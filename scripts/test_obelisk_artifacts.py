#!/usr/bin/env python3
"""Packaging/crypto safety tests, using real OpenSSL and a compiled ELF fixture.

These tests do not start ARK or accept any gameplay capability.
"""

import gzip
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import tarfile
import unittest
from unittest import mock

import obelisk_artifacts as artifacts


class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("openssl") is None or shutil.which("cc") is None:
            raise RuntimeError("Artifact tests require real openssl and a C compiler")
        cls.shared = tempfile.TemporaryDirectory(prefix="obelisk-artifact-fixture-")
        cls.shared_root = Path(cls.shared.name)
        library = cls.shared_root / "fixture.so"
        subprocess.run(["cc", "-shared", "-fPIC", "-x", "c", "-", "-o", library], input=b"int artifact_fixture(void) { return 1; }\n", check=True, capture_output=True)
        cls.elf = library.read_bytes()
        cls.private = cls.shared_root / "private.pem"
        cls.public = cls.shared_root / "public.pem"
        artifacts.keygen(cls.private, cls.public)
        cls.other_private = cls.shared_root / "other-private.pem"
        cls.other_public = cls.shared_root / "other-public.pem"
        artifacts.keygen(cls.other_private, cls.other_public)

    @classmethod
    def tearDownClass(cls):
        cls.shared.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="obelisk-artifact-test-")
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.build = self.root / "build"
        self.output = self.root / "output"
        self.stage_root = self.root / "stage"
        for directory in (self.source, self.build, self.output, self.stage_root):
            directory.mkdir(mode=0o700)
        self.put(self.build / "libobelisk.so", self.elf)
        self.put(self.build / "_deps/subhook-build/libsubhook.so", self.elf)
        for plugin in artifacts.PLUGINS:
            self.put(self.build / f"plugins/{plugin}/{plugin}.so", self.elf)
        for header in artifacts.HEADERS:
            self.put(self.source / f"include/obelisk/{header}", b"/* packaging fixture; no gameplay API assertion */\n")
        self.put(self.build / "ObeliskConfig.cmake", b"# packaging fixture\n")
        self.put(self.build / "ObeliskConfigVersion.cmake", b"# packaging fixture\n")
        self.put(self.build / "CMakeFiles/Export/fixture/ObeliskTargets.cmake", b"# packaging fixture\n")
        for path in (self.source / "LICENSE", self.build / "_deps/fmt-src/LICENSE.rst", self.build / "_deps/spdlog-src/LICENSE"):
            self.put(path, b"Test fixture copyright notice.\n")
        self.put(self.build / "_deps/subhook-src/subhook.h", b"/* Copyright test fixture\n * Redistribution permitted. DISCLAIMER.\n */\nint not_distributed;\n")

    def tearDown(self):
        artifacts.remove_temporary(self.root)
        self.temp.cleanup()

    @staticmethod
    def put(path, data):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(data)

    def build_entry(self, version="0.1.0-beta.1", channel="experimental"):
        return artifacts.build_artifact(self.build, self.source, version, channel, self.output, self.private)

    def paths(self, entry):
        return {"archive": self.output / entry["archive_name"], "manifest": self.output / entry["manifest_name"], "signature": self.output / entry["signature_name"], "trusted_key": self.public}

    def signed_archive(self, entry, archive):
        value = json.loads((self.output / entry["manifest_name"]).read_bytes())
        value["archive_sha256"] = artifacts.digest(archive)
        value["archive_size"] = len(archive)
        data = artifacts.canonical(value)
        sig = artifacts.sign_manifest(data, artifacts.read_regular(self.private, private=True))
        paths = {"archive": self.root / "candidate.tar.gz", "manifest": self.root / "candidate.json", "signature": self.root / "candidate.sig", "trusted_key": self.public}
        for key, content in (("archive", archive), ("manifest", data), ("signature", sig)):
            self.put(paths[key], content)
        return paths

    def tar_entries(self, entries):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name, content, kind in entries:
                member = tarfile.TarInfo(name)
                member.type = kind
                member.mode = 0o644
                member.size = len(content) if kind == tarfile.REGTYPE else 0
                if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                    member.linkname = "../../escape"
                archive.addfile(member, io.BytesIO(content) if kind == tarfile.REGTYPE else None)
        return gzip.compress(buffer.getvalue(), mtime=0)

    def test_real_signature_round_trip_and_deterministic_replay(self):
        entry = self.build_entry()
        value, manifest, signature, payload = artifacts.verify(**self.paths(entry))
        self.assertEqual(value["runtime_ready"], False)
        self.assertEqual(set(payload), artifacts.EXPECTED_PATHS)
        self.assertEqual(len(signature), 64)
        self.assertEqual(entry["id"], artifacts.digest(manifest))
        self.assertEqual(entry, self.build_entry())
        index = json.loads((self.output / "index.json").read_bytes())
        self.assertEqual(index["artifacts"], [entry])
        self.assertNotIn(b"not_distributed", payload["licenses/subhook.txt"])

    def test_index_has_only_names_and_unaccepted_metadata(self):
        entry = self.build_entry()
        for name in ("archive_name", "manifest_name", "signature_name"):
            self.assertEqual(Path(entry[name]).name, entry[name])
        self.assertEqual(entry["components"], list(artifacts.PLUGINS))
        self.assertFalse(entry["runtime_ready"])
        self.assertEqual(entry["stability"], "experimental")
        self.assertNotIn(str(self.private), (self.output / "index.json").read_text())

    def test_wrong_external_key_is_refused(self):
        paths = self.paths(self.build_entry())
        paths["trusted_key"] = self.other_public
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.verify(**paths)

    def test_payload_archive_manifest_and_signature_tampering_are_refused(self):
        entry = self.build_entry()
        paths = self.paths(entry)
        for name in ("archive", "manifest", "signature"):
            with self.subTest(name=name):
                target = self.root / f"changed-{name}"
                data = paths[name].read_bytes()
                self.put(target, data[:-1] + bytes([data[-1] ^ 1]))
                changed = dict(paths, **{name: target})
                with self.assertRaises(artifacts.ArtifactError):
                    artifacts.verify(**changed)

    def test_same_size_payload_tampering_with_signed_container_is_refused(self):
        entry = self.build_entry()
        payload = artifacts.collect_payload(self.build, self.source)
        name = "licenses/fmt.txt"
        payload[name] = b"X" + payload[name][1:]
        changed = artifacts.make_archive(payload)
        with self.assertRaisesRegex(artifacts.ArtifactError, "Payload digest"):
            artifacts.verify(**self.signed_archive(entry, changed))

    def test_tar_traversal_absolute_duplicates_unlisted_and_missing_are_refused(self):
        entry = self.build_entry()
        payload = artifacts.collect_payload(self.build, self.source)
        originals = [(path, data, tarfile.REGTYPE) for path, data in sorted(payload.items())]
        cases = [originals + [("../escape", b"bad", tarfile.REGTYPE)], originals + [("/tmp/escape", b"bad", tarfile.REGTYPE)], originals + [originals[0]], originals + [("config/secrets.json", b"{}", tarfile.REGTYPE)], originals[:-1]]
        for index, entries in enumerate(cases):
            with self.subTest(case=index):
                with self.assertRaises(artifacts.ArtifactError):
                    artifacts.verify(**self.signed_archive(entry, self.tar_entries(entries)))
        self.assertFalse((self.root.parent / "escape").exists())

    def test_tar_links_special_files_and_pax_are_refused(self):
        entry = self.build_entry()
        name = sorted(artifacts.EXPECTED_PATHS)[0]
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.DIRTYPE, tarfile.XHDTYPE, tarfile.GNUTYPE_LONGNAME):
            with self.subTest(kind=kind):
                archive = self.tar_entries([(name, b"", kind)])
                with self.assertRaises(artifacts.ArtifactError):
                    artifacts.verify(**self.signed_archive(entry, archive))

    def test_tar_oversized_declaration_and_data_after_end_are_refused(self):
        entry = self.build_entry()
        name = sorted(artifacts.EXPECTED_PATHS)[0]
        info = tarfile.TarInfo(name)
        info.size = artifacts.MAX_FILE + 1
        raw = info.tobuf(format=tarfile.USTAR_FORMAT) + bytes(1024)
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.verify(**self.signed_archive(entry, gzip.compress(raw)))
        payload = artifacts.collect_payload(self.build, self.source)
        good = gzip.decompress(artifacts.make_archive(payload))
        extra = self.tar_entries([(name, b"bad", tarfile.REGTYPE)])
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.verify(**self.signed_archive(entry, gzip.compress(good + gzip.decompress(extra))))

    def test_tar_standard_record_can_require_twenty_one_zero_blocks(self):
        payload = artifacts.collect_payload(self.build, self.source)
        for blocks in range(20):
            payload["licenses/fmt.txt"] = b"x" * (1 + 512 * blocks)
            logical_end = sum(512 + ((len(content) + 511) // 512) * 512 for content in payload.values())
            if logical_end % 10240 == 9728:
                break
        else:
            self.fail("Could not construct standard tar record boundary")
        archive = artifacts.make_archive(payload)
        manifest = artifacts.make_manifest("0.1.0", "experimental", payload, archive)
        self.assertEqual(artifacts.unpack_verified(archive, manifest), payload)
        oversized = gzip.compress(gzip.decompress(archive) + bytes(512))
        manifest["archive_sha256"] = artifacts.digest(oversized)
        manifest["archive_size"] = len(oversized)
        with self.assertRaisesRegex(artifacts.ArtifactError, "padding"):
            artifacts.unpack_verified(oversized, manifest)

    def test_limits_and_duplicate_json_keys_are_refused(self):
        entry = self.build_entry()
        original = (self.output / entry["manifest_name"]).read_bytes()
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.validate_manifest(original.replace(b'"api_bytes":312', b'"api_bytes":312,"api_bytes":312'))
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.validate_manifest(b" " * (artifacts.MAX_MANIFEST + 1))
        with mock.patch.object(artifacts, "MAX_ARCHIVE", 8):
            with self.assertRaises(artifacts.ArtifactError):
                artifacts.verify(**self.paths(entry))

    def test_runtime_ready_stable_or_extra_manifest_fields_are_refused(self):
        entry = self.build_entry()
        value = json.loads((self.output / entry["manifest_name"]).read_bytes())
        for key, replacement in (("runtime_ready", True), ("stability", "stable"), ("api_bytes", True), ("trusted_key", "attacker key")):
            with self.subTest(key=key):
                with self.assertRaises(artifacts.ArtifactError):
                    artifacts.validate_manifest(artifacts.canonical(dict(value, **{key: replacement})))

    def test_builder_allowlist_ignores_configs_and_game_binary(self):
        self.put(self.build / "config/server-password.json", b"fixture secret must not ship")
        self.put(self.source / "ShooterGameServer", b"not a redistributable fixture")
        payload = artifacts.collect_payload(self.build, self.source)
        self.assertEqual(set(payload), artifacts.EXPECTED_PATHS)
        self.assertFalse(any(b"fixture secret" in content for content in payload.values()))

    def test_builder_rejects_non_elf_and_missing_plugin(self):
        self.put(self.build / "libobelisk.so", b"not ELF")
        with self.assertRaises(artifacts.ArtifactError):
            self.build_entry()
        self.put(self.build / "libobelisk.so", self.elf)
        (self.build / "plugins/oPing/oPing.so").unlink()
        with self.assertRaises(artifacts.ArtifactError):
            self.build_entry()

    def test_semver_and_release_channel_boundary(self):
        for version in ("1.2", "01.2.3", "1.2.3-01", "../../escape", "1.2.3-", "1.2.3\n"):
            with self.subTest(version=version):
                with self.assertRaises(artifacts.ArtifactError):
                    artifacts.validate_version(version)
        with self.assertRaises(artifacts.ArtifactError):
            self.build_entry(channel="stable")
        artifacts.validate_version("1.2.3-beta.1+linux.4")

    def test_source_symlinks_ancestors_and_hardlinks_are_refused(self):
        target = self.build / "libobelisk.so"
        alias = self.root / "alias.so"
        os.link(target, alias)
        with self.assertRaises(artifacts.ArtifactError):
            self.build_entry()
        alias.unlink()
        alias.symlink_to(self.build, target_is_directory=True)
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.collect_payload(alias, self.source)
        alias.unlink()
        target.unlink()
        target.symlink_to(self.shared_root / "fixture.so")
        with self.assertRaises(artifacts.ArtifactError):
            self.build_entry()

    def test_keygen_modes_no_overwrite_and_private_key_permissions(self):
        private, public = self.root / "new-private.pem", self.root / "new-public.pem"
        artifacts.keygen(private, public)
        self.assertEqual(stat.S_IMODE(private.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(public.stat().st_mode), 0o600)
        previous = private.read_bytes()
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.keygen(private, public)
        self.assertEqual(private.read_bytes(), previous)
        private.chmod(0o644)
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.build_artifact(self.build, self.source, "0.1.0", "experimental", self.output, private)

    def test_stage_is_readonly_idempotent_and_never_activates(self):
        entry = self.build_entry()
        paths = self.paths(entry)
        first = artifacts.stage_artifact(**paths, stage_root=self.stage_root)
        self.assertFalse(first["activated"])
        destination = self.stage_root / "versions" / entry["id"]
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o500)
        self.assertEqual(stat.S_IMODE((destination / "runtime/libobelisk.so").stat().st_mode), 0o400)
        self.assertTrue(artifacts.stage_artifact(**paths, stage_root=self.stage_root)["replayed"])
        self.assertFalse((self.stage_root / "current").exists())
        self.assertEqual(sorted(path.name for path in self.stage_root.iterdir()), [".artifact-stage.lock", "versions"])

    def test_stage_replay_detects_changed_missing_and_extra_files(self):
        entry = self.build_entry()
        paths = self.paths(entry)
        artifacts.stage_artifact(**paths, stage_root=self.stage_root)
        destination = self.stage_root / "versions" / entry["id"]
        target = destination / "runtime/libobelisk.so"
        target.chmod(0o600)
        self.put(target, b"tampered")
        target.chmod(0o400)
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.stage_artifact(**paths, stage_root=self.stage_root)
        target.chmod(0o600)
        self.put(target, self.elf)
        target.chmod(0o400)
        parent = target.parent
        parent.chmod(0o700)
        target.unlink()
        parent.chmod(0o500)
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.stage_artifact(**paths, stage_root=self.stage_root)
        parent.chmod(0o700)
        self.put(target, self.elf)
        target.chmod(0o400)
        parent.chmod(0o500)
        destination.chmod(0o700)
        extra = destination / "extra"
        extra.mkdir(mode=0o500)
        destination.chmod(0o500)
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.stage_artifact(**paths, stage_root=self.stage_root)

    def test_unsafe_stage_roots_and_versions_symlinks_are_refused(self):
        entry = self.build_entry()
        paths = self.paths(entry)
        self.stage_root.chmod(0o755)
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.stage_artifact(**paths, stage_root=self.stage_root)
        self.stage_root.chmod(0o700)
        (self.stage_root / "versions").symlink_to(self.output, target_is_directory=True)
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.stage_artifact(**paths, stage_root=self.stage_root)

    def test_stage_signature_failure_creates_no_versions(self):
        paths = self.paths(self.build_entry())
        paths["trusted_key"] = self.other_public
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.stage_artifact(**paths, stage_root=self.stage_root)
        self.assertFalse((self.stage_root / "versions").exists())

    def test_untrusted_writable_ancestor_for_stage_or_key_is_refused(self):
        entry = self.build_entry()
        paths = self.paths(entry)
        writable = self.root / "writable-parent"
        writable.mkdir(mode=0o700)
        nested = writable / "stage"
        nested.mkdir(mode=0o700)
        copied_key = writable / "public.pem"
        self.put(copied_key, self.public.read_bytes())
        writable.chmod(0o777)
        with self.assertRaisesRegex(artifacts.ArtifactError, "ancestor"):
            artifacts.stage_artifact(**paths, stage_root=nested)
        paths["trusted_key"] = copied_key
        with self.assertRaisesRegex(artifacts.ArtifactError, "ancestor"):
            artifacts.verify(**paths)

    def test_stage_interrupted_write_removes_temporary_tree(self):
        entry = self.build_entry()
        paths = self.paths(entry)
        original = artifacts.write_new
        calls = 0

        def fail_write(path, data, mode=0o600):
            nonlocal calls
            if ".stage-" in str(path):
                calls += 1
                if calls == 3:
                    raise failure("injected interrupted write")
            return original(path, data, mode)

        for failure in (OSError, KeyboardInterrupt):
            calls = 0
            with self.subTest(failure=failure):
                with mock.patch.object(artifacts, "write_new", side_effect=fail_write):
                    with self.assertRaises(failure):
                        artifacts.stage_artifact(**paths, stage_root=self.stage_root)
                self.assertEqual(list((self.stage_root / "versions").iterdir()), [])

    def test_index_symlink_hardlink_and_conflicting_immutable_output_refused(self):
        target = self.output / "index.json"
        other = self.root / "other.json"
        self.put(other, b'{}')
        target.symlink_to(other)
        with self.assertRaises(artifacts.ArtifactError):
            self.build_entry()
        target.unlink()
        os.link(other, target)
        with self.assertRaises(artifacts.ArtifactError):
            self.build_entry()
        target.unlink()
        entry = self.build_entry()
        archive = self.output / entry["archive_name"]
        original_archive = archive.read_bytes()
        archive.chmod(0o600)
        self.put(archive, b"tampered")
        archive.chmod(0o400)
        with self.assertRaises(artifacts.ArtifactError):
            self.build_entry()
        archive.chmod(0o600)
        self.put(archive, original_archive)
        archive.chmod(0o400)
        original_fsync = artifacts.fsync_dir

        def fail_output_fsync(path):
            if path == self.output:
                raise OSError("injected directory fsync failure after index rename")
            return original_fsync(path)

        with mock.patch.object(artifacts, "fsync_dir", side_effect=fail_output_fsync):
            with self.assertRaises(OSError):
                self.build_entry(version="0.1.0-beta.2")
        index = json.loads((self.output / "index.json").read_bytes())
        added = next(item for item in index["artifacts"] if item["version"] == "0.1.0-beta.2")
        artifacts.verify(**self.paths(added))
        self.assertEqual(self.build_entry(version="0.1.0-beta.2"), added)

    def test_cli_requires_trusted_key_and_never_prints_private_key(self):
        script = Path(artifacts.__file__)
        entry = self.build_entry()
        paths = self.paths(entry)
        args = [sys_executable(), str(script), "verify"]
        for name in ("archive", "manifest", "signature"):
            args.extend(["--" + name, str(paths[name])])
        missing = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)
        valid = subprocess.run(args + ["--trusted-key", str(self.public)], capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertTrue(json.loads(valid.stdout)["verified"])
        self.assertNotIn("PRIVATE KEY", valid.stdout + valid.stderr)


def sys_executable():
    import sys
    return sys.executable


if __name__ == "__main__":
    unittest.main()

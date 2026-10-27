#!/usr/bin/env python3
"""Create, authenticate and stage experimental ObeliskNative artifacts.

Staging never changes a running server or a current-version pointer. This module
uses OpenSSL Ed25519 and an explicit, independently distributed verification key.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import zlib


PLUGINS = ("oAdvancedChat", "oEssentials", "oHomes", "oPing", "oShopKits", "oWorldTools")
HEADERS = ("ObeliskApi.h", "ObeliskChatSessionApi.h", "ObeliskCommandApi.h", "ObeliskPlayerLifecycleApi.h")
GAME_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
MAX_FILE = 128 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
MAX_ARCHIVE = 256 * 1024 * 1024
MAX_MANIFEST = 128 * 1024
MAX_INDEX = 2 * 1024 * 1024
MAX_FILES = 64
HEX = re.compile(r"^[0-9a-f]{64}$")
SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$")
EXPECTED_PATHS = frozenset(
    ["runtime/libobelisk.so", "runtime/libsubhook.so"]
    + [f"plugins/{p}/{p}.so" for p in PLUGINS]
    + [f"sdk/include/obelisk/{h}" for h in HEADERS]
    + [f"sdk/lib/cmake/Obelisk/{n}.cmake" for n in ("ObeliskConfig", "ObeliskConfigVersion", "ObeliskTargets")]
    + [f"licenses/{n}" for n in ("Obelisk.txt", "fmt.txt", "spdlog.txt", "subhook.txt")]
)


class ArtifactError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArtifactError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    except (ValueError, TypeError, RecursionError) as exc:
        raise ArtifactError("JSON document cannot be canonicalized") from exc


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def parse_json(data: bytes):
    try:
        return json.loads(data, object_pairs_hook=unique_object, parse_constant=lambda _: (_ for _ in ()).throw(ArtifactError("Non-finite JSON value")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ArtifactError("Invalid JSON document") from exc


def checked_path(value, *, exists=True) -> Path:
    path = Path(os.path.abspath(os.fspath(value)))
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            if exists or current != path:
                raise ArtifactError("Required path or ancestor does not exist")
            break
        require(not stat.S_ISLNK(info.st_mode), "Symlink path component rejected")
    return path


def read_regular(value, limit=MAX_FILE, *, private=False) -> bytes:
    path = checked_path(value)
    original = path.lstat()
    require(stat.S_ISREG(original.st_mode) and original.st_nlink == 1, "Expected a regular non-hardlinked file")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "Expected a regular non-hardlinked file")
        require((original.st_dev, original.st_ino) == (before.st_dev, before.st_ino), "File replaced during open")
        require(0 <= before.st_size <= limit, "File exceeds allowed size")
        if private:
            require(before.st_uid == os.geteuid() and stat.S_IMODE(before.st_mode) == 0o600, "Private key requires current-owner mode 0600")
        data = bytearray()
        while True:
            chunk = os.read(fd, min(1024 * 1024, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            require(len(data) <= limit, "File exceeds allowed size")
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), "File changed during read")
        return bytes(data)
    finally:
        os.close(fd)


def private_dir(value) -> Path:
    path = checked_path(value)
    info = path.stat()
    require(stat.S_ISDIR(info.st_mode), "Expected existing private directory")
    require(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700, "Directory requires current-owner mode 0700")
    trusted_ancestors(path)
    return path


def trusted_ancestors(path: Path) -> None:
    for ancestor in path.parents:
        info = ancestor.stat()
        require(info.st_uid in (0, os.geteuid()), "Untrusted ancestor owner")
        shared_tmp = info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX)
        require(not (info.st_mode & 0o022) or shared_tmp, "Untrusted writable ancestor")


def trusted_key_bytes(value, *, private=False) -> bytes:
    path = checked_path(value)
    trusted_ancestors(path)
    info = path.stat()
    require(info.st_uid in (0, os.geteuid()) and not (info.st_mode & 0o022), "Untrusted key ownership or permissions")
    return read_regular(path, 16 * 1024, private=private)


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new(path: Path, data: bytes, mode=0o600) -> None:
    checked_path(path, exists=False)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
        os.fchmod(fd, mode)
    finally:
        os.close(fd)


@contextlib.contextmanager
def directory_lock(path: Path, name: str):
    lock = path / name
    checked_path(lock, exists=False)
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o600, "Unsafe lock file")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def openssl(*args: str) -> bytes:
    try:
        result = subprocess.run(["openssl", *map(str, args)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ArtifactError("OpenSSL unavailable or timed out") from exc
    require(result.returncode == 0, "OpenSSL operation failed")
    return result.stdout


def ed25519_public(data: bytes) -> None:
    with tempfile.TemporaryDirectory(prefix="obelisk-key-check-") as name:
        key = Path(name) / "public.pem"
        write_new(key, data)
        der = openssl("pkey", "-pubin", "-in", key, "-outform", "DER")
        require(len(der) == 44 and der[:12] == bytes.fromhex("302a300506032b6570032100"), "Only Ed25519 verification keys are supported")


def sign_manifest(data: bytes, key_data: bytes) -> bytes:
    with tempfile.TemporaryDirectory(prefix="obelisk-sign-") as name:
        root = Path(name)
        write_new(root / "private.pem", key_data)
        write_new(root / "manifest", data)
        public = openssl("pkey", "-in", root / "private.pem", "-pubout")
        ed25519_public(public)
        signature = openssl("pkeyutl", "-sign", "-inkey", root / "private.pem", "-rawin", "-in", root / "manifest")
        require(len(signature) == 64, "Unexpected Ed25519 signature size")
        return signature


def verify_signature(data: bytes, signature: bytes, trusted: bytes) -> None:
    require(len(signature) == 64, "Invalid signature length")
    ed25519_public(trusted)
    with tempfile.TemporaryDirectory(prefix="obelisk-verify-") as name:
        root = Path(name)
        write_new(root / "public.pem", trusted)
        write_new(root / "manifest", data)
        write_new(root / "signature", signature)
        openssl("pkeyutl", "-verify", "-pubin", "-inkey", root / "public.pem", "-rawin", "-in", root / "manifest", "-sigfile", root / "signature")


def keygen(private_key, public_key) -> dict:
    private = checked_path(private_key, exists=False)
    public = checked_path(public_key, exists=False)
    require(private != public, "Private and public key paths must differ")
    private_dir(private.parent)
    private_dir(public.parent)
    require(not private.exists() and not public.exists(), "Key output already exists")
    generated = openssl("genpkey", "-algorithm", "ED25519")
    created = []
    try:
        write_new(private, generated)
        created.append(private)
        with tempfile.TemporaryDirectory(prefix="obelisk-keygen-") as name:
            temp_key = Path(name) / "private.pem"
            write_new(temp_key, generated)
            public_data = openssl("pkey", "-in", temp_key, "-pubout")
        write_new(public, public_data)
        created.append(public)
        fsync_dir(private.parent)
        if public.parent != private.parent:
            fsync_dir(public.parent)
    except BaseException:
        for path in reversed(created):
            path.unlink()
        raise
    return {"created": True, "algorithm": "Ed25519", "public_key_sha256": digest(public_data)}


def validate_version(version: str) -> None:
    require(isinstance(version, str) and len(version) <= 64, "Invalid version")
    match = SEMVER.fullmatch(version)
    require(match is not None, "Version must follow semver")
    if match.group(4):
        require(all(not (part.isdigit() and len(part) > 1 and part[0] == "0") for part in match.group(4).split(".")), "Numeric prerelease identifiers must not have leading zeros")


def check_elf(data: bytes) -> None:
    require(len(data) >= 64 and data[:7] == b"\x7fELF\x02\x01\x01", "Expected a Linux x86_64 ELF shared object")
    kind, machine = struct.unpack_from("<HH", data, 16)
    require(kind == 3 and machine == 62, "Expected an x86_64 shared object")


def collect_payload(build_dir, source_root) -> dict[str, bytes]:
    build = checked_path(build_dir)
    source = checked_path(source_root)
    paths = {"runtime/libobelisk.so": build / "libobelisk.so", "runtime/libsubhook.so": build / "_deps/subhook-build/libsubhook.so"}
    paths.update({f"plugins/{p}/{p}.so": build / f"plugins/{p}/{p}.so" for p in PLUGINS})
    paths.update({f"sdk/include/obelisk/{h}": source / f"include/obelisk/{h}" for h in HEADERS})
    targets = list(build.glob("CMakeFiles/Export/*/ObeliskTargets.cmake"))
    require(len(targets) == 1, "Expected exactly one generated SDK target export")
    paths.update({"sdk/lib/cmake/Obelisk/ObeliskConfig.cmake": build / "ObeliskConfig.cmake", "sdk/lib/cmake/Obelisk/ObeliskConfigVersion.cmake": build / "ObeliskConfigVersion.cmake", "sdk/lib/cmake/Obelisk/ObeliskTargets.cmake": targets[0]})
    paths.update({"licenses/Obelisk.txt": source / "LICENSE", "licenses/fmt.txt": build / "_deps/fmt-src/LICENSE.rst", "licenses/spdlog.txt": build / "_deps/spdlog-src/LICENSE"})
    payload = {path: read_regular(local) for path, local in paths.items()}
    subhook = read_regular(build / "_deps/subhook-src/subhook.h", 64 * 1024)
    require(subhook.startswith(b"/* Copyright") and b" */" in subhook, "Subhook license notice missing")
    notice = subhook.split(b" */", 1)[0] + b" */\n"
    require(b"Redistribution" in notice and b"DISCLAIMER" in notice.upper(), "Incomplete subhook license notice")
    payload["licenses/subhook.txt"] = notice
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, bytes]) -> None:
    require(set(payload) == EXPECTED_PATHS, "Artifact must contain exactly the approved runtime, plugins, SDK and notices")
    require(sum(map(len, payload.values())) <= MAX_TOTAL, "Payload exceeds total limit")
    for path, content in payload.items():
        require(0 < len(content) <= MAX_FILE, "Empty or oversized artifact file")
        if path.endswith(".so"):
            check_elf(content)


def make_archive(payload: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=9) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for path, content in sorted(payload.items()):
                info = tarfile.TarInfo(path)
                info.size = len(content)
                info.mode = 0o644
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                archive.addfile(info, io.BytesIO(content))
    result = buffer.getvalue()
    require(len(result) <= MAX_ARCHIVE, "Compressed archive exceeds limit")
    return result


def make_manifest(version: str, channel: str, payload: dict[str, bytes], archive: bytes) -> dict:
    validate_version(version)
    require(channel == "experimental", "Only experimental artifacts can be produced before acceptance")
    return {"schema_version": 1, "version": version, "channel": channel, "platform": "linux-x86_64", "game": "ase", "game_build": "21241282", "game_executable_sha256": GAME_SHA256, "api_bytes": 312, "stability": "experimental", "runtime_ready": False, "components": list(PLUGINS), "archive_sha256": digest(archive), "archive_size": len(archive), "files": [{"path": path, "size": len(content), "sha256": digest(content)} for path, content in sorted(payload.items())]}


def validate_manifest(data: bytes) -> dict:
    require(0 < len(data) <= MAX_MANIFEST, "Invalid manifest size")
    result = parse_json(data)
    keys = {"schema_version", "version", "channel", "platform", "game", "game_build", "game_executable_sha256", "api_bytes", "stability", "runtime_ready", "components", "archive_sha256", "archive_size", "files"}
    require(isinstance(result, dict) and set(result) == keys and canonical(result) == data, "Manifest is not canonical schema 1 JSON")
    validate_version(result["version"])
    require(type(result["schema_version"]) is int and result["schema_version"] == 1, "Unsupported manifest schema")
    require(result["channel"] == result["stability"] == "experimental" and result["runtime_ready"] is False, "Experimental readiness boundary changed")
    require(result["platform"] == "linux-x86_64" and result["game"] == "ase" and result["game_build"] == "21241282" and result["game_executable_sha256"] == GAME_SHA256, "Unsupported game target")
    require(type(result["api_bytes"]) is int and result["api_bytes"] == 312 and result["components"] == list(PLUGINS), "Unexpected API or components")
    require(isinstance(result["archive_sha256"], str) and HEX.fullmatch(result["archive_sha256"]) is not None, "Invalid archive digest")
    require(type(result["archive_size"]) is int and 0 < result["archive_size"] <= MAX_ARCHIVE, "Invalid archive size")
    files = result["files"]
    require(isinstance(files, list) and 0 < len(files) <= MAX_FILES, "Invalid file list")
    names = []
    total = 0
    for entry in files:
        require(isinstance(entry, dict) and set(entry) == {"path", "size", "sha256"}, "Invalid file entry")
        path = entry["path"]
        require(isinstance(path, str) and path in EXPECTED_PATHS, "Unapproved artifact path")
        require(type(entry["size"]) is int and 0 < entry["size"] <= MAX_FILE, "Invalid payload size")
        require(isinstance(entry["sha256"], str) and HEX.fullmatch(entry["sha256"]) is not None, "Invalid payload digest")
        names.append(path)
        total += entry["size"]
    require(names == sorted(EXPECTED_PATHS) and total <= MAX_TOTAL, "Missing, duplicate or oversized payload")
    return result


class LimitedReader:
    def __init__(self, stream, limit):
        self.stream, self.remaining = stream, limit

    def read(self, size=-1):
        if size < 0:
            size = self.remaining + 1
        result = self.stream.read(min(size, self.remaining + 1))
        self.remaining -= len(result)
        require(self.remaining >= 0, "Uncompressed archive exceeds limit")
        return result


def unpack_verified(archive: bytes, manifest: dict) -> dict[str, bytes]:
    require(len(archive) == manifest["archive_size"] and digest(archive) == manifest["archive_sha256"], "Archive digest or size mismatch")
    expected = {entry["path"]: entry for entry in manifest["files"]}
    payload = {}
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(archive), mode="rb") as compressed:
            limited = LimitedReader(compressed, MAX_TOTAL + MAX_FILES * 4096 + 10240)
            end_blocks = 0
            while True:
                block = limited.read(512)
                if not block:
                    break
                require(len(block) == 512, "Truncated tar block")
                if block == bytes(512):
                    end_blocks += 1
                    require(end_blocks <= 21, "Excessive tar padding")
                    continue
                require(end_blocks == 0, "Data after tar end marker")
                require(len(payload) < MAX_FILES, "Too many tar entries")
                # Parse each raw header; TarFile iteration silently consumes GNU/PAX
                # metadata before exposing members and therefore cannot police it.
                info = tarfile.TarInfo.frombuf(block, "utf-8", "strict")
                require(info.type == tarfile.REGTYPE and not info.pax_headers and not info.sparse, "Only plain regular tar files are allowed")
                name = info.name
                require(not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts and "\\" not in name and name in expected, "Unsafe or unlisted tar path")
                require(name not in payload, "Duplicate tar entry")
                entry = expected[name]
                require(info.size == entry["size"] and not (info.mode & 0o7000), "Invalid tar file size or mode")
                content = limited.read(entry["size"])
                require(len(content) == entry["size"] and digest(content) == entry["sha256"], "Payload digest mismatch")
                padding = limited.read((-entry["size"]) % 512)
                require(padding == bytes((-entry["size"]) % 512), "Invalid tar payload padding")
                payload[name] = content
            require(end_blocks >= 2, "Missing tar end marker")
    except (tarfile.TarError, gzip.BadGzipFile, EOFError, OSError, UnicodeError, zlib.error) as exc:
        raise ArtifactError("Invalid compressed tar archive") from exc
    validate_payload(payload)
    return payload


def verify(archive, manifest, signature, trusted_key):
    data = read_regular(manifest, MAX_MANIFEST)
    value = validate_manifest(data)
    sig = read_regular(signature, 64)
    trusted = trusted_key_bytes(trusted_key)
    verify_signature(data, sig, trusted)
    payload = unpack_verified(read_regular(archive, MAX_ARCHIVE), value)
    return value, data, sig, payload


def replace_index(directory: Path, data: bytes) -> None:
    target = directory / "index.json"
    if target.exists() or target.is_symlink():
        read_regular(target, MAX_INDEX)
    fd, name = tempfile.mkstemp(prefix=".index-", dir=directory)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        fsync_dir(directory)
    finally:
        temporary.unlink(missing_ok=True)


def build_artifact(build_dir, source_root, version, channel, output_dir, signing_key) -> dict:
    output = private_dir(output_dir)
    key_data = trusted_key_bytes(signing_key, private=True)
    payload = collect_payload(build_dir, source_root)
    archive = make_archive(payload)
    manifest = make_manifest(version, channel, payload, archive)
    data = canonical(manifest)
    signature = sign_manifest(data, key_data)
    identifier = digest(data)
    base = f"obelisknative-{version}-{channel}-linux-x86_64-{identifier}"
    names = {"archive_name": base + ".tar.gz", "manifest_name": base + ".manifest.json", "signature_name": base + ".manifest.sig"}
    entry = {key: manifest[key] for key in ("version", "channel", "stability", "platform", "game", "game_build", "api_bytes", "runtime_ready", "components", "archive_sha256", "archive_size")}
    entry.update(names)
    entry["id"] = identifier
    with directory_lock(output, ".artifact-index.lock"):
        index_path = output / "index.json"
        if index_path.exists() or index_path.is_symlink():
            index = parse_json(read_regular(index_path, MAX_INDEX))
            require(isinstance(index, dict) and set(index) == {"schema_version", "artifacts"} and type(index["schema_version"]) is int and index["schema_version"] == 1 and isinstance(index["artifacts"], list), "Invalid artifact index")
        else:
            index = {"schema_version": 1, "artifacts": []}
        require(len(index["artifacts"]) <= 256 and all(isinstance(item, dict) and isinstance(item.get("id"), str) for item in index["artifacts"]), "Invalid or oversized artifact index")
        same = [item for item in index["artifacts"] if item["id"] == identifier]
        require(not same or same == [entry], "Conflicting index entry")
        created = []
        encoded = None
        try:
            for name, content in ((names["archive_name"], archive), (names["manifest_name"], data), (names["signature_name"], signature)):
                path = output / name
                if path.exists() or path.is_symlink():
                    require(read_regular(path, MAX_ARCHIVE) == content, "Immutable output already exists with different bytes")
                else:
                    write_new(path, content, 0o400)
                    created.append(path)
            if not same:
                index["artifacts"].append(entry)
                index["artifacts"].sort(key=lambda item: item["id"])
            encoded = canonical(index)
            require(len(encoded) <= MAX_INDEX, "Artifact index exceeds size limit")
            replace_index(output, encoded)
        except BaseException:
            # A failed directory fsync may follow a successful index rename.
            # Preserve published bytes in that case; a retry revalidates them.
            published = False
            if encoded is not None and (index_path.exists() or index_path.is_symlink()):
                try:
                    published = read_regular(index_path, MAX_INDEX) == encoded
                except Exception:
                    published = True  # Uncertain publication: retain, never guess.
            if not published:
                for path in reversed(created):
                    path.unlink()
            raise
    return entry


def assert_staged(destination: Path, data: bytes, signature: bytes, payload: dict[str, bytes]) -> None:
    expected = dict(payload, **{"manifest.json": data, "manifest.sig": signature})
    expected_directories = {parent.as_posix() for name in expected for parent in PurePosixPath(name).parents if str(parent) != "."}
    require(stat.S_IMODE(destination.stat().st_mode) == 0o500 and destination.stat().st_uid == os.geteuid(), "Staged version is not immutable/private")
    actual = set()
    for directory, folders, filenames in os.walk(destination, followlinks=False):
        for folder in folders:
            path = checked_path(Path(directory) / folder)
            require(path.relative_to(destination).as_posix() in expected_directories, "Unexpected staged directory")
            require(path.is_dir() and path.stat().st_uid == os.geteuid() and stat.S_IMODE(path.stat().st_mode) == 0o500, "Unsafe staged directory")
        for filename in filenames:
            path = Path(directory) / filename
            relative = path.relative_to(destination).as_posix()
            require(relative in expected, "Unexpected staged file")
            require(read_regular(path, MAX_FILE) == expected[relative] and path.stat().st_uid == os.geteuid() and stat.S_IMODE(path.stat().st_mode) == 0o400, "Staged file was changed")
            actual.add(relative)
    require(actual == set(expected), "Missing staged file")


def remove_temporary(path: Path) -> None:
    if path.exists():
        for directory, _, _ in os.walk(path, followlinks=False):
            os.chmod(directory, 0o700)
        shutil.rmtree(path)


def stage_artifact(archive, manifest, signature, trusted_key, stage_root) -> dict:
    root = private_dir(stage_root)
    value, data, sig, payload = verify(archive, manifest, signature, trusted_key)
    identifier = digest(data)
    with directory_lock(root, ".artifact-stage.lock"):
        versions = root / "versions"
        if not versions.exists() and not versions.is_symlink():
            versions.mkdir(mode=0o700)
            fsync_dir(root)
        private_dir(versions)
        destination = checked_path(versions / identifier, exists=False)
        if destination.exists():
            assert_staged(destination, data, sig, payload)
            return {"id": identifier, "staged": True, "replayed": True, "activated": False, "runtime_ready": False}
        temporary = Path(tempfile.mkdtemp(prefix=".stage-", dir=versions))
        try:
            files = dict(payload, **{"manifest.json": data, "manifest.sig": sig})
            for name, content in sorted(files.items()):
                target = temporary / name
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                write_new(target, content, 0o400)
            for directory, _, _ in os.walk(temporary, topdown=False):
                os.chmod(directory, 0o500)
                fsync_dir(Path(directory))
            assert_staged(temporary, data, sig, payload)
            os.rename(temporary, destination)
            fsync_dir(versions)
        except BaseException:
            remove_temporary(temporary)
            raise
    return {"id": identifier, "staged": True, "replayed": False, "activated": False, "runtime_ready": value["runtime_ready"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("keygen", help="Create a new Ed25519 pair without overwriting any file")
    generate.add_argument("--private-key", required=True)
    generate.add_argument("--public-key", required=True)
    build = commands.add_parser("build", help="Package an experimental artifact from an existing build")
    for name in ("build-dir", "source-root", "version", "output-dir", "signing-key"):
        build.add_argument("--" + name, required=True)
    build.add_argument("--channel", choices=("experimental",), default="experimental")
    for command in ("verify", "stage"):
        sub = commands.add_parser(command)
        for name in ("archive", "manifest", "signature", "trusted-key"):
            sub.add_argument("--" + name, required=True)
        if command == "stage":
            sub.add_argument("--stage-root", required=True)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        if command == "keygen":
            result = keygen(**args)
        elif command == "build":
            result = build_artifact(**args)
        elif command == "stage":
            result = stage_artifact(**args)
        else:
            value, data, _, _ = verify(**args)
            result = {"id": digest(data), "verified": True, "files": len(value["files"]), "runtime_ready": False, "activated": False}
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ArtifactError, OSError) as exc:
        print(f"Artifact operation refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

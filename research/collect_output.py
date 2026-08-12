"""Validate and copy a tiny, link-free research result for human review."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
from pathlib import Path

WINDOWS_REPARSE_POINT = 0x400
MAX_FILES = 3


def _is_reparse(info: os.stat_result) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & WINDOWS_REPARSE_POINT)


def _regular_lstat(path: Path) -> os.stat_result:
    info = path.lstat()
    if path.is_symlink() or _is_reparse(info) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"research output must be a regular non-link file: {path}")
    if info.st_nlink != 1:
        raise ValueError(f"research output hardlinks are forbidden: {path}")
    return info


def _stable_read(path: Path, maximum: int) -> bytes:
    before = _regular_lstat(path)
    if before.st_size > maximum:
        raise ValueError(f"research output exceeds byte limit: {path}")
    with path.open("rb") as stream:
        handle_before = os.fstat(stream.fileno())
        content = stream.read(maximum + 1)
        handle_after = os.fstat(stream.fileno())
    after = _regular_lstat(path)

    def identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)

    if not identity(before) == identity(handle_before) == identity(handle_after) == identity(after):
        raise ValueError(f"research output changed while being collected: {path}")
    if len(content) > maximum:
        raise ValueError(f"research output exceeds byte limit: {path}")
    return content


def _inventory(source: Path) -> list[tuple[Path, Path]]:
    source_info = source.lstat()
    if source.is_symlink() or _is_reparse(source_info) or not stat.S_ISDIR(source_info.st_mode):
        raise ValueError("research output root must be a regular directory")
    allowed: list[tuple[Path, Path]] = []
    root_entries = sorted(source.iterdir(), key=lambda path: path.name)
    for entry in root_entries:
        relative = entry.relative_to(source)
        if entry.name == "report.md":
            _regular_lstat(entry)
            allowed.append((entry, relative))
            continue
        if entry.name != "candidates":
            raise ValueError(f"unexpected research output path: {relative}")
        info = entry.lstat()
        if entry.is_symlink() or _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("candidates output must be a regular directory")
        for candidate in sorted(entry.iterdir(), key=lambda path: path.name):
            candidate_relative = candidate.relative_to(source)
            _regular_lstat(candidate)
            if not (
                candidate.suffix == ".py" or candidate.name.endswith(".candidate.json")
            ):
                raise ValueError(f"unexpected candidate output: {candidate_relative}")
            allowed.append((candidate, candidate_relative))

    if not any(relative.as_posix() == "report.md" for _path, relative in allowed):
        raise ValueError("research cycle must produce output/report.md")
    candidate_files = [
        relative for _path, relative in allowed if relative.parts[0] == "candidates"
    ]
    if candidate_files:
        if len(candidate_files) != 2:
            raise ValueError("candidate output must contain exactly one .py/.candidate.json pair")
        python_files = [path for path in candidate_files if path.suffix == ".py"]
        manifests = [path for path in candidate_files if path.name.endswith(".candidate.json")]
        if len(python_files) != 1 or len(manifests) != 1:
            raise ValueError("candidate output must contain one Python file and one manifest")
        manifest_slug = manifests[0].name.removesuffix(".candidate.json")
        if python_files[0].stem != manifest_slug:
            raise ValueError("candidate Python and manifest filenames must share one slug")
    if len(allowed) > MAX_FILES:
        raise ValueError(f"research output may contain at most {MAX_FILES} files")
    return allowed


def collect(source: Path, destination: Path, maximum_bytes: int) -> dict[str, object]:
    if maximum_bytes < 1:
        raise ValueError("maximum_bytes must be positive")
    source = source.absolute()
    destination = destination.absolute()
    if destination.exists():
        raise ValueError("research inbox destination already exists")
    inventory = _inventory(source)
    remaining = maximum_bytes
    contents: list[tuple[Path, bytes]] = []
    for path, relative in inventory:
        content = _stable_read(path, remaining)
        remaining -= len(content)
        contents.append((relative, content))

    destination.mkdir(parents=True)
    try:
        for relative, content in contents:
            output = destination / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return {
        "ok": True,
        "destination": str(destination),
        "files": [relative.as_posix() for relative, _content in contents],
        "bytes": maximum_bytes - remaining,
    }


def safe_remove_tree(root: Path, expected_parent: Path) -> None:
    """Remove only a verified non-link tree directly below the dedicated temp root."""

    root = root.absolute()
    expected_parent = expected_parent.resolve(strict=True)
    if root.parent.resolve(strict=True) != expected_parent:
        raise ValueError("cleanup root is not directly below the dedicated temporary root")
    root_info = root.lstat()
    if root.is_symlink() or _is_reparse(root_info) or not stat.S_ISDIR(root_info.st_mode):
        raise ValueError("cleanup root must be a regular directory")

    def remove_directory(directory: Path) -> None:
        for entry in list(os.scandir(directory)):
            path = Path(entry.path)
            info = path.lstat()
            if path.is_symlink() or _is_reparse(info):
                raise ValueError(f"refusing to clean linked workspace entry: {path}")
            if stat.S_ISDIR(info.st_mode):
                remove_directory(path)
                path.rmdir()
            elif stat.S_ISREG(info.st_mode):
                path.unlink()
            else:
                raise ValueError(f"refusing to clean non-regular workspace entry: {path}")

    remove_directory(root)
    root.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--maximum-bytes", type=int, required=True)
    parser.add_argument("--cleanup-root", type=Path)
    parser.add_argument("--cleanup-parent", type=Path)
    args = parser.parse_args()
    result = collect(args.source, args.destination, args.maximum_bytes)
    if (args.cleanup_root is None) != (args.cleanup_parent is None):
        raise ValueError("--cleanup-root and --cleanup-parent must be supplied together")
    if args.cleanup_root is not None and args.cleanup_parent is not None:
        safe_remove_tree(args.cleanup_root, args.cleanup_parent)
        result["workspace_removed"] = True
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

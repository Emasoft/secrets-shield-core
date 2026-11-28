#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Vendor a tag or commit of secrets-shield-core into a consumer plugin as a hash-pinned folder.

  vendor_into.py --into <consumer-root> --dir <subpath> --ref <tag|sha>

Copies every tracked file of the ref (except tools/) to <consumer-root>/<subpath>, deletes the files a previous
UPSTREAM.json listed that the ref no longer has, and writes the new UPSTREAM.json pin. Consumers ship only a read-only
check of that pin; this writer stays here (CPV rule RC-164 forbids a plugin script that writes fetched code into its own tree).
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

# WHY a timeout on every git call: a git that hangs (an index lock, a stalled filesystem) must stop the run with an error,
# never wait forever. The TimeoutExpired surfaces the same way a failing git call already does under check=True.
GIT_TIMEOUT_S = 60

# WHY the checkout is found from the script path and the destination never is: the core is always the repo holding this script,
# while the destination is whatever the caller names on the command line; deriving it from here could write into this repo.
CORE_ROOT = Path(__file__).resolve().parent.parent
SOURCE = "Emasoft/secrets-shield-core"
PIN_FILE = "UPSTREAM.json"
# WHY tools is never vendored: this writer lives in tools/, and a consumer must not receive a script that writes into its own tree.
EXCLUDED_FIRST_SEGMENT = "tools"
REGULAR_FILE_MODE = "100644"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_run(git: str, root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([git, "-C", str(root), *args], check=check, capture_output=True, timeout=GIT_TIMEOUT_S)


def git_text(git: str, root: Path, *args: str) -> str:
    return git_run(git, root, *args).stdout.decode("utf-8").strip()


def resolve_target(into_arg: str, dir_arg: str) -> tuple[Path, Path]:
    into = Path(into_arg).resolve()
    if not into.is_dir():
        sys.exit(f"vendor_into: --into {into} is not an existing directory")
    # WHY refuse an absolute --dir: into / "/abs" silently becomes "/abs", which would write outside the consumer.
    if Path(dir_arg).is_absolute():
        sys.exit(f"vendor_into: --dir {dir_arg} must be relative to --into")
    target = (into / dir_arg).resolve()
    # WHY strictly inside: target == into would make the writer own the whole consumer root, and ../x or a symlink hop would leave it.
    if target == into or not target.is_relative_to(into):
        sys.exit(f"vendor_into: --dir {dir_arg} resolves to {target}, which is not strictly inside {into}")
    return into, target


def require_clean_target(git: str, into: Path, target: Path) -> None:
    # WHY refuse a non-repo: without git there is no way to restore what this run overwrites or deletes.
    inside = git_run(git, into, "rev-parse", "--is-inside-work-tree", check=False)
    if inside.returncode != 0 or inside.stdout.decode("utf-8").strip() != "true":
        sys.exit(f"vendor_into: {into} is not a git work tree; nothing there could be restored")
    # WHY refuse any status output: uncommitted changes under target would be overwritten with no way for git to bring them back.
    dirty = git_text(git, into, "status", "--porcelain", "--", str(target))
    if dirty:
        sys.exit(f"vendor_into: {target} has uncommitted changes; commit or discard them first:\n{dirty}")


def list_kept_paths(git: str, sha: str) -> list[str]:
    listing = git_run(git, CORE_ROOT, "ls-tree", "-r", "-z", sha).stdout.decode("utf-8")
    kept = []
    for entry in listing.split("\0"):
        if not entry:
            continue
        # WHY split on the tab: ls-tree -z prints "<mode> <type> <sha>\t<path>" and the path may hold spaces.
        meta, path = entry.split("\t", 1)
        mode, kind, _ = meta.split(" ")
        if path.split("/", 1)[0] == EXCLUDED_FIRST_SEGMENT:
            continue
        # WHY refuse anything but a plain blob: the copy is write_bytes, which reproduces neither modes nor symlinks nor submodules;
        # refusing before any write keeps the consumer folder untouched.
        if mode != REGULAR_FILE_MODE or kind != "blob":
            sys.exit(f"vendor_into: {path} is mode {mode}; only regular files are vendored")
        kept.append(path)
    return sorted(kept)


def previous_pin_files(target: Path) -> list[str]:
    pin_path = target / PIN_FILE
    if not pin_path.is_file():
        return []
    files = list(json.loads(pin_path.read_text(encoding="utf-8"))["files"])
    for rel in files:
        # WHY validate the old pin paths: the deletion list comes from a file in the consumer, so a hand-edited ../ entry must not unlink outside target.
        if Path(rel).is_absolute() or not (target / rel).resolve().is_relative_to(target):
            sys.exit(f"vendor_into: previous {PIN_FILE} lists {rel}, which is outside {target}")
    return files


def delete_stale(target: Path, stale: list[str]) -> int:
    deleted = 0
    for rel in stale:
        file = target / rel
        if file.is_file() or file.is_symlink():
            file.unlink()
            deleted += 1
        # WHY walk up from the deleted file and not over the folder: only directories that held a pinned file are touched, so a
        # consumer own empty directory is left alone; target itself and anything above it are never removed.
        parent = file.parent
        while parent != target and parent.is_relative_to(target) and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
    return deleted


def vendor(into_arg: str, dir_arg: str, ref: str) -> int:
    # WHY shutil.which: bandit B607 flags a bare program name; no git on PATH is a hard error, never a partial run.
    git = shutil.which("git")
    if git is None:
        sys.exit("vendor_into: git is not on PATH")
    # WHY verify the toplevel: if the script was copied out of its repo, parent.parent would be some unrelated folder.
    if Path(git_text(git, CORE_ROOT, "rev-parse", "--show-toplevel")).resolve() != CORE_ROOT:
        sys.exit(f"vendor_into: {CORE_ROOT} is not the top level of a git work tree")
    into, target = resolve_target(into_arg, dir_arg)
    require_clean_target(git, into, target)
    # WHY resolve first: the pin must record a full sha, never a branch name that moves.
    full = git_text(git, CORE_ROOT, "rev-parse", "--verify", f"{ref}^{{commit}}")
    # WHY a tag is recorded only when the ref is one: a raw sha or branch name has no tag to record.
    is_tag = git_run(git, CORE_ROOT, "rev-parse", "--verify", "--quiet", f"refs/tags/{ref}", check=False).returncode == 0
    print(f"vendor_into: {ref} -> {full}" + (f" (tag {ref})" if is_tag else ""))
    rels = list_kept_paths(git, full)
    previous = previous_pin_files(target)
    # WHY fetch every blob before writing: one failing git call must leave the consumer folder untouched.
    fetched = {rel: git_run(git, CORE_ROOT, "show", f"{full}:{rel}").stdout for rel in rels}
    for rel, data in fetched.items():
        file = target / rel
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
    print(f"vendor_into: wrote {len(fetched)} files")
    # WHY only the previous pin decides what to delete: files it lists were written by this tool and are git-tracked, so git restores
    # them; no previous pin means nothing to delete, and files no pin lists are the consumer own and are never touched.
    deleted = delete_stale(target, [rel for rel in previous if rel not in fetched])
    print(f"vendor_into: deleted {deleted} files")
    pin: dict[str, object] = {"source": SOURCE}
    if is_tag:
        pin["tag"] = ref
    pin["commit"] = full
    pin["files"] = {rel: sha256(data) for rel, data in fetched.items()}
    pin_path = target / PIN_FILE
    pin_path.write_text(json.dumps(pin, indent=2) + "\n", encoding="utf-8")
    print(f"vendor_into: pin {pin_path}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--into", required=True, help="consumer plugin root (an existing git work tree)")
    parser.add_argument("--dir", required=True, help="folder inside --into that receives the vendored files")
    parser.add_argument("--ref", required=True, help="secrets-shield-core tag or commit to vendor")
    args = parser.parse_args(argv)
    # WHY a one-line error for a failed or timed-out git call: an unknown ref is a user mistake, not a crash, and a traceback hides the git message.
    # Every such failure happens before the first write (rev-parse, ls-tree, show of every blob), so exiting here leaves the consumer untouched.
    try:
        return vendor(args.into, args.dir, args.ref)
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", "replace").strip()
        sys.exit(f"vendor_into: git failed with exit {error.returncode}: {detail}")
    except subprocess.TimeoutExpired:
        sys.exit(f"vendor_into: git timed out after {GIT_TIMEOUT_S}s")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

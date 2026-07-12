import subprocess


def get_commit_sha() -> str | None:
    """Returns the current git commit SHA for the repository.

    Tries the full SHA first; falls back to the short SHA if needed.
    Returns None if git is unavailable or the repo has no commits.
    """
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).strip().decode()
        return sha
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        sha = (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).strip().decode()
        )
        return sha
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_commit_tag() -> str | None:
    """Returns the current git tag for the repository, if any.

    Returns None if git is unavailable or the repo has no tags.
    """
    try:
        tag = (
            subprocess.check_output(["git", "describe", "--tags", "--abrev=0"], stderr=subprocess.DEVNULL)
            .strip()
            .decode()
        )
        return tag
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_loc(
    since: str,
    author: str | None = None,
    all_authors: bool = False,
    branch: str | None = None,
    repo: str = ".",
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    breakdown: bool = False,
) -> dict:
    """Count lines of code written since a given point in time.

    Mirrors the behaviour of scripts/loc_since.sh.

    Args:
        since:       Point in time accepted by ``git log --since`` (e.g.
                     ``"midnight"``, ``"2 days ago"``, ``"2026-04-06"``).
        author:      Limit to a specific author name or e-mail pattern.
                     Defaults to the current git ``user.name`` when
                     *all_authors* is ``False``.
        all_authors: When ``True`` count commits from every author,
                     ignoring *author*.
        branch:      Branch or ref to inspect (default: current branch).
        repo:        Path to the git repository (default: ``"."``).
        include:     Glob patterns — only matching files are counted
                     (e.g. ``["*.py"]``).  Passed directly to ``git log``
                     as path filters.
        exclude:     Glob patterns — matching files are excluded in
                     post-processing (e.g. ``["*.json"]``).
        breakdown:   When ``True`` the returned dict contains a ``"files"``
                     key with per-file addition/deletion/net counts.

    Returns:
        A dict with keys:
            ``since``, ``author``, ``commits``, ``additions``,
            ``deletions``, ``net``, and (when *breakdown* is ``True``)
            ``files`` — a list of
            ``{"file": str, "additions": int, "deletions": int, "net": int}``.

    Raises:
        ValueError: if *since* is empty or *repo* is not a git repository.
        RuntimeError: if the current git ``user.name`` cannot be determined
                      and no author is provided.
    """
    import fnmatch
    import os

    if not since:
        raise ValueError("'since' is required")

    # Verify the repo path looks like a git repo.
    try:
        subprocess.check_output(["git", "-C", repo, "rev-parse", "--git-dir"], stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise ValueError(f"'{repo}' is not a git repository") from exc

    # Resolve author when not counting all authors.
    resolved_author: str | None = None
    if not all_authors:
        if author:
            resolved_author = author
        else:
            try:
                resolved_author = (
                    subprocess.check_output(["git", "-C", repo, "config", "user.name"], stderr=subprocess.DEVNULL)
                    .strip()
                    .decode()
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
            if not resolved_author:
                raise RuntimeError("Could not determine git user. " "Set git config user.name or pass author=.")

    # Build git log command.
    cmd = ["git", "-C", repo, "log", f"--since={since}", "--no-merges", "--numstat", "--format=COMMIT:%H"]

    if branch:
        cmd.append(branch)

    if resolved_author:
        cmd.append(f"--author={resolved_author}")

    include_globs = list(include or [])
    if include_globs:
        cmd.append("--")
        cmd.extend(include_globs)

    # Run git log and parse output.
    try:
        raw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode()
    except subprocess.CalledProcessError:
        raw = ""

    exclude_globs = list(exclude or [])
    file_add: dict[str, int] = {}
    file_del: dict[str, int] = {}
    commit_count = 0

    for line in raw.splitlines():
        if line.startswith("COMMIT:"):
            commit_count += 1
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        added_s, deleted_s, filepath = parts
        if not added_s.isdigit() or not deleted_s.isdigit():
            # Binary files produce "-" — skip them.
            continue

        # Apply exclude globs.
        if any(fnmatch.fnmatch(os.path.basename(filepath), g) or fnmatch.fnmatch(filepath, g) for g in exclude_globs):
            continue

        added = int(added_s)
        deleted = int(deleted_s)
        file_add[filepath] = file_add.get(filepath, 0) + added
        file_del[filepath] = file_del.get(filepath, 0) + deleted

    total_additions = sum(file_add.values())
    total_deletions = sum(file_del.values())
    net_lines = total_additions - total_deletions

    result: dict = {
        "since": since,
        "author": resolved_author or "all",
        "commits": commit_count,
        "additions": total_additions,
        "deletions": total_deletions,
        "net": net_lines,
    }

    if breakdown:
        result["files"] = [
            {
                "file": f,
                "additions": file_add[f],
                "deletions": file_del.get(f, 0),
                "net": file_add[f] - file_del.get(f, 0),
            }
            for f in sorted(file_add)
        ]

    return result

import subprocess


def get_commit_sha() -> str:
    """Returns the current git commit SHA for the repository.

    Tries the full SHA first; falls back to the short SHA if needed.
    Returns an empty string if git is unavailable or the repo has no commits.
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
        return ""

import importlib
from io import StringIO
from unittest.mock import patch

import pytest
import responses as resp


@pytest.fixture
def fbi_main(monkeypatch):
    """Reload pkg.data.sources.fbi.main with test env vars injected."""
    monkeypatch.setenv("GOV_API_BASE_URL", "https://example.test")
    monkeypatch.setenv("GOV_API_KEY", "test-api-key")

    module = importlib.import_module("pkg.data.sources.fbi.main")
    return importlib.reload(module)


@pytest.fixture
def mocked_responses():
    """Activate the `responses` library for the duration of a test.

    Any real HTTP call that is *not* registered will raise a
    ``ConnectionError``, preventing accidental network access.
    """
    with resp.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


@pytest.fixture
def cli_runner(monkeypatch, tmp_path):
    """Run the statpack CLI (main.py:main) in-process.

    Returns a callable:  run(argv) → (stdout: str, stderr: str, exit_code: int)
    """
    monkeypatch.setenv("GOV_API_BASE_URL", "https://example.test")
    monkeypatch.setenv("GOV_API_KEY", "test-api-key")

    def run(argv: list[str]):
        import main as cli_main  # top-level main.py
        importlib.reload(cli_main)

        stdout_buf = StringIO()
        stderr_buf = StringIO()

        exit_code = 0
        with patch("sys.argv", ["main.py"] + argv):
            with patch("sys.stdout", stdout_buf):
                with patch("sys.stderr", stderr_buf):
                    try:
                        cli_main.main()
                    except SystemExit as exc:
                        exit_code = exc.code if exc.code is not None else 0

        return stdout_buf.getvalue(), stderr_buf.getvalue(), exit_code

    run.tmp_path = tmp_path
    return run

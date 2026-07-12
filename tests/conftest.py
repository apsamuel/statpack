import importlib

import pytest
import responses as resp
from click.testing import CliRunner


@pytest.fixture
def fbi_main(monkeypatch):
    """Reload pkg.data.sources.fbi.main with test env vars injected."""
    monkeypatch.setenv("GOV_API_BASE_URL", "https://example.test")
    monkeypatch.setenv("GOV_API_KEY", "test-api-key")

    module = importlib.import_module("statpack.data.sources.fbi.main")
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
        import statpack.cli as cli_main  # src/statpack/cli.py

        importlib.reload(cli_main)

        runner = CliRunner()
        result = runner.invoke(cli_main.cli, argv)

        exit_code = result.exit_code if result.exit_code is not None else 0
        return result.stdout, result.stderr, exit_code

    run.tmp_path = tmp_path
    return run

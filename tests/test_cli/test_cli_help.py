"""Smoke tests for CLI help outputs — verify all sub-commands exit cleanly."""

from typer.testing import CliRunner

from aividio.cli.app import app

runner = CliRunner()


class TestCLIHelp:
    def test_aividio_help_exits_0(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "aividio" in result.output.lower() or "AI-powered" in result.output

    def test_generate_help_exits_0(self):
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "generate" in result.output.lower()

    def test_channel_help_exits_0(self):
        result = runner.invoke(app, ["channel", "--help"])
        assert result.exit_code == 0
        assert "channel" in result.output.lower()

    def test_job_help_exits_0(self):
        result = runner.invoke(app, ["job", "--help"])
        assert result.exit_code == 0
        assert "job" in result.output.lower()

    def test_batch_help_exits_0(self):
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "batch" in result.output.lower()

    def test_effects_help_exits_0(self):
        result = runner.invoke(app, ["effects", "--help"])
        assert result.exit_code == 0
        assert "effects" in result.output.lower()

"""Tests for the chrome-mcp default provider and its auto-connect preflight."""

import json
import socket
from unittest.mock import patch

from click.testing import CliRunner

from reverse_api.chrome_mcp import CHROME_DEVTOOLS_MCP_PACKAGE, AutoConnectStatus, check_auto_connect
from reverse_api.config import DEFAULT_CONFIG


def _config(tmp_path, provider="chrome-mcp"):
    values = {
        "agent_provider": provider,
        "sdk": "claude",
        "claude_code_model": "claude-sonnet-4-6",
        "output_dir": str(tmp_path),
    }
    return lambda key, default=None: values.get(key, default)


class TestCheckAutoConnect:
    def test_missing_port_file(self, tmp_path):
        status = check_auto_connect(tmp_path)
        assert not status.ok
        assert "chrome://inspect/#remote-debugging" in status.message

    def test_unreadable_port_file(self, tmp_path):
        (tmp_path / "DevToolsActivePort").write_text("not-a-port\n")
        assert not check_auto_connect(tmp_path).ok

    def test_closed_port(self, tmp_path):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        (tmp_path / "DevToolsActivePort").write_text(f"{port}\n/devtools/browser/x\n")
        status = check_auto_connect(tmp_path, timeout=0.2)
        assert not status.ok
        assert str(port) in status.message

    def test_open_port(self, tmp_path):
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            port = server.getsockname()[1]
            (tmp_path / "DevToolsActivePort").write_text(f"{port}\n/devtools/browser/x\n")
            assert check_auto_connect(tmp_path).ok


def test_chrome_devtools_mcp_is_pinned_to_1_12():
    assert CHROME_DEVTOOLS_MCP_PACKAGE == "chrome-devtools-mcp@1.12"


def test_chrome_mcp_is_the_default_provider():
    assert DEFAULT_CONFIG["agent_provider"] == "chrome-mcp"


class TestDryRunAutoConnect:
    def _invoke(self, tmp_path, status, *args):
        from reverse_api.cli import agent as agent_cmd

        with patch("reverse_api.cli.config_manager") as cm, \
             patch("reverse_api.chrome_mcp.check_auto_connect", return_value=status), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake"}, clear=False):
            cm.get.side_effect = _config(tmp_path)
            result = CliRunner().invoke(agent_cmd, ["--dry-run", "-p", "fetch jobs", *args])
        return result, json.loads(result.stdout.strip())

    def test_headed_without_auto_connect_is_an_error(self, tmp_path):
        result, payload = self._invoke(tmp_path, AutoConnectStatus(False, "not enabled"))
        assert result.exit_code == 1
        check = next(c for c in payload["checks"] if c["name"] == "chrome-mcp:auto-connect")
        assert check["status"] == "error"
        assert check["message"].startswith("not enabled; ") and "chrome://inspect" in check["message"]
        assert payload["error_kind"] == "config_invalid"

    def test_headed_with_auto_connect_passes(self, tmp_path):
        result, payload = self._invoke(tmp_path, AutoConnectStatus(True, "reachable"))
        check = next(c for c in payload["checks"] if c["name"] == "chrome-mcp:auto-connect")
        assert check["status"] == "ok"

    def test_headless_skips_the_check(self, tmp_path):
        _, payload = self._invoke(tmp_path, AutoConnectStatus(False, "not enabled"), "--headless")
        assert "chrome-mcp:auto-connect" not in {c["name"] for c in payload["checks"]}


def test_agent_json_fails_fast_without_auto_connect(tmp_path):
    from reverse_api.cli import agent as agent_cmd

    with patch("reverse_api.cli.config_manager") as cm, \
         patch("reverse_api.chrome_mcp.check_auto_connect", return_value=AutoConnectStatus(False, "not enabled")), \
         patch("reverse_api.cli.session_manager") as sessions:
        cm.get.side_effect = _config(tmp_path)
        result = CliRunner().invoke(agent_cmd, ["--json", "-p", "fetch jobs", "-u", "https://example.com"])

    payload = json.loads(result.stdout.strip())
    assert result.exit_code == 1
    assert payload["status"] == "error"
    assert payload["error"].startswith("not enabled; ")
    assert payload["error_kind"] == "config_invalid"
    sessions.add_run.assert_not_called()


class TestChromeUserDataDir:
    def test_macos(self, monkeypatch, tmp_path):
        from reverse_api import chrome_mcp

        monkeypatch.setattr(chrome_mcp.sys, "platform", "darwin")
        monkeypatch.setattr(chrome_mcp.Path, "home", lambda: tmp_path)
        assert chrome_mcp.chrome_user_data_dir() == tmp_path / "Library" / "Application Support" / "Google" / "Chrome"

    def test_windows(self, monkeypatch, tmp_path):
        from reverse_api import chrome_mcp

        monkeypatch.setattr(chrome_mcp.sys, "platform", "win32")
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert chrome_mcp.chrome_user_data_dir() == tmp_path / "Google" / "Chrome" / "User Data"
        monkeypatch.delenv("LOCALAPPDATA")
        assert chrome_mcp.chrome_user_data_dir() is None

    def test_linux(self, monkeypatch, tmp_path):
        from reverse_api import chrome_mcp

        monkeypatch.setattr(chrome_mcp.sys, "platform", "linux")
        monkeypatch.delenv("CHROME_CONFIG_HOME", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert chrome_mcp.chrome_user_data_dir() == tmp_path / "google-chrome"
        monkeypatch.setenv("CHROME_CONFIG_HOME", str(tmp_path / "chrome-home"))
        assert chrome_mcp.chrome_user_data_dir() == tmp_path / "chrome-home" / "google-chrome"


def test_out_of_range_port_is_rejected(tmp_path):
    (tmp_path / "DevToolsActivePort").write_text("999999999999999999999999\n")
    status = check_auto_connect(tmp_path)
    assert not status.ok
    assert "invalid port" in status.reason


def test_unreadable_port_file_is_not_reported_as_disabled(tmp_path):
    (tmp_path / "DevToolsActivePort").mkdir()
    status = check_auto_connect(tmp_path)
    assert not status.ok
    assert "could not read" in status.reason


def test_interactive_run_prints_setup_once(tmp_path, capsys):
    from reverse_api.cli import run_auto_capture

    with patch("reverse_api.cli.config_manager") as cm, \
         patch("reverse_api.chrome_mcp.check_auto_connect", return_value=AutoConnectStatus(False, "not enabled")), \
         patch("reverse_api.cli.session_manager") as sessions:
        cm.get.side_effect = _config(tmp_path)
        result = run_auto_capture(prompt="fetch jobs", url="https://example.com", agent_provider="chrome-mcp")

    out = capsys.readouterr().out
    assert result["error"].startswith("not enabled; ")
    assert result["error_kind"] == "config_invalid" and result["error_reported"] is True
    assert out.count("chrome://inspect/#remote-debugging") == 1
    sessions.add_run.assert_not_called()


class TestEngineerHarlessRuns:
    def _invoke(self, tmp_path, mode, *args):
        from reverse_api.cli import engineer as engineer_cmd

        run = {"prompt": "fetch jobs", "mode": mode, "paths": {"har_dir": str(tmp_path / "har")}}
        with patch("reverse_api.cli.session_manager") as sessions, \
             patch("reverse_api.cli.run_reverse_engineering") as engine:
            sessions.get_run.return_value = run
            result = CliRunner().invoke(engineer_cmd, ["abc123", *args])
        engine.assert_not_called()
        return result

    def test_chrome_mcp_run_is_rejected_as_misuse(self, tmp_path):
        result = self._invoke(tmp_path, "chrome-mcp", "--json")
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        assert result.exit_code == 2
        assert payload["error_kind"] == "misuse"
        assert "captured with chrome-mcp" in payload["error"]

    def test_text_mode_exits_2(self, tmp_path):
        assert self._invoke(tmp_path, "chrome-mcp").exit_code == 2

    def test_other_run_without_har_names_the_path(self, tmp_path):
        result = self._invoke(tmp_path, "auto", "--json")
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        assert payload["error"] == f"run abc123 has no HAR at {tmp_path / 'har' / 'recording.har'}"


def test_engineer_json_runtime_error_mentioning_required_exits_1(tmp_path):
    from reverse_api.cli import engineer as engineer_cmd

    with patch("reverse_api.cli.run_engineer", return_value={"error": "field X is required by the API"}):
        result = CliRunner().invoke(engineer_cmd, ["abc123", "--json"])
    assert result.exit_code == 1

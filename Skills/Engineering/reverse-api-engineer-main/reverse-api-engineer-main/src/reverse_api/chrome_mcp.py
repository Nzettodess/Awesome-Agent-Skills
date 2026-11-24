"""Chrome DevTools MCP provider: package pin and auto-connect detection.

Headed chrome-mcp runs attach to the user's own Chrome through ``--autoConnect``,
which only works after remote debugging is enabled at chrome://inspect/#remote-debugging.
Chrome then writes ``DevToolsActivePort`` into its user data directory; that file plus
an open port is what chrome-devtools-mcp looks for.
"""

from __future__ import annotations

import os
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

# Pinned to a minor line: tool signatures change between releases (1.12 requires pageId).
CHROME_DEVTOOLS_MCP_PACKAGE = "chrome-devtools-mcp@1.12"

AUTO_CONNECT_SETUP = (
    "enable remote debugging in Chrome 146+ at chrome://inspect/#remote-debugging "
    "(click \"Enable auto-connect\"), keep Chrome open, or run with --headless"
)


@dataclass(frozen=True)
class AutoConnectStatus:
    ok: bool
    reason: str

    @property
    def message(self) -> str:
        return self.reason if self.ok else f"{self.reason}; {AUTO_CONNECT_SETUP}"


def chrome_user_data_dir() -> Path | None:
    """Default user data directory of stable Google Chrome, the channel --autoConnect uses."""
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        return Path(local) / "Google" / "Chrome" / "User Data" if local else None
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    else:
        # Chrome on Linux prefers CHROME_CONFIG_HOME over XDG_CONFIG_HOME.
        config_home = os.environ.get("CHROME_CONFIG_HOME") or os.environ.get("XDG_CONFIG_HOME")
        return Path(config_home or Path.home() / ".config") / "google-chrome"


def check_auto_connect(user_data_dir: Path | None = None, timeout: float = 1.0) -> AutoConnectStatus:
    """Report whether a running Chrome accepts auto-connect, without launching anything."""
    data_dir = user_data_dir if user_data_dir is not None else chrome_user_data_dir()
    if data_dir is None:
        return AutoConnectStatus(False, "could not locate the Chrome profile directory")
    port_file = data_dir / "DevToolsActivePort"
    try:
        port = int(port_file.read_text(encoding="utf-8").splitlines()[0].strip())
    except FileNotFoundError:
        return AutoConnectStatus(False, "Chrome remote debugging is not enabled")
    except (OSError, ValueError, IndexError) as e:
        return AutoConnectStatus(False, f"could not read {port_file}: {e}")
    if not 0 < port < 65536:
        return AutoConnectStatus(False, f"could not read {port_file}: invalid port {port}")
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            pass
    except OSError:
        return AutoConnectStatus(False, f"Chrome is not running with remote debugging on port {port}")
    return AutoConnectStatus(True, f"Chrome remote debugging reachable on port {port}")

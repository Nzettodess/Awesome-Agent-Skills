"""A failed manual-capture start must not leak Playwright's event loop.

ManualBrowser.start() calls sync_playwright().start() and only stops it inside
close() on the happy path. If startup fails first (e.g. a bad URL makes
page.goto raise), Playwright's sync API leaves an asyncio loop running; the
REPL's next prompt then dies forever with "asyncio.run() cannot be called from
a running event loop". start() must stop Playwright before propagating.
"""

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("playwright")  # ships in the [manual] extra only

from reverse_api.browser import ManualBrowser  # noqa: E402


def _browser(tmp_path):
    return ManualBrowser(run_id="testrun", prompt="grab jobs", output_dir=str(tmp_path))


class TestStartupFailureCleanup:
    def test_playwright_stopped_when_start_raises(self, tmp_path):
        browser = _browser(tmp_path)
        fake_pw = MagicMock()

        with patch("reverse_api.browser.sync_playwright") as sp, patch.object(
            browser, "_start_with_real_chrome", side_effect=RuntimeError("bad URL")
        ):
            sp.return_value.start.return_value = fake_pw
            with pytest.raises(RuntimeError, match="bad URL"):
                browser.start(start_url="https://example.com")

        fake_pw.stop.assert_called_once()
        assert browser._playwright is None

import io
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from quickplay import QuickPlay


class _Response(io.BytesIO):
    def __init__(self, data, headers, url, status=200, timeout_at_end=False):
        super().__init__(data)
        self.headers = headers
        self.url = url
        self.status = status
        self.timeout_at_end = timeout_at_end

    def geturl(self):
        return self.url

    def read(self, size=-1):
        if self.timeout_at_end and self.tell() == len(self.getbuffer()):
            raise TimeoutError("The read operation timed out")
        return super().read(size)


class _CancelEvent:
    def is_set(self):
        return False

    def wait(self, _seconds):
        return False


class DownloadTimeoutTest(unittest.TestCase):
    def test_timeout_reconnects_and_resumes_partial_zip(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("game.txt", b"game data" * 100)
        content = archive.getvalue()
        midpoint = len(content) // 2
        url = "https://example.invalid/Game.zip"
        headers = {"Content-Length": str(len(content)), "ETag": '"v1"',
                   "Content-Disposition": 'attachment; filename="Game.zip"'}
        calls = []

        def open_response(request, timeout):
            calls.append(request.get_header("Range"))
            if request.get_header("Range"):
                return _Response(content[midpoint:], {
                    "Content-Length": str(len(content) - midpoint),
                    "Content-Range": f"bytes {midpoint}-{len(content)-1}/{len(content)}",
                }, url, 206)
            if len(calls) == 1:
                return _Response(content[:midpoint], headers, url, timeout_at_end=True)
            return _Response(content, headers, url)

        app = QuickPlay.__new__(QuickPlay)
        events = []
        app._emit = lambda kind, value: events.append((kind, value))
        app.cancel_event = _CancelEvent()
        app.pause_event = threading.Event()

        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            folder = Path(temporary)
            with patch("quickplay.urllib.request.urlopen", side_effect=open_response):
                app._download_worker(url, "Game", folder, False)
            self.assertEqual((folder / "Game.zip").read_bytes(), content)
            self.assertFalse((folder / "Game.zip.part").exists())
            self.assertIn(f"bytes={midpoint}-", calls)
            self.assertIn(("done", "Download complete"), events)


if __name__ == "__main__":
    unittest.main()

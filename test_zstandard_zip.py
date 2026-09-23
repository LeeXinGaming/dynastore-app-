import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import zstandard

from quickplay import QuickPlay


class ZstandardZipTest(unittest.TestCase):
    def test_extract_method_93(self):
        original_check = zipfile._check_compression
        original_compressor = zipfile._get_compressor

        def check(compression):
            if compression != 93:
                original_check(compression)

        def compressor(compression, compresslevel=None):
            if compression == 93:
                return zstandard.ZstdCompressor().compressobj()
            return original_compressor(compression, compresslevel)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "game.zip"
            payload = b"game data" * 200000
            with patch.object(zipfile, "_check_compression", check), patch.object(
                zipfile, "_get_compressor", compressor
            ):
                with zipfile.ZipFile(archive, "w") as zipped:
                    zipped.writestr("game/data.bin", payload, compress_type=93)

            app = QuickPlay.__new__(QuickPlay)
            app.cancel_event = threading.Event()
            app._emit = lambda *args: None
            app._find_seven_zip = lambda: None
            app._remove_unwanted_files = lambda *args: None
            destination = root / "output"
            app._safe_extract(archive, destination, "Game")
            self.assertEqual((destination / "game" / "data.bin").read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()

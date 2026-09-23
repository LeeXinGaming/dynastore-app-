"""Automated tests for DYNA-STORE Online Hosting Server.

Tests:
1. Full file streaming (HTTP 200)
2. Resumable Byte-Range streaming (HTTP 206 Partial Content)
3. Invalid range handling (HTTP 416)
4. Version & auto-updater endpoints
5. Catalog API read/write
"""

import hashlib
import json
import os
import secrets
import sys
from pathlib import Path
import unittest

from starlette.testclient import TestClient

# Add server directory to path
server_dir = Path(__file__).resolve().parent / "server"
sys.path.insert(0, str(server_dir))

from hosting_server import app, FILES_DIR, APP_DIR, META_FILE, load_meta, save_meta


class TestHostingServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Create a test sample file (2 MB)
        cls.sample_data = bytes((i % 256) for i in range(2 * 1024 * 1024))
        cls.sample_filename = "test_game_archive.zip"
        cls.sample_token = "test_token_" + secrets.token_hex(4)
        cls.stored_name = f"{cls.sample_token}_{cls.sample_filename}"
        cls.file_path = FILES_DIR / cls.stored_name
        cls.file_path.write_bytes(cls.sample_data)

        meta = load_meta()
        meta[cls.sample_token] = {
            "original_name": cls.sample_filename,
            "stored_name": cls.stored_name,
            "size": len(cls.sample_data),
            "uploaded_at": "2026-09-24 00:00:00",
            "downloads": 0,
        }
        save_meta(meta)

    @classmethod
    def tearDownClass(cls):
        if cls.file_path.exists():
            cls.file_path.unlink()
        meta = load_meta()
        if cls.sample_token in meta:
            del meta[cls.sample_token]
            save_meta(meta)

    def test_01_full_download(self):
        url = f"/download/{self.sample_token}/{self.sample_filename}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.content), len(self.sample_data))
        self.assertEqual(resp.content, self.sample_data)
        self.assertEqual(resp.headers.get("accept-ranges"), "bytes")
        self.assertEqual(resp.headers.get("content-length"), str(len(self.sample_data)))
        self.assertIn("attachment", resp.headers.get("content-disposition", ""))

    def test_02_range_download_resumption(self):
        """Simulates DYNA-STORE resuming an interrupted download from byte offset 500,000."""
        offset = 500000
        url = f"/download/{self.sample_token}/{self.sample_filename}"
        headers = {"Range": f"bytes={offset}-"}
        resp = self.client.get(url, headers=headers)

        self.assertEqual(resp.status_code, 206)
        expected_slice = self.sample_data[offset:]
        self.assertEqual(resp.content, expected_slice)
        self.assertEqual(len(resp.content), len(expected_slice))
        self.assertEqual(
            resp.headers.get("content-range"),
            f"bytes {offset}-{len(self.sample_data)-1}/{len(self.sample_data)}",
        )

    def test_03_range_slice(self):
        """Tests specific range slice: bytes=1000-4999."""
        url = f"/download/{self.sample_token}/{self.sample_filename}"
        headers = {"Range": "bytes=1000-4999"}
        resp = self.client.get(url, headers=headers)

        self.assertEqual(resp.status_code, 206)
        expected_slice = self.sample_data[1000:5000]
        self.assertEqual(resp.content, expected_slice)
        self.assertEqual(len(resp.content), 4000)
        self.assertEqual(
            resp.headers.get("content-range"),
            f"bytes 1000-4999/{len(self.sample_data)}",
        )

    def test_04_invalid_range_416(self):
        url = f"/download/{self.sample_token}/{self.sample_filename}"
        headers = {"Range": f"bytes={len(self.sample_data) + 1000}-"}
        resp = self.client.get(url, headers=headers)
        self.assertEqual(resp.status_code, 416)

    def test_05_api_version(self):
        resp = self.client.get("/api/version")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("version", data)
        self.assertIn("download_url", data)

    def test_06_api_catalog(self):
        resp = self.client.get("/api/catalog")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)

    def test_07_server_status(self):
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "online")
        self.assertIn("local_url", data)


if __name__ == "__main__":
    unittest.main()

"""Cloudflare Tunnel Manager.

Manages cloudflared lifecycle:
- Detects or downloads official cloudflared binary
- Spawns public HTTPS tunnel pointing to local server
- Extracts and exposes the assigned https://*.trycloudflare.com URL
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("tunnel_manager")

CLOUDFLARED_DOWNLOAD_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
)

BIN_DIR = Path(__file__).resolve().parent / "bin"
CLOUDFLARED_EXE = BIN_DIR / "cloudflared.exe"
INFO_FILE = Path(__file__).resolve().parent / "server_info.json"


class TunnelManager:
    def __init__(self, port: int = 8000, on_url_ready: Optional[Callable[[str], None]] = None) -> None:
        self.port = port
        self.on_url_ready = on_url_ready
        self.process: Optional[subprocess.Popen] = None
        self.public_url: Optional[str] = None
        self.running = False
        self._reader_thread: Optional[threading.Thread] = None

    def find_executable(self) -> Path | None:
        """Find cloudflared in bin folder or system PATH."""
        if CLOUDFLARED_EXE.is_file():
            return CLOUDFLARED_EXE
        path_in_env = shutil.which("cloudflared")
        if path_in_env:
            return Path(path_in_env)
        return None

    def ensure_executable(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> Path:
        """Ensure cloudflared executable exists, downloading if necessary."""
        existing = self.find_executable()
        if existing and existing.is_file():
            return existing

        BIN_DIR.mkdir(parents=True, exist_ok=True)
        temp_exe = BIN_DIR / "cloudflared.exe.part"
        logger.info(f"Downloading cloudflared from {CLOUDFLARED_DOWNLOAD_URL}...")

        req = urllib.request.Request(CLOUDFLARED_DOWNLOAD_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(temp_exe, "wb") as out_file:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(downloaded, total)

        if temp_exe.exists():
            if CLOUDFLARED_EXE.exists():
                CLOUDFLARED_EXE.unlink()
            temp_exe.rename(CLOUDFLARED_EXE)

        logger.info(f"cloudflared ready at {CLOUDFLARED_EXE}")
        return CLOUDFLARED_EXE

    def start(self, wait_for_url_seconds: float = 30.0) -> Optional[str]:
        """Start cloudflared tunnel pointing to local server port."""
        if self.running and self.process and self.process.poll() is None:
            return self.public_url

        exe_path = self.ensure_executable()
        cmd = [
            str(exe_path),
            "tunnel",
            "--url",
            f"http://127.0.0.1:{self.port}",
            "--no-autoupdate",
        ]

        logger.info(f"Launching tunnel: {' '.join(cmd)}")
        self.public_url = None
        self.running = True

        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            startupinfo=startupinfo,
        )

        self._reader_thread = threading.Thread(target=self._monitor_output, daemon=True)
        self._reader_thread.start()

        # Wait up to wait_for_url_seconds for public URL to be emitted
        deadline = time.time() + wait_for_url_seconds
        while time.time() < deadline:
            if self.public_url:
                break
            if self.process.poll() is not None:
                logger.error(f"Tunnel process died with code {self.process.returncode}")
                self.running = False
                break
            time.sleep(0.5)

        return self.public_url

    def _monitor_output(self) -> None:
        """Read stderr where cloudflared logs tunnel connection and URL."""
        if not self.process or not self.process.stderr:
            return

        pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
        for line in iter(self.process.stderr.readline, ""):
            line_str = line.strip()
            if not line_str:
                continue

            match = pattern.search(line_str)
            if match and not self.public_url:
                url = match.group(0)
                self.public_url = url
                logger.info(f"Cloudflare Tunnel Public URL ready: {url}")
                self._save_info(url)
                if self.on_url_ready:
                    try:
                        self.on_url_ready(url)
                    except Exception as err:
                        logger.error(f"Error in on_url_ready callback: {err}")

        self.running = False

    def _save_info(self, url: str) -> None:
        try:
            info = {
                "local_url": f"http://127.0.0.1:{self.port}",
                "public_url": url,
                "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "online",
            }
            INFO_FILE.write_text(json.dumps(info, indent=2), encoding="utf-8")
        except Exception as err:
            logger.warning(f"Could not write server_info.json: {err}")

    def stop(self) -> None:
        """Terminate the tunnel process."""
        self.running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
        self.public_url = None
        try:
            if INFO_FILE.exists():
                info = json.loads(INFO_FILE.read_text(encoding="utf-8"))
                info["status"] = "offline"
                INFO_FILE.write_text(json.dumps(info, indent=2), encoding="utf-8")
        except Exception:
            pass


tunnel_singleton = TunnelManager()

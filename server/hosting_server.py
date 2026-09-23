"""DYNA-STORE High-Performance Online Hosting Server.

Features:
- Resumable Range downloads (HTTP 206 Partial Content, bytes=start-end)
- Fast streaming chunk transfer for large .exe, .zip, and game archives
- Cloudflare Tunnel integration (auto-public HTTPS URL)
- DYNA-STORE.exe distribution and version/update management
- Dynamic Game Catalog API (synchronized with .quickplay_catalog.json)
- Web Admin Dashboard with drag-and-drop file upload
"""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import os
import re
import secrets
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Generator, Optional

from fastapi import FastAPI, File, Form, HTTPException, Header, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hosting_server")

ROOT_DIR = Path(__file__).resolve().parent.parent
SERVER_DIR = Path(__file__).resolve().parent
STORAGE_DIR = SERVER_DIR / "storage"
FILES_DIR = STORAGE_DIR / "files"
APP_DIR = STORAGE_DIR / "app"
META_FILE = STORAGE_DIR / "meta.json"
APP_META_FILE = STORAGE_DIR / "app_version.json"
CATALOG_FILE = ROOT_DIR / ".quickplay_catalog.json"
TEMPLATES_DIR = SERVER_DIR / "templates"

# Ensure directories exist
FILES_DIR.mkdir(parents=True, exist_ok=True)
APP_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Import tunnel manager
from tunnel_manager import tunnel_singleton

app = FastAPI(title="DYNA-STORE Online Hosting Server", version="1.0.0")

# Enable CORS for all clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_meta() -> dict[str, dict]:
    if not META_FILE.exists():
        return {}
    try:
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_meta(data: dict[str, dict]) -> None:
    META_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_app_meta() -> dict:
    default_meta = {
        "version": "1.0.0",
        "name": "DYNA-STORE",
        "filename": "DYNA-STORE.exe",
        "changelog": "Initial online hosting release.",
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "size": 0,
        "sha256": "",
    }
    if not APP_META_FILE.exists():
        # Check if an existing build exists in dist/
        dist_exe = ROOT_DIR / "dist" / "DYNA-STORE TEST.exe"
        if dist_exe.is_file():
            target = APP_DIR / "DYNA-STORE.exe"
            if not target.is_file():
                try:
                    shutil.copy2(dist_exe, target)
                    stat = target.stat()
                    default_meta["size"] = stat.st_size
                except Exception as err:
                    logger.warning(f"Could not copy initial build: {err}")
        APP_META_FILE.write_text(json.dumps(default_meta, indent=2), encoding="utf-8")
        return default_meta
    try:
        return json.loads(APP_META_FILE.read_text(encoding="utf-8"))
    except Exception:
        return default_meta


def save_app_meta(data: dict) -> None:
    APP_META_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def calculate_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(2 * 1024 * 1024):
            sha.update(chunk)
    return sha.hexdigest()


def stream_file_range(file_path: Path, start: int, end: int, chunk_size: int = 1024 * 1024) -> Generator[bytes, None, None]:
    """Yield file slices efficiently without memory overhead."""
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            bytes_to_read = min(remaining, chunk_size)
            chunk = f.read(bytes_to_read)
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def build_streaming_response(
    file_path: Path,
    filename: str,
    range_header: Optional[str] = None,
    media_type: Optional[str] = None,
) -> StreamingResponse:
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    file_size = file_path.stat().st_size
    mtime = file_path.stat().st_mtime
    etag = f'"{hashlib.md5(f"{file_size}-{mtime}".encode()).hexdigest()}"'
    
    if not media_type:
        mime, _ = mimetypes.guess_type(filename)
        media_type = mime or "application/octet-stream"

    headers = {
        "Accept-Ranges": "bytes",
        "ETag": etag,
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges, Content-Length, Content-Disposition, ETag",
    }

    # Handle HTTP Byte Range Requests
    if range_header and range_header.startswith("bytes="):
        range_val = range_header.replace("bytes=", "").strip()
        parts = range_val.split("-")
        try:
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
            if start >= file_size or end >= file_size or start > end:
                raise HTTPException(
                    status_code=416,
                    detail="Requested Range Not Satisfiable",
                    headers={"Content-Range": f"bytes */{file_size}"},
                )
            
            content_length = end - start + 1
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(content_length)

            return StreamingResponse(
                stream_file_range(file_path, start, end),
                status_code=206,
                headers=headers,
                media_type=media_type,
            )
        except ValueError:
            pass  # Fall back to full content

    # Full content response
    headers["Content-Length"] = str(file_size)
    return StreamingResponse(
        stream_file_range(file_path, 0, file_size - 1),
        status_code=200,
        headers=headers,
        media_type=media_type,
    )


# -------------------------------------------------------------
# Endpoints: File Downloads (Range-capable)
# IMPORTANT: Specific routes MUST be registered before generic
# wildcard routes so FastAPI matches them first.
# -------------------------------------------------------------

@app.get("/download/app/latest")
async def download_app_latest(range: Optional[str] = Header(None)):
    """Direct download for the latest DYNA-STORE.exe installer/executable."""
    app_meta = load_app_meta()
    target = APP_DIR / app_meta.get("filename", "DYNA-STORE.exe")
    if not target.is_file():
        # Fallback: find any .exe in APP_DIR
        exes = list(APP_DIR.glob("*.exe"))
        if exes:
            target = sorted(exes, key=lambda f: f.stat().st_mtime, reverse=True)[0]
        else:
            raise HTTPException(status_code=404, detail="DYNA-STORE.exe has not been uploaded yet. Please build and deploy the executable first.")
    return build_streaming_response(target, target.name, range_header=range)


@app.get("/download/direct/{filename}")
async def download_file_direct(filename: str, range: Optional[str] = Header(None)):
    """Direct download link using only filename (no token needed)."""
    target = FILES_DIR / filename
    if not target.is_file():
        # Search case-insensitively
        for f in FILES_DIR.iterdir():
            if f.name.casefold() == filename.casefold():
                target = f
                break
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")
    return build_streaming_response(target, target.name, range_header=range)


@app.get("/download/{token}/{filename}")
async def download_file_by_token(token: str, filename: str, request: Request, range: Optional[str] = Header(None)):
    """Primary download endpoint matching the token/filename format used in the catalog."""
    meta = load_meta()

    # 1. Lookup by token from metadata index
    target_file = None
    real_filename = filename
    if token in meta:
        file_info = meta[token]
        candidate = FILES_DIR / file_info.get("stored_name", "")
        if candidate.is_file():
            target_file = candidate
            real_filename = file_info.get("original_name", filename)
            meta[token]["downloads"] = meta[token].get("downloads", 0) + 1
            save_meta(meta)

    # 2. Fallback: scan files directory for matching name or token prefix
    if not target_file:
        for f in FILES_DIR.iterdir():
            if f.name.casefold() == filename.casefold() or f.name.startswith(f"{token}_"):
                target_file = f
                real_filename = filename
                break

    if not target_file or not target_file.is_file():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found. Upload it via the Admin Dashboard first.")

    return build_streaming_response(target_file, real_filename, range_header=range)


# -------------------------------------------------------------
# Endpoints: API & Version Management
# -------------------------------------------------------------

@app.get("/api/version")
async def get_app_version():
    """Return latest DYNA-STORE application version for client auto-update check."""
    meta = load_app_meta()
    public_url = tunnel_singleton.public_url or "http://127.0.0.1:8000"
    target = APP_DIR / meta.get("filename", "DYNA-STORE.exe")
    size = target.stat().st_size if target.is_file() else 0
    return {
        "version": meta.get("version", "1.0.0"),
        "name": meta.get("name", "DYNA-STORE"),
        "filename": meta.get("filename", "DYNA-STORE.exe"),
        "size": size,
        "sha256": meta.get("sha256", ""),
        "changelog": meta.get("changelog", ""),
        "updated_at": meta.get("updated_at", ""),
        "download_url": f"{public_url}/download/app/latest",
        "local_download_url": "http://127.0.0.1:8000/download/app/latest",
    }


@app.get("/api/catalog")
async def get_catalog():
    """Serve the active game catalog to DYNA-STORE clients."""
    if not CATALOG_FILE.exists():
        return []
    try:
        catalog_data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        return catalog_data
    except Exception as err:
        logger.error(f"Error loading catalog: {err}")
        return []


@app.post("/api/catalog")
async def add_or_update_catalog_game(game: dict):
    """Add or update a game entry in .quickplay_catalog.json."""
    if not isinstance(game, dict) or not game.get("name"):
        raise HTTPException(status_code=400, detail="Invalid game data")

    catalog = []
    if CATALOG_FILE.exists():
        try:
            catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            catalog = []

    # Update if exists, else append
    existing_index = next(
        (i for i, item in enumerate(catalog) if item.get("name", "").strip().casefold() == game["name"].strip().casefold()),
        -1,
    )
    if existing_index >= 0:
        catalog[existing_index].update(game)
    else:
        catalog.append(game)

    CATALOG_FILE.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"success": True, "message": f"Game '{game['name']}' saved to catalog.", "count": len(catalog)}


@app.get("/api/files")
async def list_files():
    """List all hosted game files with their direct links."""
    meta = load_meta()
    public_url = tunnel_singleton.public_url or "http://127.0.0.1:8000"
    files_list = []
    
    for token, info in meta.items():
        stored_path = FILES_DIR / info.get("stored_name", "")
        if stored_path.is_file():
            size = stored_path.stat().st_size
            files_list.append({
                "token": token,
                "name": info.get("original_name", stored_path.name),
                "size": size,
                "formatted_size": f"{size / (1024 * 1024):.2f} MB" if size < 1024**3 else f"{size / (1024**3):.2f} GB",
                "uploaded_at": info.get("uploaded_at", ""),
                "downloads": info.get("downloads", 0),
                "download_url": f"{public_url}/download/{token}/{info.get('original_name', stored_path.name)}",
                "local_url": f"http://127.0.0.1:8000/download/{token}/{info.get('original_name', stored_path.name)}",
            })
            
    # Also list untracked files in files/ directory
    tracked_stored_names = {info.get("stored_name") for info in meta.values()}
    for f in FILES_DIR.iterdir():
        if f.is_file() and f.name not in tracked_stored_names:
            token = secrets.token_urlsafe(16)
            size = f.stat().st_size
            meta[token] = {
                "original_name": f.name,
                "stored_name": f.name,
                "size": size,
                "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "downloads": 0,
            }
            save_meta(meta)
            files_list.append({
                "token": token,
                "name": f.name,
                "size": size,
                "formatted_size": f"{size / (1024 * 1024):.2f} MB" if size < 1024**3 else f"{size / (1024**3):.2f} GB",
                "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "downloads": 0,
                "download_url": f"{public_url}/download/{token}/{f.name}",
                "local_url": f"http://127.0.0.1:8000/download/{token}/{f.name}",
            })

    return files_list


@app.post("/api/upload")
async def upload_game_file(file: UploadFile = File(...)):
    """Upload a game file (.exe, .zip, .rar, .7z) with streaming chunk writes."""
    token = secrets.token_urlsafe(18)
    filename = Path(file.filename or "download.bin").name
    stored_name = f"{token}_{filename}"
    target_path = FILES_DIR / stored_name

    total_bytes = 0
    with open(target_path, "wb") as out_file:
        while chunk := await file.read(4 * 1024 * 1024):
            out_file.write(chunk)
            total_bytes += len(chunk)

    meta = load_meta()
    meta[token] = {
        "original_name": filename,
        "stored_name": stored_name,
        "size": total_bytes,
        "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "downloads": 0,
    }
    save_meta(meta)

    public_url = tunnel_singleton.public_url or "http://127.0.0.1:8000"
    download_url = f"{public_url}/download/{token}/{filename}"

    return {
        "success": True,
        "token": token,
        "filename": filename,
        "size": total_bytes,
        "download_url": download_url,
        "local_url": f"http://127.0.0.1:8000/download/{token}/{filename}",
    }


@app.post("/api/app/upload")
async def upload_app_executable(
    file: UploadFile = File(...),
    version: str = Form("1.0.0"),
    changelog: str = Form("New release update"),
):
    """Upload a new build of DYNA-STORE.exe and update version metadata."""
    filename = "DYNA-STORE.exe"
    target_path = APP_DIR / filename

    total_bytes = 0
    sha = hashlib.sha256()
    with open(target_path, "wb") as out_file:
        while chunk := await file.read(4 * 1024 * 1024):
            out_file.write(chunk)
            sha.update(chunk)
            total_bytes += len(chunk)

    app_meta = {
        "version": version.strip(),
        "name": "DYNA-STORE",
        "filename": filename,
        "changelog": changelog.strip(),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "size": total_bytes,
        "sha256": sha.hexdigest(),
    }
    save_app_meta(app_meta)

    public_url = tunnel_singleton.public_url or "http://127.0.0.1:8000"
    return {
        "success": True,
        "version": version,
        "size": total_bytes,
        "download_url": f"{public_url}/download/app/latest",
    }


@app.delete("/api/files/{token}")
async def delete_hosted_file(token: str):
    """Delete a hosted game file."""
    meta = load_meta()
    if token not in meta:
        raise HTTPException(status_code=404, detail="File token not found")

    stored_name = meta[token].get("stored_name", "")
    target = FILES_DIR / stored_name
    if target.is_file():
        try:
            target.unlink()
        except Exception as err:
            logger.error(f"Error removing file: {err}")

    del meta[token]
    save_meta(meta)
    return {"success": True, "message": "File deleted"}


@app.get("/api/status")
async def server_status():
    """Return server status and public Cloudflare tunnel info."""
    meta = load_meta()
    total_size = sum(f.stat().st_size for f in FILES_DIR.iterdir() if f.is_file())
    app_meta = load_app_meta()
    
    return {
        "status": "online",
        "local_url": f"http://127.0.0.1:{tunnel_singleton.port}",
        "public_url": tunnel_singleton.public_url or "Starting tunnel...",
        "files_count": len(meta),
        "total_storage_bytes": total_size,
        "formatted_storage": f"{total_size / (1024 * 1024):.2f} MB" if total_size < 1024**3 else f"{total_size / (1024**3):.2f} GB",
        "app_version": app_meta.get("version", "1.0.0"),
    }


# -------------------------------------------------------------
# Web Admin Dashboard
# -------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def admin_dashboard():
    """Serve the Web Admin Dashboard."""
    dashboard_file = TEMPLATES_DIR / "dashboard.html"
    if dashboard_file.is_file():
        return HTMLResponse(content=dashboard_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>DYNA-STORE Server Running</h1><p>Dashboard template loading...</p>")


def run_server(port: int = 8000, start_tunnel: bool = True):
    """Launch the server and optionally initialize Cloudflare Tunnel."""
    tunnel_singleton.port = port

    if start_tunnel:
        def on_url_ready(url: str):
            sep = "=" * 65
            print(f"\n{sep}")
            print("DYNA-STORE ONLINE HOSTING SERVER IS LIVE!")
            print(f"[PUBLIC]  HTTPS URL : {url}")
            print(f"[LOCAL]   Admin URL : http://127.0.0.1:{port}")
            print(f"[APP DL]  Download  : {url}/download/app/latest")
            print(f"[CATALOG] API       : {url}/api/catalog")
            print(f"{sep}\n")

        tunnel_singleton.on_url_ready = on_url_ready
        threading.Thread(target=tunnel_singleton.start, daemon=True).start()

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    port_arg = 8000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port_arg = int(sys.argv[1])
    run_server(port=port_arg)

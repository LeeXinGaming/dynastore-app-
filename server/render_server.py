"""DYNA-STORE Render-optimized Hosting Server.

This is the cloud version of the hosting server designed for Render.com:
- No Cloudflare Tunnel (Render provides its own free HTTPS URL)
- No emoji in console output (avoids encoding errors)
- Reads RENDER_EXTERNAL_URL env var to generate correct download links
- Supports Render Disk for persistent file storage
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import secrets
import shutil
import time
from pathlib import Path
from typing import Generator, Optional

from fastapi import FastAPI, File, Form, HTTPException, Header, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import uvicorn

# ── Directory setup ──────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent

# On Render, use the mounted persistent disk; locally use server/storage/
RENDER_DISK = Path("/opt/render/project/src/storage")
STORAGE_DIR = RENDER_DISK if RENDER_DISK.exists() else (ROOT_DIR / "storage")
FILES_DIR = STORAGE_DIR / "files"
APP_DIR = STORAGE_DIR / "app"
META_FILE = STORAGE_DIR / "meta.json"
APP_META_FILE = STORAGE_DIR / "app_version.json"
CATALOG_FILE = ROOT_DIR.parent / ".quickplay_catalog.json"
TEMPLATES_DIR = ROOT_DIR / "templates"

FILES_DIR.mkdir(parents=True, exist_ok=True)
APP_DIR.mkdir(parents=True, exist_ok=True)

# ── Public URL (from Render environment, or local fallback) ──────
def get_public_base_url() -> str:
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    if render_url:
        return render_url
    port = os.environ.get("PORT", "8000")
    return f"http://127.0.0.1:{port}"

# ── FastAPI app ───────────────────────────────────────────────────
app = FastAPI(
    title="DYNA-STORE Online Hosting Server",
    description="Game file distribution, catalog API, and app update server",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_meta() -> dict:
    if not META_FILE.exists():
        return {}
    try:
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_meta(data: dict) -> None:
    META_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_app_meta() -> dict:
    default = {
        "version": "2.0.0",
        "name": "DYNA-STORE",
        "filename": "DYNA-STORE.exe",
        "changelog": "Online hosting release",
        "updated_at": time.strftime("%Y-%m-%d"),
        "size": 0,
        "sha256": "",
    }
    if not APP_META_FILE.exists():
        APP_META_FILE.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    try:
        return json.loads(APP_META_FILE.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_app_meta(data: dict) -> None:
    APP_META_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def calculate_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(2 * 1024 * 1024):
            sha.update(chunk)
    return sha.hexdigest()


def stream_file_range(path: Path, start: int, end: int, chunk=1024 * 1024) -> Generator[bytes, None, None]:
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            data = f.read(min(remaining, chunk))
            if not data:
                break
            remaining -= len(data)
            yield data


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

    if range_header and range_header.startswith("bytes="):
        parts = range_header.replace("bytes=", "").split("-")
        try:
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
            if start >= file_size or end >= file_size or start > end:
                raise HTTPException(status_code=416, detail="Range Not Satisfiable",
                                    headers={"Content-Range": f"bytes */{file_size}"})
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(end - start + 1)
            return StreamingResponse(stream_file_range(file_path, start, end),
                                     status_code=206, headers=headers, media_type=media_type)
        except ValueError:
            pass

    headers["Content-Length"] = str(file_size)
    return StreamingResponse(stream_file_range(file_path, 0, file_size - 1),
                             status_code=200, headers=headers, media_type=media_type)


# ─────────────────────────────────────────────────────────────────
# ROUTES  (specific before generic — critical for correct matching)
# ─────────────────────────────────────────────────────────────────

@app.get("/download/app/latest")
async def download_app_latest(range: Optional[str] = Header(None)):
    """Download the latest DYNA-STORE.exe application."""
    meta = load_app_meta()
    target = APP_DIR / meta.get("filename", "DYNA-STORE.exe")
    if not target.is_file():
        exes = sorted(APP_DIR.glob("*.exe"), key=lambda f: f.stat().st_mtime, reverse=True)
        if exes:
            target = exes[0]
        else:
            raise HTTPException(
                status_code=404,
                detail="DYNA-STORE.exe has not been uploaded yet. Use POST /api/app/upload to deploy the executable."
            )
    return build_streaming_response(target, target.name, range_header=range)


@app.get("/download/direct/{filename}")
async def download_file_direct(filename: str, range: Optional[str] = Header(None)):
    """Download a hosted file by filename directly."""
    target = FILES_DIR / filename
    if not target.is_file():
        for f in FILES_DIR.iterdir():
            if f.name.casefold() == filename.casefold():
                target = f
                break
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")
    return build_streaming_response(target, target.name, range_header=range)


@app.get("/download/{token}/{filename}")
async def download_file_by_token(token: str, filename: str, range: Optional[str] = Header(None)):
    """Download a hosted game file using its token and filename."""
    meta = load_meta()
    target_file = None
    real_filename = filename

    if token in meta:
        info = meta[token]
        candidate = FILES_DIR / info.get("stored_name", "")
        if candidate.is_file():
            target_file = candidate
            real_filename = info.get("original_name", filename)
            meta[token]["downloads"] = meta[token].get("downloads", 0) + 1
            save_meta(meta)

    if not target_file:
        for f in FILES_DIR.iterdir():
            if f.name.casefold() == filename.casefold() or f.name.startswith(f"{token}_"):
                target_file = f
                real_filename = filename
                break

    if not target_file or not target_file.is_file():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found. Upload it via the Admin Dashboard.")

    return build_streaming_response(target_file, real_filename, range_header=range)


# ── API ───────────────────────────────────────────────────────────

@app.get("/api/status")
async def server_status():
    meta = load_meta()
    app_meta = load_app_meta()
    total = sum(f.stat().st_size for f in FILES_DIR.iterdir() if f.is_file())
    public_url = get_public_base_url()
    return {
        "status": "online",
        "public_url": public_url,
        "local_url": public_url,
        "files_count": len(meta),
        "total_storage_bytes": total,
        "formatted_storage": f"{total/(1024**2):.2f} MB" if total < 1024**3 else f"{total/(1024**3):.2f} GB",
        "app_version": app_meta.get("version", "2.0.0"),
    }


@app.get("/api/version")
async def get_app_version():
    meta = load_app_meta()
    public_url = get_public_base_url()
    target = APP_DIR / meta.get("filename", "DYNA-STORE.exe")
    size = target.stat().st_size if target.is_file() else 0
    return {
        "version": meta.get("version", "2.0.0"),
        "name": meta.get("name", "DYNA-STORE"),
        "filename": meta.get("filename", "DYNA-STORE.exe"),
        "size": size,
        "sha256": meta.get("sha256", ""),
        "changelog": meta.get("changelog", ""),
        "updated_at": meta.get("updated_at", ""),
        "download_url": f"{public_url}/download/app/latest",
    }


@app.get("/api/catalog")
async def get_catalog():
    if not CATALOG_FILE.exists():
        return []
    try:
        return json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


@app.post("/api/catalog")
async def upsert_catalog_game(game: dict):
    if not isinstance(game, dict) or not game.get("name"):
        raise HTTPException(status_code=400, detail="Invalid game data")
    catalog = []
    if CATALOG_FILE.exists():
        try:
            catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    idx = next((i for i, item in enumerate(catalog)
                 if item.get("name", "").casefold() == game["name"].casefold()), -1)
    if idx >= 0:
        catalog[idx].update(game)
    else:
        catalog.append(game)
    CATALOG_FILE.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"success": True, "count": len(catalog)}


@app.get("/api/files")
async def list_files():
    meta = load_meta()
    public_url = get_public_base_url()
    result = []
    for token, info in meta.items():
        path = FILES_DIR / info.get("stored_name", "")
        if path.is_file():
            sz = path.stat().st_size
            result.append({
                "token": token,
                "name": info.get("original_name", path.name),
                "size": sz,
                "formatted_size": f"{sz/(1024**2):.2f} MB" if sz < 1024**3 else f"{sz/(1024**3):.2f} GB",
                "uploaded_at": info.get("uploaded_at", ""),
                "downloads": info.get("downloads", 0),
                "download_url": f"{public_url}/download/{token}/{info.get('original_name', path.name)}",
            })
    for f in FILES_DIR.iterdir():
        tracked = {i.get("stored_name") for i in meta.values()}
        if f.is_file() and f.name not in tracked:
            token = secrets.token_urlsafe(16)
            sz = f.stat().st_size
            meta[token] = {"original_name": f.name, "stored_name": f.name,
                           "size": sz, "uploaded_at": time.strftime("%Y-%m-%d"), "downloads": 0}
            save_meta(meta)
            result.append({
                "token": token, "name": f.name, "size": sz,
                "formatted_size": f"{sz/(1024**2):.2f} MB",
                "uploaded_at": time.strftime("%Y-%m-%d"), "downloads": 0,
                "download_url": f"{public_url}/download/{token}/{f.name}",
            })
    return result


@app.post("/api/upload")
async def upload_game_file(file: UploadFile = File(...)):
    token = secrets.token_urlsafe(18)
    filename = Path(file.filename or "upload.bin").name
    stored_name = f"{token}_{filename}"
    target = FILES_DIR / stored_name
    total = 0
    with open(target, "wb") as out:
        while chunk := await file.read(4 * 1024 * 1024):
            out.write(chunk)
            total += len(chunk)
    meta = load_meta()
    meta[token] = {"original_name": filename, "stored_name": stored_name,
                   "size": total, "uploaded_at": time.strftime("%Y-%m-%d"), "downloads": 0}
    save_meta(meta)
    public_url = get_public_base_url()
    return {
        "success": True, "token": token, "filename": filename, "size": total,
        "download_url": f"{public_url}/download/{token}/{filename}",
    }


@app.post("/api/app/upload")
async def upload_app_exe(
    file: UploadFile = File(...),
    version: str = Form("2.0.0"),
    changelog: str = Form("New release"),
):
    filename = "DYNA-STORE.exe"
    target = APP_DIR / filename
    total = 0
    sha = hashlib.sha256()
    with open(target, "wb") as out:
        while chunk := await file.read(4 * 1024 * 1024):
            out.write(chunk)
            sha.update(chunk)
            total += len(chunk)
    save_app_meta({
        "version": version.strip(), "name": "DYNA-STORE", "filename": filename,
        "changelog": changelog.strip(), "updated_at": time.strftime("%Y-%m-%d"),
        "size": total, "sha256": sha.hexdigest(),
    })
    public_url = get_public_base_url()
    return {"success": True, "version": version, "size": total,
            "download_url": f"{public_url}/download/app/latest"}


@app.delete("/api/files/{token}")
async def delete_file(token: str):
    meta = load_meta()
    if token not in meta:
        raise HTTPException(status_code=404, detail="Token not found")
    target = FILES_DIR / meta[token].get("stored_name", "")
    if target.is_file():
        target.unlink()
    del meta[token]
    save_meta(meta)
    return {"success": True}


# ── Web Dashboard ─────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def admin_dashboard():
    dashboard = TEMPLATES_DIR / "dashboard.html"
    if dashboard.is_file():
        return HTMLResponse(content=dashboard.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>DYNA-STORE Server</h1><p>Dashboard loading...</p>")


@app.get("/favicon.ico")
async def favicon():
    raise HTTPException(status_code=204)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting DYNA-STORE server on port {port}")
    print(f"Public URL: {get_public_base_url()}")
    uvicorn.run(app, host="0.0.0.0", port=port)

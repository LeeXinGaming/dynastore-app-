# DYNA-STORE Complete System Guide

This system allows you to host game files (`.exe`, `.zip`, `.rar`), distribute the `DYNA-STORE.exe` client app, and synchronize your game catalog online via a free Cloudflare Tunnel.

---

## 1. Quick Start (All-in-One Launcher)

Double-click:
```
START_ALL_SYSTEMS.cmd
```
This automatically starts:
1. **The Online Hosting Server** (FastAPI on port 8000)
2. **The Cloudflare Tunnel** (Generates a free global public HTTPS link)
3. **The Web Admin Dashboard** (Opens in your web browser)
4. **The DYNA-STORE Application (.exe)** (Runs on your desktop)

---

## 2. System Architecture & URLs

| Component | Local URL / Path | Public Online URL | Purpose |
| :--- | :--- | :--- | :--- |
| **Web Dashboard** | `http://127.0.0.1:8000` | `https://*.trycloudflare.com` | Upload files, manage games, view links |
| **App Download** | `http://127.0.0.1:8000/download/app/latest` | `https://*.trycloudflare.com/download/app/latest` | Download latest `DYNA-STORE.exe` |
| **Game Catalog** | `http://127.0.0.1:8000/api/catalog` | `https://*.trycloudflare.com/api/catalog` | Live game catalog API |
| **App Updater** | `http://127.0.0.1:8000/api/version` | `https://*.trycloudflare.com/api/version` | Version check for client auto-updates |
| **Client App** | `dist/DYNA-STORE.exe` | — | The desktop game store & downloader |

---

## 3. How to Upload & Host Games Online

1. Open the Web Dashboard at `http://127.0.0.1:8000`.
2. Drag and drop any `.exe`, `.zip`, `.rar`, or `.7z` file into the upload zone.
3. Once uploaded:
   - Click **Copy Link** to share the direct download link.
   - Click **Add to Catalog** to instantly add the game to DYNA-STORE's online catalog.
4. All connected DYNA-STORE client apps will immediately see the newly added game!

---

## 4. Key Files & Folders

- **`START_ALL_SYSTEMS.cmd`**: One-click launcher to run everything together.
- **`dist/DYNA-STORE.exe`**: The compiled desktop application (177.8 MB).
- **`server/hosting_server.py`**: The resumable Range-download streaming backend.
- **`server/storage/files/`**: Where all uploaded game archives are stored.
- **`server/storage/app/`**: Stores the latest `DYNA-STORE.exe` build for user downloads.
- **`server/bin/cloudflared.exe`**: Cloudflare tunnel engine for free public HTTPS.
- **`.quickplay_catalog.json`**: The central game catalog.

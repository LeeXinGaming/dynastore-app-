from __future__ import annotations

import os
import json
import hashlib
import hmac
import base64
import contextlib
import queue
import re
import secrets
import ipaddress
import socket
import math
import io
import struct
import sys
import zlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import shutil
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
import webbrowser
import zipfile
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

from keyauth_client import KeyAuthClient, KeyAuthError

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageTk
except ImportError:
    build_deps = Path(__file__).with_name(".build-deps")
    if build_deps.is_dir():
        sys.path.insert(0, str(build_deps))
        try:
            from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageTk
        except ImportError:
            Image = ImageDraw = ImageEnhance = ImageFilter = ImageFont = ImageOps = ImageTk = None
    else:
        Image = ImageDraw = ImageEnhance = ImageFilter = ImageFont = ImageOps = ImageTk = None

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import zstandard
except ImportError:
    zstandard = None


class _LimitedReader(io.RawIOBase):
    def __init__(self, source, length: int) -> None:
        self.source = source
        self.remaining = length

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        if self.remaining <= 0:
            return 0
        data = self.source.read(min(len(buffer), self.remaining))
        count = len(data)
        buffer[:count] = data
        self.remaining -= count
        return count


APP_BG = "#111318"
PANEL_BG = "#1a1d24"
INPUT_BG = "#242832"
TEXT = "#f3f4f6"
MUTED = "#9ca3af"
ACCENT = "#f5a623"
GREEN = "#30d17c"
GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID",
    "",
)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8765/")
ADMIN_USERNAME = "dinacomputer0110"
COVER_IMAGE_WIDTH = 600
COVER_IMAGE_HEIGHT = 900
KHMER_TRANSLATIONS = {
    "Browse": "រុករក",
    "My Library": "បណ្ណាល័យរបស់ខ្ញុំ",
    "Downloads": "ការទាញយក",
    "Settings": "ការកំណត់",
    "Help": "ជំនួយ",
    "Admin": "អ្នកគ្រប់គ្រង",
    "Sign in with Google": "ចូលដោយប្រើ Google",
    "KeyAuth Login": "ចូល KeyAuth",
    "Settings saved successfully.": "បានរក្សាទុកការកំណត់ដោយជោគជ័យ។",
    "Catalog Server": "ម៉ាស៊ីនមេកាតាឡុក",
    "Choose which catalog to browse.": "ជ្រើសរើសកាតាឡុកសម្រាប់រុករក។",
    "Language": "ភាសា",
    "Choose the app display language.": "ជ្រើសរើសភាសាបង្ហាញរបស់កម្មវិធី។",
    "Download / Games Folder": "ថតទាញយក / ហ្គេម",
    "All downloads and extracted games go here.": "ឯកសារទាញយក និងហ្គេមទាំងអស់ត្រូវរក្សាទុកទីនេះ។",
    "Download Connections": "ចំនួនការតភ្ជាប់ទាញយក",
    "Parallel connection preference (1–64).": "កំណត់ចំនួនការតភ្ជាប់ស្របគ្នា (1–64)។",
    "Extract archives after download": "ពន្លាឯកសារបង្ហាប់បន្ទាប់ពីទាញយក",
    "Show download logs panel": "បង្ហាញផ្ទាំងកំណត់ត្រាទាញយក",
    "Disable announcement on startup": "បិទសេចក្តីជូនដំណឹងពេលចាប់ផ្ដើម",
    "Add download folder to Microsoft Defender exclusions (all Windows users)":
        "បន្ថែមថតទាញយកទៅបញ្ជីលើកលែង Microsoft Defender (អ្នកប្រើ Windows ទាំងអស់)",
    "Save Settings": "រក្សាទុកការកំណត់",
    "Help & Support": "ជំនួយ និងការគាំទ្រ",
    "Have a question or need help? Join our group or contact the admin.":
        "មានសំណួរ ឬត្រូវការជំនួយ? ចូលរួមក្រុម ឬទាក់ទងអ្នកគ្រប់គ្រង។",
    "Click a support card to open the official community link.":
        "ចុចកាតគាំទ្រដើម្បីបើកតំណសហគមន៍ផ្លូវការ។",
    "Display name": "ឈ្មោះបង្ហាញ",
    "Save folder": "ថតរក្សាទុក",
    "Browse...": "រកមើល...",
    "Browse": "រុករក",
    "Download": "ទាញយក",
    "Cancel": "បោះបង់",
    "Pause": "ផ្អាក",
    "Download Logs": "កំណត់ត្រាទាញយក",
    "Log out": "ចាកចេញ",
    "Save Game": "រក្សាទុកហ្គេម",
    "Delete Selected": "លុបធាតុដែលបានជ្រើស",
    "Upload Image": "បង្ហោះរូបភាព",
    "Admin Telegram": "Telegram អ្នកគ្រប់គ្រង",
}


class Cancelled(Exception):
    pass


class QuickPlay(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DYNA-STORE")
        self.geometry("1400x850")
        self.minsize(900, 600)
        self.configure(bg=APP_BG)
        logo_dir = Path(__file__).with_name("assets") / "logo"
        logo_path = logo_dir / "dyna-store-v1.png"
        self.app_logo = None
        try:
            self.app_logo = tk.PhotoImage(file=str(logo_path))
            self.app_logo_small = self.app_logo.subsample(20, 20)
            self.app_logo_medium = self.app_logo.subsample(10, 10)
            self.iconphoto(True, self.app_logo_medium, self.app_logo_small)
        except (OSError, tk.TclError):
            if sys.platform == "win32":
                try:
                    self.iconbitmap(str(logo_dir / "dyna-store-v1.ico"))
                except tk.TclError:
                    pass

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.pause_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.retry_archive: tuple[Path, Path, str] | None = None
        self.game_map_file = Path(__file__).with_name(".quickplay_games.json")
        self.video_map_file = Path(__file__).with_name(".quickplay_videos.json")
        self.youtube_map_file = Path(__file__).with_name(".quickplay_youtube.json")
        self.admin_file = Path(__file__).with_name(".quickplay_admin.json")
        self.catalog_file = Path(__file__).with_name(".quickplay_catalog.json")
        self.deleted_games_file = Path(__file__).with_name(".quickplay_deleted_games.json")
        self.google_config_file = Path(__file__).with_name(".quickplay_google_oauth.json")
        self.settings_file = Path(__file__).with_name(".quickplay_settings.json")
        saved_settings = self._load_settings()
        self.admin_authenticated = False
        self.game_executables = self._load_game_mappings()
        self.game_videos = self._load_json_mapping(self.video_map_file)
        self.youtube_links = self._load_json_mapping(self.youtube_map_file)
        self.game_download_links: dict[str, str] = {}
        self.game_cover_paths: dict[str, str] = {}
        self.deleted_games = self._load_deleted_games()

        self.url_var = tk.StringVar()
        self.name_var = tk.StringVar(value="Download")
        self.output_var = tk.StringVar(value=str(saved_settings.get(
            "download_folder", Path.home() / "Downloads" / "DYNA-STORE"
        )))
        self.extract_var = tk.BooleanVar(value=bool(saved_settings.get("extract_zip", True)))
        self.settings_server = tk.StringVar(value=str(saved_settings.get("catalog_server", "Server 1")))
        self.settings_server_url = tk.StringVar(value=str(saved_settings.get("online_server_url", "")))
        self.settings_language = tk.StringVar(value=str(saved_settings.get("language", "English")))
        self.settings_connections = tk.IntVar(value=int(saved_settings.get("connections", 8)))
        self.settings_show_logs = tk.BooleanVar(value=bool(saved_settings.get("show_logs", True)))
        self.settings_disable_announcements = tk.BooleanVar(
            value=bool(saved_settings.get("disable_announcements", False))
        )
        self.settings_defender_exclusion = tk.BooleanVar(
            value=bool(saved_settings.get("defender_exclusion", False))
        )
        self.status_var = tk.StringVar(value="No active downloads.")
        self.progress_var = tk.DoubleVar(value=0)
        self.data_progress_var = tk.DoubleVar(value=0)
        self.download_progress_var = tk.StringVar(value="0%  •  0.00 MB / -- MB")
        self.download_speed_var = tk.StringVar(value="0 bps")
        self.download_peak_var = tk.StringVar(value="0 bps")
        self.disk_speed_var = tk.StringVar(value="0 bps")
        self.download_amount_var = tk.StringVar(value="0.0 MB / -- MB")
        self.install_progress_var = tk.DoubleVar(value=0)
        self.install_percent_var = tk.StringVar(value="0%")
        self._peak_download_speed = 0.0
        self._installation_active = False
        self.google_user: dict[str, str] | None = None
        self.google_user_var = tk.StringVar(value="Not signed in")
        self.keyauth_client = KeyAuthClient("Dyna11's Application", "UviI76U4J9", "1.0")
        self.keyauth_user: dict[str, object] | None = None
        self.keyauth_user_var = tk.StringVar(value="KeyAuth: signed out")
        self.google_client_id = self._load_google_client_id()
        self.animation_phase = 0
        self.background_video_path = (
            Path(__file__).with_name("assets") / "video" / "dyna-store-background.mp4"
        )
        self.video_capture = None
        self.video_frame_image = None
        self.video_background_tick = 0
        self.video_source_fps = 30.0
        self.video_frame_step = 1
        self.youtube_stream_capture = None
        self.youtube_stream_playing = False
        self.youtube_stream_resolving = False
        self.youtube_cookie_browser: str | None = None

        self._configure_style()
        self._build_ui()
        self._start_background_video()
        self.after(80, self._drain_events)
        self.after(60, self._animate_ui)
        self.protocol("WM_DELETE_WINDOW", self._close_app)
        self.auth_gate_active = True
        self.after(180, lambda: self.show_keyauth_login(lock_app=True))
        self.after(1200, self._start_online_sync)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor=INPUT_BG, background=ACCENT, borderwidth=0)
        style.configure("Download.Horizontal.TProgressbar", troughcolor="#394351",
                        background="#58a4df", borderwidth=0)
        style.configure("Install.Horizontal.TProgressbar", troughcolor="#394351",
                        background="#63cd5a", borderwidth=0)
        style.configure("TCheckbutton", background=PANEL_BG, foreground=TEXT)
        style.map("TCheckbutton", background=[("active", PANEL_BG)], foreground=[("active", TEXT)])

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg="#121212", padx=14, pady=8)
        header.pack(fill="x")
        self.logo_label = tk.Label(header, text="DYNA-STORE", bg="#121212", fg="#FF2B00",
                                   font=("Segoe UI", 16, "bold"))
        self.logo_label.pack(side="left", padx=(0, 14))
        self.nav_buttons: dict[str, tk.Button] = {}
        for page in ("Browse", "My Library", "Downloads", "Settings", "Help", "Admin"):
            button = tk.Button(
                header, text=page, command=lambda p=page: self.navigate(p),
                bg="#121212", fg=MUTED, activebackground="#292929",
                activeforeground=TEXT, relief="flat", padx=12, pady=7,
                cursor="hand2", font=("Segoe UI", 10),
            )
            button.pack(side="left", padx=2)
            self.nav_buttons[page] = button
        self.keyauth_button = self._button(header, "KeyAuth Login", self.show_keyauth_login,
                                           "#6c4df6", "#ffffff")
        self.keyauth_button.pack(side="right", padx=(10, 0))
        tk.Label(header, textvariable=self.keyauth_user_var, bg="#121212", fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="right", padx=8)

        self.content = tk.Frame(self, bg=APP_BG)
        self.content.pack(fill="both", expand=True)
        self.views: dict[str, tk.Frame] = {}
        self._build_browse_view()
        self._build_game_detail_view()
        self._build_library_view()
        self._build_download_view()
        self._build_info_views()
        self._build_admin_view()
        self._apply_settings_ui()
        self._apply_language()
        self.animated_font_widgets = self._collect_animated_font_widgets(self)
        self._show_view("Browse")

    @staticmethod
    def _collect_animated_font_widgets(root: tk.Widget) -> list[tk.Widget]:
        widgets: list[tk.Widget] = []

        def visit(widget: tk.Widget) -> None:
            try:
                if "foreground" in widget.keys() and str(widget.cget("foreground")) == ACCENT:
                    widgets.append(widget)
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                visit(child)

        visit(root)
        return widgets

    def navigate(self, page: str) -> None:
        if getattr(self, "auth_gate_active", False):
            if self.grab_current() is None:
                self.show_keyauth_login(lock_app=True)
            return
        if page == "Admin" and not self.admin_authenticated:
            self.show_admin_login()
            return
        self._show_view(page)

    def google_sign_in(self) -> None:
        if self.google_user:
            self.google_user = None
            self.google_user_var.set("Not signed in")
            self.google_button.configure(text="Sign in with Google")
            self.status_var.set("Signed out")
            return
        if not self.google_client_id and not self.configure_google_oauth():
            return
        self.google_button.configure(state="disabled", text="Opening browser…")
        self.status_var.set("Waiting for Google sign-in…")
        threading.Thread(target=self._google_oauth_worker, daemon=True).start()

    def _load_google_client_id(self) -> str:
        if GOOGLE_CLIENT_ID:
            return GOOGLE_CLIENT_ID
        try:
            data = json.loads(self.google_config_file.read_text(encoding="utf-8"))
            return str(data.get("client_id", ""))
        except (OSError, ValueError, TypeError):
            return ""

    def configure_google_oauth(self) -> bool:
        messagebox.showinfo(
            "Google OAuth Setup",
            "In Google Cloud Console, create an OAuth client with application type "
            "'Desktop app'. Download its JSON file, then select it here.\n\n"
            "A Web application credential will not work with this desktop login.",
        )
        selected = filedialog.askopenfilename(
            title="Select Google Desktop OAuth credential JSON",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not selected:
            return False
        try:
            credential = json.loads(Path(selected).read_text(encoding="utf-8"))
            installed = credential.get("installed")
            if not isinstance(installed, dict) or not installed.get("client_id"):
                messagebox.showerror(
                    "Wrong OAuth credential",
                    "This is not a Google Desktop app credential. Create a new OAuth client "
                    "with application type 'Desktop app' and download its JSON file.",
                )
                return False
            client_id = str(installed["client_id"])
            if not client_id.endswith(".apps.googleusercontent.com"):
                raise ValueError("Invalid Google client ID.")
            # Persist only the public client ID. Never copy the client_secret.
            self.google_config_file.write_text(
                json.dumps({"client_id": client_id, "client_type": "desktop"}, indent=2),
                encoding="utf-8",
            )
            self.google_client_id = client_id
            self.status_var.set("Google Desktop OAuth configured")
            return True
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Google OAuth Setup", f"Could not read credential file:\n{exc}")
            return False

    def _google_oauth_worker(self) -> None:
        server: HTTPServer | None = None
        try:
            client_id = self.google_client_id
            if not client_id:
                raise ValueError("Google Desktop OAuth is not configured.")
            web_client_mode = bool(GOOGLE_CLIENT_SECRET and GOOGLE_CLIENT_ID)
            verifier = secrets.token_urlsafe(64)[:96]
            challenge = base64.urlsafe_b64encode(
                hashlib.sha256(verifier.encode("ascii")).digest()
            ).rstrip(b"=").decode("ascii")
            state = secrets.token_urlsafe(32)
            result: queue.Queue[dict[str, str]] = queue.Queue(maxsize=1)

            class OAuthHandler(BaseHTTPRequestHandler):
                def do_GET(handler) -> None:  # noqa: N802
                    params = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
                    payload = {key: values[0] for key, values in params.items() if values}
                    result.put(payload)
                    message = "Google sign-in complete. You can close this window and return to DYNA-STORE."
                    body = f"<html><body style='font-family:sans-serif;background:#111;color:#fff;padding:40px'><h2>{message}</h2></body></html>".encode()
                    handler.send_response(200)
                    handler.send_header("Content-Type", "text/html; charset=utf-8")
                    handler.send_header("Content-Length", str(len(body)))
                    handler.end_headers()
                    handler.wfile.write(body)

                def log_message(handler, _format: str, *args: object) -> None:
                    return

            if web_client_mode:
                redirect = urllib.parse.urlparse(GOOGLE_REDIRECT_URI)
                if redirect.scheme != "http" or redirect.hostname not in {"127.0.0.1", "localhost"}:
                    raise ValueError("GOOGLE_REDIRECT_URI must be an HTTP loopback URL.")
                if not redirect.port:
                    raise ValueError("GOOGLE_REDIRECT_URI must include a port.")
                server = HTTPServer((redirect.hostname, redirect.port), OAuthHandler)
                redirect_uri = GOOGLE_REDIRECT_URI
            else:
                server = HTTPServer(("127.0.0.1", 0), OAuthHandler)
                redirect_uri = f"http://127.0.0.1:{server.server_port}/"
            server.timeout = 180
            auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "prompt": "select_account",
            })
            webbrowser.open(auth_url)
            server.handle_request()
            if result.empty():
                raise TimeoutError("Google sign-in timed out.")
            response = result.get_nowait()
            if response.get("state") != state:
                raise ValueError("Google sign-in state validation failed.")
            if "error" in response:
                raise ValueError(f"Google sign-in was denied: {response['error']}")
            code = response.get("code")
            if not code:
                raise ValueError("Google did not return an authorization code.")

            token_data = urllib.parse.urlencode({
                "client_id": client_id,
                "code": code,
                "code_verifier": verifier,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                **({"client_secret": GOOGLE_CLIENT_SECRET} if web_client_mode else {}),
            }).encode()
            token_request = urllib.request.Request(
                "https://oauth2.googleapis.com/token", data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(token_request, timeout=30) as token_response:
                tokens = json.loads(token_response.read().decode("utf-8"))
            id_token = tokens.get("id_token")
            if not id_token:
                raise ValueError("Google did not return an ID token.")

            verify_url = "https://oauth2.googleapis.com/tokeninfo?" + urllib.parse.urlencode({"id_token": id_token})
            with urllib.request.urlopen(verify_url, timeout=30) as verify_response:
                profile = json.loads(verify_response.read().decode("utf-8"))
            if profile.get("aud") != client_id or profile.get("email_verified") not in {"true", True}:
                raise ValueError("Google identity verification failed.")
            self._emit("google_login", {
                "name": str(profile.get("name", "Google User")),
                "email": str(profile.get("email", "")),
                "sub": str(profile.get("sub", "")),
            })
        except Exception as exc:
            self._emit("google_error", str(exc))
        finally:
            if server:
                server.server_close()

    def _show_view(self, page: str) -> None:
        if getattr(self, "current_page", "") == "Game Details" and page != "Game Details":
            self._stop_youtube_stream()
        self.current_page = page
        for view in self.views.values():
            view.pack_forget()
        self.views[page].pack(fill="both", expand=True)
        if page == "My Library" and hasattr(self, "library_grid"):
            self._render_library()
        for name, button in self.nav_buttons.items():
            active = name == page
            button.configure(bg="#292929" if active else "#121212",
                             fg=ACCENT if active else MUTED)

    def _show_view_animated(self, page: str) -> None:
        target = self.views[page]
        width = max(self.content.winfo_width(), 900)
        height = max(self.content.winfo_height(), 600)
        self.current_page = page
        target.place(x=width, y=0, width=width, height=height)
        target.lift()
        for name, button in self.nav_buttons.items():
            active = name == page
            button.configure(bg="#292929" if active else "#121212",
                             fg=ACCENT if active else MUTED)

        def slide(step: int = 0) -> None:
            amount = min(1.0, step / 12)
            eased = 1 - (1 - amount) ** 3
            target.place_configure(x=int(width * (1 - eased)))
            if step < 12:
                self.after(16, lambda: slide(step + 1))
            else:
                for view in self.views.values():
                    view.pack_forget()
                target.place_forget()
                target.pack(fill="both", expand=True)

        slide()

    def _build_browse_view(self) -> None:
        view = tk.Frame(self.content, bg="#080808")
        self.views["Browse"] = view
        self.video_placeholder = tk.PhotoImage(width=1, height=1)
        self.video_banner = tk.Label(
            view, text="➤ 𝕎𝔼ℂ𝕆𝕄𝔼 𝔻𝕐ℕ𝔸-𝕊𝕋𝕆ℝ𝔼 ✦", bg="#17120e", fg="#ffffff",
            font=("Segoe UI", 25, "bold"), compound="center", height=220,
            image=self.video_placeholder,
        )
        self.video_banner.pack(fill="x")
        tools = tk.Frame(view, bg="#080808", padx=14, pady=10)
        tools.pack(fill="x")
        self.search_var = tk.StringVar()
        search = tk.Entry(tools, textvariable=self.search_var, bg="#202020", fg=TEXT,
                          insertbackground=TEXT, relief="flat", font=("Segoe UI", 10))
        search.pack(side="left", fill="x", expand=True, ipady=8)
        search.bind("<KeyRelease>", lambda _event: self._render_games())
        self._button(tools, "Search", self._render_games, ACCENT, "#111111").pack(side="left", padx=(8, 0))

        genres = tk.Frame(view, bg="#080808", padx=14, pady=4)
        genres.pack(fill="x")
        self.genre_var = tk.StringVar(value="All")
        for genre in ("All", "Action", "Adventure", "Simulation", "Horror", "RPG", "Strategy", "Indie", "Casual", "Racing"):
            tk.Radiobutton(
                genres, text=genre, value=genre, variable=self.genre_var,
                command=self._render_games, indicatoron=False, relief="flat",
                bg="#252525", fg=MUTED, selectcolor=ACCENT,
                activebackground=ACCENT, activeforeground="#111111",
                padx=12, pady=5, font=("Segoe UI", 9), cursor="hand2",
            ).pack(side="left", padx=(0, 6))

        holder = tk.Frame(view, bg="#080808")
        holder.pack(fill="both", expand=True)
        self.games_canvas = tk.Canvas(holder, bg="#080808", highlightthickness=0)
        scrollbar = tk.Scrollbar(holder, command=self.games_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.games_canvas.pack(fill="both", expand=True)
        self.games_canvas.configure(yscrollcommand=scrollbar.set)
        self.games_background_item = self.games_canvas.create_image(0, 0, anchor="nw")
        self.games_background_image = None
        self.games_grid = tk.Frame(self.games_canvas, bg="#080808")
        self.games_window = self.games_canvas.create_window((0, 0), window=self.games_grid, anchor="nw")
        self.games_grid.bind("<Configure>", lambda _e: self.games_canvas.configure(
            scrollregion=self.games_canvas.bbox("all")))
        self.games_canvas.bind("<Configure>", self._on_games_canvas_resize)
        self.games_canvas.bind_all("<MouseWheel>", lambda e: self.games_canvas.yview_scroll(
            int(-e.delta / 120), "units"))

        self.games = [
            ("Berry Bury Berry", "Adventure"), ("Task Bar Hero", "Casual"),
            ("Octopath Traveler", "RPG"), ("Fears to Fathom", "Horror"),
            ("House of Ashes", "Horror"), ("Darksiders", "Action"),
            ("Paralives", "Simulation"), ("Road Redemption", "Racing"),
            ("BioShock 2 Remastered", "Action"), ("LEGO Batman", "Adventure"),
            ("Mechanicus II", "Strategy"), ("Thick as Thieves", "Action"),
            ("Final Fantasy II", "RPG"), ("Tetris Effect", "Casual"),
            ("Hotel Architect", "Simulation"), ("Journey", "Indie"),
            ("Victoria 3", "Strategy"), ("Astral Ascent", "Action"),
            ("Space Haven", "Strategy"), ("Forza Horizon", "Racing"),
        ]
        self.default_games = dict(self.games)
        self.games = [(title, genre) for title, genre in self.games
                      if title.casefold() not in self.deleted_games]
        self._load_custom_catalog()
        self._render_games()

    def _on_games_canvas_resize(self, event) -> None:
        # Use the complete Browse area at every window size instead of leaving
        # the catalog constrained to a narrow strip on wide/full-screen displays.
        self.games_canvas.itemconfigure(self.games_window, width=max(1, event.width))
        self.games_canvas.coords(self.games_background_item, 0, 0)
        self._layout_game_cards(event.width)

    def _layout_game_cards(self, available_width: int) -> None:
        cards = getattr(self, "game_cards", [])
        if not cards:
            return
        columns = max(1, available_width // 180)
        for index, card in enumerate(cards):
            card.grid_configure(row=index // columns, column=index % columns, sticky="n")
        for column in range(max(columns, 5)):
            self.games_grid.columnconfigure(column, weight=0, uniform="")

    def _start_background_video(self) -> None:
        if cv2 is None or not self.background_video_path.is_file():
            return
        capture = cv2.VideoCapture(str(self.background_video_path))
        if not capture.isOpened():
            capture.release()
            return
        self.video_capture = capture
        self.video_source_fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        # Tkinter cannot redraw a 6480px-wide source reliably at 60 FPS. Render
        # at 30 FPS and skip source frames so playback keeps its original speed.
        playback_fps = min(self.video_source_fps, 30.0)
        self.video_frame_step = max(1, round(self.video_source_fps / playback_fps))
        self.video_delay_ms = max(16, round(1000 / playback_fps))
        self.after(1, self._update_video_background)

    def _update_video_background(self) -> None:
        if self.video_capture is None or cv2 is None or Image is None or ImageTk is None:
            return
        try:
            if getattr(self, "current_page", "Browse") != "Browse":
                self.after(180, self._update_video_background)
                return
            ok, frame = self.video_capture.read()
            if not ok:
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.video_capture.read()
            if not ok:
                self.after(500, self._update_video_background)
                return
            # Drop intermediate 60 FPS frames without decoding/converting them.
            for _ in range(self.video_frame_step - 1):
                self.video_capture.grab()
            source_frame = frame
            target_width = max(self.video_banner.winfo_width(), 900)
            target_height = 220
            source_height, source_width = frame.shape[:2]
            target_ratio = target_width / target_height
            source_ratio = source_width / source_height
            if source_ratio < target_ratio:
                crop_height = max(1, int(source_width / target_ratio))
                top = (source_height - crop_height) // 2
                frame = frame[top:top + crop_height, :]
            else:
                crop_width = max(1, int(source_height * target_ratio))
                left = (source_width - crop_width) // 2
                frame = frame[:, left:left + crop_width]
            frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            picture = Image.fromarray(frame)
            picture = ImageEnhance.Brightness(picture).enhance(0.85)
            self.video_frame_image = ImageTk.PhotoImage(picture)
            self.video_banner.configure(image=self.video_frame_image)
            self.video_background_tick += 1
            canvas_width = max(1, self.games_canvas.winfo_width())
            canvas_height = max(1, self.games_canvas.winfo_height())
            # The catalog background is deliberately refreshed less often: its
            # blur hides the lower frame rate and avoids blocking Tk's UI loop.
            if canvas_width > 10 and canvas_height > 10 and self.video_background_tick % 10 == 0:
                full_frame = source_frame
                source_height, source_width = full_frame.shape[:2]
                target_ratio = canvas_width / canvas_height
                source_ratio = source_width / source_height
                if source_ratio < target_ratio:
                    crop_height = max(1, int(source_width / target_ratio))
                    top = (source_height - crop_height) // 2
                    full_frame = full_frame[top:top + crop_height, :]
                else:
                    crop_width = max(1, int(source_height * target_ratio))
                    left = (source_width - crop_width) // 2
                    full_frame = full_frame[:, left:left + crop_width]
                full_frame = cv2.resize(
                    full_frame, (canvas_width, canvas_height), interpolation=cv2.INTER_AREA
                )
                # Keep enough detail visible so the catalog does not look like a
                # flat black panel, while still keeping game titles readable.
                full_frame = cv2.GaussianBlur(full_frame, (9, 9), 0)
                full_frame = cv2.cvtColor(full_frame, cv2.COLOR_BGR2RGB)
                background = Image.fromarray(full_frame)
                background = ImageEnhance.Brightness(background).enhance(0.48)
                self.games_background_image = ImageTk.PhotoImage(background)
                self.games_canvas.itemconfigure(
                    self.games_background_item, image=self.games_background_image
                )
                self.games_canvas.tag_lower(self.games_background_item)
            self.after(self.video_delay_ms, self._update_video_background)
        except (tk.TclError, RuntimeError):
            return

    def _close_app(self) -> None:
        self._stop_youtube_stream()
        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None
        self.destroy()

    def _load_custom_catalog(self) -> None:
        try:
            entries = json.loads(self.catalog_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            entries = []
        if not isinstance(entries, list):
            return
        known = {title.casefold() for title, _genre in self.games}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("name", "")).strip()
            genre = str(entry.get("genre", "Other")).strip() or "Other"
            if title.casefold() in self.deleted_games:
                continue
            if title and title.casefold() not in known:
                self.games.append((title, genre))
                known.add(title.casefold())
            if title and entry.get("download_url"):
                self.game_download_links[title] = str(entry["download_url"])
            if title and entry.get("youtube_url"):
                self.youtube_links[title] = str(entry["youtube_url"])
            if title and entry.get("cover_image"):
                self.game_cover_paths[title] = str(entry["cover_image"])

    def _load_deleted_games(self) -> set[str]:
        try:
            data = json.loads(self.deleted_games_file.read_text(encoding="utf-8"))
            return {str(title).casefold() for title in data} if isinstance(data, list) else set()
        except (OSError, ValueError):
            return set()

    def _save_deleted_games(self) -> None:
        self.deleted_games_file.write_text(
            json.dumps(sorted(self.deleted_games), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _get_active_server_url(self) -> str:
        custom_url = self.settings_server_url.get().strip().rstrip("/")
        if custom_url and custom_url.startswith(("http://", "https://")):
            return custom_url
        candidates = [
            Path(__file__).resolve().parent / "server" / "server_info.json",
            Path(sys.executable).resolve().parent / "server" / "server_info.json",
            Path.cwd() / "server" / "server_info.json",
        ]
        for server_info in candidates:
            if server_info.is_file():
                try:
                    info = json.loads(server_info.read_text(encoding="utf-8"))
                    if info.get("status") == "online" and info.get("public_url"):
                        return info["public_url"].rstrip("/")
                    if info.get("local_url"):
                        return info["local_url"].rstrip("/")
                except Exception:
                    pass
        return "http://127.0.0.1:8000"

    def _sync_online_server_action(self) -> None:
        self.status_var.set("Connecting to online server...")
        threading.Thread(target=self._sync_online_server_worker, args=(True,), daemon=True).start()

    def _start_online_sync(self) -> None:
        threading.Thread(target=self._sync_online_server_worker, args=(False,), daemon=True).start()

    def _sync_online_server_worker(self, manual: bool = False) -> None:
        server_url = self._get_active_server_url()
        if not server_url:
            if manual:
                self.after(0, lambda: messagebox.showinfo("Online Server", "No online server configured.\nEnter a server URL or start start_hosting_server.cmd."))
            return

        # 1. Fetch live game catalog from online server
        try:
            req = urllib.request.Request(f"{server_url}/api/catalog", headers={"User-Agent": "DYNA-STORE/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    entries = json.loads(resp.read().decode("utf-8"))
                    if isinstance(entries, list) and entries:
                        self.after(0, lambda: self._apply_online_catalog(entries, manual))
        except Exception as err:
            if manual:
                self.after(0, lambda: messagebox.showwarning("Online Sync", f"Could not reach online server:\n{err}"))

        # 2. Check for application executable updates
        try:
            req = urllib.request.Request(f"{server_url}/api/version", headers={"User-Agent": "DYNA-STORE/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    ver_info = json.loads(resp.read().decode("utf-8"))
                    remote_ver = str(ver_info.get("version", "")).strip()
                    if remote_ver and remote_ver not in ("1.0.0", "2.0"):
                        self.after(0, lambda: self._notify_app_update(ver_info))
        except Exception:
            pass

    def _apply_online_catalog(self, entries: list[dict], notify: bool = False) -> None:
        added = 0
        known = {title.casefold() for title, _genre in self.games}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("name", "")).strip()
            genre = str(entry.get("genre", "Other")).strip() or "Other"
            if not title or title.casefold() in self.deleted_games:
                continue
            if title.casefold() not in known:
                self.games.append((title, genre))
                known.add(title.casefold())
                added += 1
            if entry.get("download_url"):
                self.game_download_links[title] = str(entry["download_url"])
            if entry.get("youtube_url"):
                self.youtube_links[title] = str(entry["youtube_url"])
            if entry.get("cover_image"):
                self.game_cover_paths[title] = str(entry["cover_image"])

        self._render_games()
        self.status_var.set(f"Catalog synced: {len(self.games)} games")
        if notify:
            messagebox.showinfo("Online Catalog", f"Online catalog synchronized successfully!\nTotal games: {len(self.games)}")

    def _notify_app_update(self, ver_info: dict) -> None:
        new_ver = ver_info.get("version", "Latest")
        dl_url = ver_info.get("download_url", "")
        changelog = ver_info.get("changelog", "New updates and fixes.")
        ans = messagebox.askyesno(
            "DYNA-STORE Update Available",
            f"A new version of DYNA-STORE is available online!\n\n"
            f"Version: {new_ver}\n"
            f"Changelog: {changelog}\n\n"
            f"Would you like to open the download link in your browser?"
        )
        if ans and dl_url:
            webbrowser.open(dl_url)



    def _render_games(self) -> None:
        for widget in self.games_grid.winfo_children():
            widget.destroy()
        self.cover_images: dict[str, tk.PhotoImage] = {}
        self.game_cards: list[tk.Frame] = []
        query = self.search_var.get().strip().casefold()
        genre = self.genre_var.get()
        filtered = [game for game in self.games if query in game[0].casefold()
                    and (genre == "All" or game[1] == genre)]
        colors = ("#263b5a", "#5a2732", "#254b3b", "#493264", "#6b4a24", "#244f59")
        for index, (title, game_genre) in enumerate(filtered):
            card = tk.Frame(self.games_grid, bg="#080808", padx=7, pady=8,
                            highlightthickness=1, highlightbackground="#080808")
            self.game_cards.append(card)
            card.grid(row=index // 5, column=index % 5, sticky="n")
            card.grid_remove()
            self.after(index * 35, lambda item=card: self._reveal_card(item))
            cover_image = self._game_cover(title, game_genre)
            if cover_image:
                self.cover_images[title] = cover_image
            cover = tk.Label(card, bg=colors[index % len(colors)], fg=TEXT,
                             width=160 if cover_image else 20, height=220 if cover_image else 8,
                             image=cover_image, text="" if cover_image else "\n\n" + title.upper() + "\n\n",
                             wraplength=140, font=("Segoe UI", 11, "bold"), cursor="hand2")
            cover.pack(fill="x")
            title_label = tk.Label(card, text=title, bg="#080808", fg=TEXT, anchor="w",
                                   wraplength=160, font=("Segoe UI", 9, "bold"), cursor="hand2")
            title_label.pack(fill="x", pady=(5, 0))
            genre_label = tk.Label(card, text=game_genre, bg="#080808", fg=MUTED,
                                   anchor="w", font=("Segoe UI", 8), cursor="hand2")
            genre_label.pack(fill="x")
            for click_widget in (card, cover, title_label, genre_label):
                click_widget.bind(
                    "<ButtonRelease-1>",
                    lambda _event, game=title: self.show_game_details(game),
                )
            for hover_widget in (card, cover, title_label, genre_label):
                hover_widget.bind("<Enter>", lambda _event, item=card: self._set_game_card_hover(item, True))
                hover_widget.bind("<Leave>", lambda _event, item=card: self._set_game_card_hover(item, False))
        self._layout_game_cards(max(1, self.games_canvas.winfo_width()))
        if not filtered:
            tk.Label(self.games_grid, text="No games found.", bg="#080808", fg=MUTED,
                     font=("Segoe UI", 13)).grid(row=0, column=0, padx=30, pady=40)

    @staticmethod
    def _reveal_card(card: tk.Frame) -> None:
        try:
            if card.winfo_exists():
                card.grid()
        except tk.TclError:
            pass

    @staticmethod
    def _set_game_card_hover(card: tk.Frame, hovering: bool) -> None:
        try:
            card.configure(
                highlightbackground=ACCENT if hovering else "#080808",
                bg="#121212" if hovering else "#080808",
            )
        except tk.TclError:
            pass

    def _game_cover(self, title: str, genre: str) -> tk.PhotoImage | None:
        exact = {
            "Berry Bury Berry": "berry-bury-berry.png",
            "Task Bar Hero": "task-bar-hero.png",
            "Octopath Traveler": "octopath-traveler.png",
            "Fears to Fathom": "fears-to-fathom.png",
            "House of Ashes": "house-of-ashes.png",
            "Darksiders": "darksiders.png",
            "Paralives": "paralives.png",
            "Road Redemption": "road-redemption.png",
        }
        by_genre = {
            "Action": "darksiders.png", "Adventure": "berry-bury-berry.png",
            "Simulation": "paralives.png", "Horror": "fears-to-fathom.png",
            "RPG": "octopath-traveler.png", "Strategy": "house-of-ashes.png",
            "Indie": "berry-bury-berry.png", "Casual": "task-bar-hero.png",
            "Racing": "road-redemption.png", "Sports": "road-redemption.png",
            "Other": "task-bar-hero.png",
        }
        title_key = title.casefold()
        custom_filename = next(
            (filename for game, filename in self.game_cover_paths.items()
             if game.casefold() == title_key),
            "",
        )
        exact_filename = next(
            (filename for game, filename in exact.items() if game.casefold() == title_key),
            "",
        )
        slug = re.sub(r"[^a-z0-9]+", "-", title_key).strip("-") or "game"
        candidates = [
            custom_filename,
            f"custom-{slug}.png",
            f"custom-{slug}.gif",
            f"custom-{slug}.jpg",
            f"custom-{slug}.jpeg",
            exact_filename,
            by_genre.get(genre, "task-bar-hero.png"),
        ]
        covers_dir = Path(__file__).with_name("assets") / "covers"
        for filename in dict.fromkeys(name for name in candidates if name):
            path = covers_dir / filename
            try:
                if Image is not None and ImageTk is not None and ImageOps is not None:
                    with Image.open(path) as source:
                        fitted = source.convert("RGB").resize(
                            (160, 220), resample=Image.Resampling.LANCZOS
                        )
                        image = ImageTk.PhotoImage(fitted)
                else:
                    source = tk.PhotoImage(file=str(path))
                    x_scale = max(1, source.width() // 160)
                    y_scale = max(1, source.height() // 220)
                    image = source.subsample(x_scale, y_scale)
                return image
            except (OSError, tk.TclError):
                continue
        return None

    @staticmethod
    def _load_json_mapping(path: Path) -> dict[str, str]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {str(name): str(path) for name, path in data.items()} if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _load_settings(self) -> dict[str, object]:
        try:
            data = json.loads(self.settings_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _apply_settings_ui(self) -> None:
        if not hasattr(self, "download_log_frame"):
            return
        if self.settings_show_logs.get():
            if not self.download_log_frame.winfo_manager():
                self.download_log_frame.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        else:
            self.download_log_frame.pack_forget()

    def _apply_language(self, _event=None) -> None:
        use_khmer = self.settings_language.get() == "Khmer"
        reverse = {khmer: english for english, khmer in KHMER_TRANSLATIONS.items()}
        font_family = "Khmer UI" if use_khmer else "Segoe UI"

        def translate_widgets(widget: tk.Widget) -> None:
            try:
                if "text" in widget.keys():
                    current = str(widget.cget("text"))
                    translated = KHMER_TRANSLATIONS.get(current, current) if use_khmer else reverse.get(current, current)
                    if translated != current:
                        widget.configure(text=translated)
                if "font" in widget.keys() and str(widget.cget("font")):
                    current_font = tkfont.Font(font=widget.cget("font"))
                    details = current_font.actual()
                    widget.configure(font=(
                        font_family,
                        int(details.get("size", 10)),
                        str(details.get("weight", "normal")),
                        str(details.get("slant", "roman")),
                    ))
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                translate_widgets(child)

        translate_widgets(self)
        self.status_var.set("ភាសាត្រូវបានប្តូរទៅខ្មែរ" if use_khmer else "Language changed to English")

    def save_settings(self) -> None:
        folder = self.output_var.get().strip()
        if not folder:
            messagebox.showerror("Settings", "Choose a download folder.")
            return
        previous = self._load_settings()
        defender_changed = (
            bool(previous.get("defender_exclusion", False))
            != self.settings_defender_exclusion.get()
        )
        folder_changed = str(previous.get("download_folder", "")) != folder
        if self.settings_defender_exclusion.get() and (defender_changed or folder_changed):
            approved = messagebox.askyesno(
                "Microsoft Defender Exclusion",
                "Add this folder to Microsoft Defender exclusions for every user on this PC?\n\n"
                f"{folder}\n\nOnly continue if you trust every file saved in this folder.",
            )
            if not approved:
                self.settings_defender_exclusion.set(False)
            else:
                try:
                    self._add_defender_exclusion(folder)
                except (OSError, subprocess.SubprocessError) as exc:
                    messagebox.showerror(
                        "Microsoft Defender Exclusion",
                        "Windows could not add the exclusion. Run DYNA-STORE as administrator "
                        f"and try again.\n\n{exc}",
                    )
                    return
        data = {
            "catalog_server": self.settings_server.get(),
            "online_server_url": self.settings_server_url.get().strip(),
            "language": self.settings_language.get(),
            "download_folder": folder,
            "connections": max(1, min(64, self.settings_connections.get())),
            "extract_zip": self.extract_var.get(),
            "show_logs": self.settings_show_logs.get(),
            "disable_announcements": self.settings_disable_announcements.get(),
            "defender_exclusion": self.settings_defender_exclusion.get(),
        }
        try:
            self.settings_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            self._apply_settings_ui()
            if hasattr(self, "library_folder_label"):
                self.library_folder_label.configure(text=f"Games folder: {folder}")
            self.status_var.set("Settings saved")
            if self.settings_language.get() == "Khmer":
                messagebox.showinfo("ការកំណត់", "បានរក្សាទុកការកំណត់ដោយជោគជ័យ។")
            else:
                messagebox.showinfo("Settings", "Settings saved successfully.")
        except OSError as exc:
            messagebox.showerror("Settings", f"Could not save settings:\n{exc}")

    @staticmethod
    def _add_defender_exclusion(folder: str) -> None:
        if os.name != "nt":
            raise OSError("Microsoft Defender exclusions are only available on Windows.")
        safe_folder = folder.replace("'", "''")
        command = f"Add-MpPreference -ExclusionPath '{safe_folder}' -ErrorAction Stop"
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "Access denied."
            raise OSError(detail)

    def _load_game_mappings(self) -> dict[str, str]:
        return self._load_json_mapping(self.game_map_file)

    @staticmethod
    def _write_json_mapping(path: Path, mapping: dict[str, str]) -> None:
        path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")

    def _save_game_mappings(self) -> None:
        try:
            self._write_json_mapping(self.game_map_file, self.game_executables)
        except OSError as exc:
            messagebox.showerror("DYNA-STORE", f"Could not save game path:\n{exc}")

    def _build_game_detail_view(self) -> None:
        view = tk.Frame(self.content, bg="#080808")
        self.views["Game Details"] = view
        self.detail_title_var = tk.StringVar(value="Game")
        self.detail_genre_var = tk.StringVar()
        self.detail_video_var = tk.StringVar(value="No gameplay video selected")
        self.youtube_var = tk.StringVar()

        self.detail_hero = tk.Frame(view, bg="#332313", height=220)
        self.detail_hero.pack(fill="x")
        self.detail_hero.pack_propagate(False)
        self._button(self.detail_hero, "← Browse", lambda: self._show_view("Browse"), "#292929").pack(
            anchor="nw", padx=18, pady=16)
        self.hero_title_label = tk.Label(self.detail_hero, textvariable=self.detail_title_var,
                                         bg="#332313", fg="#7a542b",
                                         font=("Segoe UI", 42, "bold"))
        self.hero_title_label.pack(expand=True)

        body = tk.Frame(view, bg="#080808", width=760)
        self.detail_body = body
        body.pack(pady=(14, 20))
        body.pack_propagate(False)
        body.configure(height=540)
        tk.Label(body, text="GAME DETAILS", bg="#080808", fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(body, textvariable=self.detail_title_var, bg="#080808", fg=TEXT,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(6, 0))
        tk.Label(body, textvariable=self.detail_genre_var, bg="#080808", fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(2, 12))

        video = tk.Frame(body, bg="#111318", width=720, height=300, highlightthickness=1,
                         highlightbackground="#343944", cursor="hand2")
        self.detail_video_frame = video
        video.pack(fill="x")
        video.pack_propagate(False)
        self.youtube_preview_label = tk.Label(video, bg="#111318", cursor="hand2")
        self.youtube_preview_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.youtube_preview_label.bind("<Button-1>", lambda _e: self.play_game_video())
        self.youtube_preview_image = None
        self.play_icon = tk.Label(video, text="▶", bg="#111318", fg=ACCENT,
                                  font=("Segoe UI Symbol", 56), cursor="hand2")
        self.play_icon.place(relx=.5, rely=.48, anchor="center")
        self.video_status_label = tk.Label(video, textvariable=self.detail_video_var,
                                           bg="#111318", fg=MUTED, font=("Segoe UI", 9))
        self.video_status_label.place(relx=.5, rely=.91, anchor="center")
        video.bind("<Button-1>", lambda _e: self.play_game_video())
        self.play_icon.bind("<Button-1>", lambda _e: self.play_game_video())

        actions = tk.Frame(body, bg="#080808", pady=8, highlightthickness=1,
                           highlightbackground="#252525")
        actions.pack(fill="x")
        self.download_game_button = self._button(
            actions, "↓ Download Game", self._download_selected_game, ACCENT, "#111111"
        )
        self.download_game_button.pack(side="left", padx=8, pady=5)

    def show_game_details(self, title: str) -> None:
        self._stop_youtube_stream()
        self.selected_game = title
        genre = next((genre for game, genre in self.games if game == title), "Game")
        self.detail_title_var.set(title)
        self.detail_genre_var.set(genre)
        self.download_game_button.configure(state="normal", text="↓ Download Game")
        video = Path(self.game_videos.get(title, ""))
        youtube = self.youtube_links.get(title, "")
        self.youtube_var.set(youtube)
        if youtube:
            self.detail_video_var.set("Loading YouTube preview…")
            self.youtube_preview_label.configure(image="", bg="#111318")
            threading.Thread(target=self._load_youtube_preview, args=(title, youtube), daemon=True).start()
        else:
            self.youtube_preview_label.configure(image="", bg="#111318")
            self.detail_video_var.set(video.name if video.is_file() else "Add a YouTube link or choose a local video")
        self._show_view_animated("Game Details")
        self._animate_game_details_view()

    def _animate_game_details_view(self) -> None:
        self.detail_animation_token = getattr(self, "detail_animation_token", 0) + 1
        token = self.detail_animation_token
        self.detail_hero.configure(height=128)
        self.hero_title_label.configure(font=("Segoe UI", 27, "bold"), fg="#5b4025")
        self.detail_video_frame.configure(highlightthickness=3, highlightbackground="#5d421f")

        def animate(step: int = 0) -> None:
            if token != self.detail_animation_token or self.current_page != "Game Details":
                return
            amount = min(1.0, step / 12)
            eased = 1 - (1 - amount) ** 3
            self.detail_hero.configure(height=int(128 + 92 * eased))
            family = "Khmer UI" if self.settings_language.get() == "Khmer" else "Segoe UI"
            self.hero_title_label.configure(font=(family, int(27 + 15 * eased), "bold"))
            glow = int(66 + 80 * eased)
            self.detail_video_frame.configure(
                highlightbackground=f"#{glow:02x}{int(glow * .68):02x}24"
            )
            if step < 12:
                self.after(18, lambda: animate(step + 1))
            else:
                self.detail_video_frame.configure(
                    highlightthickness=1, highlightbackground="#343944"
                )

        animate()

    @staticmethod
    def _youtube_video_id(url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").casefold()
        if host == "youtu.be":
            return parsed.path.strip("/").split("/")[0]
        if parsed.path == "/watch":
            return urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live"}:
            return parts[1]
        return ""

    def _load_youtube_preview(self, title: str, url: str) -> None:
        video_id = self._youtube_video_id(url)
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video_id):
            self._emit("youtube_preview_error", (title, "Invalid YouTube video link"))
            return
        try:
            request = urllib.request.Request(
                f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                headers={"User-Agent": "DYNA-STORE/1.0"},
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read(3 * 1024 * 1024)
            self._emit("youtube_preview", (title, data))
        except Exception as exc:
            self._emit("youtube_preview_error", (title, str(exc)))

    def save_youtube_link(self) -> None:
        title = getattr(self, "selected_game", "")
        link = self.youtube_var.get().strip()
        if not title:
            return
        parsed = urllib.parse.urlparse(link)
        hostname = (parsed.hostname or "").casefold()
        if parsed.scheme not in {"http", "https"} or hostname not in {
            "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
        }:
            messagebox.showerror("Invalid YouTube link", "Paste a valid youtube.com or youtu.be URL.")
            return
        self.youtube_links[title] = link
        try:
            self._write_json_mapping(self.youtube_map_file, self.youtube_links)
            self.detail_video_var.set("Click ▶ to open YouTube gameplay video")
            self.status_var.set(f"YouTube link saved: {title}")
        except OSError as exc:
            messagebox.showerror("DYNA-STORE", f"Could not save YouTube link:\n{exc}")

    def choose_game_video(self) -> None:
        title = getattr(self, "selected_game", "")
        if not title:
            return
        selected = filedialog.askopenfilename(
            title=f"Select gameplay video for {title}",
            filetypes=(("Video files", "*.mp4 *.mkv *.avi *.mov *.webm"), ("All files", "*.*")),
        )
        if selected:
            self.game_videos[title] = selected
            try:
                self._write_json_mapping(self.video_map_file, self.game_videos)
                self.detail_video_var.set(Path(selected).name)
            except OSError as exc:
                messagebox.showerror("DYNA-STORE", f"Could not save video path:\n{exc}")

    def play_game_video(self) -> None:
        title = getattr(self, "selected_game", "")
        youtube = self.youtube_links.get(title, "")
        if youtube:
            if getattr(sys, "frozen", False):
                player = Path(__file__).with_name("youtube_player.exe")
                command = [str(player), youtube]
            else:
                player = Path(__file__).with_name("youtube_player.py")
                command = [sys.executable, str(player), youtube]
            try:
                subprocess.Popen(
                    command,
                    cwd=str(player.parent),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                self.status_var.set(f"Playing YouTube: {title}")
                self.detail_video_var.set("Playing in DYNA-STORE Video Player")
            except OSError as exc:
                messagebox.showerror("YouTube Player", str(exc))
            return
            if self.youtube_stream_capture is not None:
                self.youtube_stream_playing = not self.youtube_stream_playing
                if self.youtube_stream_playing:
                    self.play_icon.place_forget()
                    self.detail_video_var.set("Playing in DYNA-STORE (video only)")
                    self._update_youtube_stream()
                else:
                    self.play_icon.place(relx=.5, rely=.48, anchor="center")
                    self.detail_video_var.set("Paused — click ▶ to resume")
                return
            if self.youtube_stream_resolving:
                return
            if yt_dlp is None or cv2 is None:
                messagebox.showerror("YouTube Player", "Install yt-dlp and OpenCV to use the internal player.")
                return
            self.youtube_stream_resolving = True
            self.detail_video_var.set("Preparing YouTube stream…")
            threading.Thread(target=self._resolve_youtube_stream,
                             args=(title, youtube), daemon=True).start()
            return
        video = Path(self.game_videos.get(title, ""))
        if not video.is_file():
            self.choose_game_video()
            video = Path(self.game_videos.get(title, ""))
        if video.is_file():
            try:
                os.startfile(video)  # type: ignore[attr-defined]
            except OSError as exc:
                messagebox.showerror("Could not play video", str(exc))

    def _resolve_youtube_stream(self, title: str, url: str) -> None:
        try:
            options = {
                "quiet": True, "no_warnings": True, "noplaylist": True,
                "format": "best[ext=mp4][height<=720]/best[ext=mp4]/best[height<=720]/best",
            }
            if self.youtube_cookie_browser:
                options["cookiesfrombrowser"] = (self.youtube_cookie_browser,)
            with yt_dlp.YoutubeDL(options) as downloader:
                info = downloader.extract_info(url, download=False)
            stream_url = str(info.get("url", ""))
            if not stream_url:
                raise ValueError("No playable stream was returned.")
            capture = cv2.VideoCapture(stream_url)
            if not capture.isOpened():
                capture.release()
                raise ValueError("The resolved stream could not be opened.")
            self._emit("youtube_stream_ready", (title, capture))
        except Exception as exc:
            error = str(exc)
            if "Sign in to confirm" in error and not self.youtube_cookie_browser:
                self._emit("youtube_auth_required", (title, url))
            else:
                self._emit("youtube_stream_error", (title, error))

    def _update_youtube_stream(self) -> None:
        capture = self.youtube_stream_capture
        if not self.youtube_stream_playing or capture is None or cv2 is None:
            return
        ok, frame = capture.read()
        if not ok:
            self._stop_youtube_stream()
            self.detail_video_var.set("Video ended — click ▶ to replay")
            self.play_icon.place(relx=.5, rely=.48, anchor="center")
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        picture = Image.fromarray(frame)
        picture = ImageOps.fit(picture, (720, 300), method=Image.Resampling.LANCZOS)
        self.youtube_preview_image = ImageTk.PhotoImage(picture)
        self.youtube_preview_label.configure(image=self.youtube_preview_image)
        fps = capture.get(cv2.CAP_PROP_FPS) or 24
        self.after(max(25, int(1000 / min(fps, 30))), self._update_youtube_stream)

    def _stop_youtube_stream(self) -> None:
        self.youtube_stream_playing = False
        self.youtube_stream_resolving = False
        if self.youtube_stream_capture is not None:
            self.youtube_stream_capture.release()
            self.youtube_stream_capture = None

    def _play_selected_game(self) -> None:
        title = getattr(self, "selected_game", "")
        if title:
            self.open_game(title)

    def _download_selected_game(self) -> None:
        if not self.keyauth_user:
            messagebox.showwarning("KeyAuth Required", "Log in to KeyAuth before downloading a game.")
            self.show_keyauth_login(lock_app=True)
            return
        title = getattr(self, "selected_game", "")
        if title:
            self.name_var.set(title)
            download_url = self.game_download_links.get(title, "")
            if download_url:
                self.url_var.set(download_url)
                if hasattr(self, "start_button"):
                    self.start_button.configure(state="normal")
        self._show_view("Downloads")

    def open_game(self, title: str) -> None:
        executable = Path(self.game_executables.get(title, ""))
        if not executable.is_file():
            selected = self._choose_library_exe(title)
            if selected is None:
                return
            executable = selected

        try:
            if os.name == "nt":
                os.startfile(executable, cwd=str(executable.parent))  # type: ignore[attr-defined]
            else:
                subprocess.Popen([str(executable)], cwd=str(executable.parent))
            self.status_var.set(f"Playing: {title}")
        except OSError as exc:
            messagebox.showerror("Could not open game", str(exc))

    def _build_library_view(self) -> None:
        view = tk.Frame(self.content, bg=APP_BG, padx=16, pady=16)
        self.views["My Library"] = view
        heading = tk.Frame(view, bg=APP_BG)
        heading.pack(fill="x", pady=(0, 16))
        tk.Label(heading, text="Installed Games", bg=APP_BG, fg=TEXT,
                 font=("Segoe UI", 15, "bold")).pack(side="left")
        self.library_folder_label = tk.Label(
            heading, text=f"Games folder: {self.output_var.get()}", bg=APP_BG, fg=MUTED,
            font=("Segoe UI", 9)
        )
        self.library_folder_label.pack(side="right", padx=(12, 0))
        self._button(heading, "Re-scan folder", self._scan_library, "#292929").pack(side="right")

        body = tk.Frame(view, bg=APP_BG)
        body.pack(fill="both", expand=True)
        self.library_canvas = tk.Canvas(body, bg=APP_BG, highlightthickness=0)
        library_scroll = ttk.Scrollbar(body, orient="vertical", command=self.library_canvas.yview)
        self.library_canvas.configure(yscrollcommand=library_scroll.set)
        library_scroll.pack(side="right", fill="y")
        self.library_canvas.pack(side="left", fill="both", expand=True)
        self.library_grid = tk.Frame(self.library_canvas, bg=APP_BG)
        self.library_window = self.library_canvas.create_window((0, 0), window=self.library_grid, anchor="nw")
        self.library_grid.bind(
            "<Configure>",
            lambda _event: self.library_canvas.configure(scrollregion=self.library_canvas.bbox("all")),
        )
        self.library_canvas.bind(
            "<Configure>",
            lambda event: self.library_canvas.itemconfigure(self.library_window, width=event.width),
        )
        self._render_library()

    def _render_library(self) -> None:
        for child in self.library_grid.winfo_children():
            child.destroy()
        self.library_cover_images: list[tk.PhotoImage] = []
        installed = [
            (title, Path(executable))
            for title, executable in sorted(self.game_executables.items())
            if Path(executable).is_file()
        ]
        if hasattr(self, "library_folder_label"):
            self.library_folder_label.configure(text=f"Games folder: {self.output_var.get()}")
        if not installed:
            tk.Label(
                self.library_grid,
                text="No installed games found. Select Re-scan folder or play a game to choose its EXE.",
                bg=APP_BG, fg=MUTED, font=("Segoe UI", 11), pady=45,
            ).grid(row=0, column=0, sticky="w")
            return

        for index, (title, executable) in enumerate(installed):
            card = tk.Frame(self.library_grid, bg="#0d0d0d", width=230)
            card.grid(row=index // 5, column=index % 5, padx=(0, 12), pady=(0, 22), sticky="n")
            card.grid_propagate(False)
            card.configure(height=390)
            genre = next((genre for game, genre in self.games if game == title), "Other")
            cover_image = self._game_cover(title, genre)
            if cover_image:
                self.library_cover_images.append(cover_image)
            tk.Label(
                card, image=cover_image, text="" if cover_image else title.upper(),
                compound="center", bg="#20242c", fg=TEXT, width=210, height=220,
                font=("Segoe UI", 10, "bold"), wraplength=145,
            ).pack(fill="x")
            tk.Label(card, text=title, bg="#0d0d0d", fg=TEXT, anchor="w",
                     font=("Segoe UI", 9, "bold")).pack(fill="x", pady=(7, 0))
            tk.Label(card, text=executable.name, bg="#0d0d0d", fg=MUTED, anchor="w",
                     font=("Segoe UI", 8)).pack(fill="x", pady=(2, 5))
            controls = tk.Frame(card, bg="#0d0d0d")
            controls.pack(fill="x")
            self._button(controls, "▶ PLAY", lambda game=title: self.open_game(game), ACCENT, "#111111").pack(side="left")
            self._button(controls, "Delete", lambda game=title: self._remove_library_game(game), "#a8362a").pack(side="left")
            self._button(card, "Choose EXE / BAT File", lambda game=title: self._choose_library_exe(game),
                         "#292929").pack(fill="x", pady=(5, 0))
            tools = tk.Frame(card, bg="#0d0d0d")
            tools.pack(fill="x", pady=(5, 0))
            self._button(tools, "Open Folder", lambda path=executable: self._open_game_folder(path), "#292929").pack(side="left")
            self._button(tools, "Desktop", lambda game=title: self._create_desktop_shortcut(game), "#334b70").pack(side="left", padx=4)

    def _choose_library_exe(self, title: str) -> Path | None:
        current = Path(self.game_executables.get(title, ""))
        downloads = Path(self.output_var.get()).expanduser().resolve()
        try:
            relative = current.resolve().relative_to(downloads)
            game_folder = downloads / relative.parts[0] if relative.parts else downloads
        except ValueError:
            game_folder = current.parent if current.is_file() else downloads / title
        if not game_folder.is_dir():
            game_folder = downloads

        dialog = tk.Toplevel(self)
        dialog.title(f"Select EXE or BAT — {title}")
        dialog.configure(bg=PANEL_BG)
        dialog.geometry("700x390")
        dialog.transient(self)
        dialog.grab_set()
        tk.Label(dialog, text=f"Select EXE or BAT — {title}", bg=PANEL_BG, fg=ACCENT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=24, pady=(18, 4))
        tk.Label(dialog, text="Pick an EXE or BAT file for the PLAY button in Library.",
                 bg=PANEL_BG, fg=MUTED).pack(anchor="w", padx=24, pady=(0, 12))
        list_frame = tk.Frame(dialog, bg=PANEL_BG)
        list_frame.pack(fill="both", expand=True, padx=24)
        file_list = tk.Listbox(list_frame, bg=INPUT_BG, fg=TEXT, selectbackground=ACCENT,
                               selectforeground="#111111", font=("Segoe UI", 10))
        scroll = tk.Scrollbar(list_frame, command=file_list.yview)
        file_list.configure(yscrollcommand=scroll.set)
        file_list.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        candidates: list[Path] = []

        def rescan() -> None:
            candidates.clear()
            file_list.delete(0, "end")
            for folder, directories, files in os.walk(game_folder):
                location = Path(folder)
                depth = len(location.relative_to(game_folder).parts)
                directories[:] = [part for part in directories if not part.startswith((".", "$"))]
                if depth >= 4:
                    directories.clear()
                candidates.extend(location / name for name in files
                                  if name.casefold().endswith((".exe", ".bat")))
            candidates.sort(key=lambda path: str(path.relative_to(game_folder)).casefold())
            for path in candidates:
                file_list.insert("end", str(path.relative_to(game_folder)))
            selected_index = next((i for i, path in enumerate(candidates) if path == current), None)
            if selected_index is not None:
                file_list.selection_set(selected_index)
                file_list.see(selected_index)

        result: list[Path] = []

        def save(path: Path) -> None:
            if not path.is_file() or path.suffix.casefold() not in {".exe", ".bat"}:
                messagebox.showerror("Choose Game File", "Choose an existing EXE or BAT file.", parent=dialog)
                return
            self.game_executables[title] = str(path)
            self._save_game_mappings()
            self._render_library()
            result.append(path)
            dialog.destroy()

        def save_selected(_event=None) -> None:
            selection = file_list.curselection()
            if selection:
                save(candidates[selection[0]])
            else:
                messagebox.showinfo("Choose Game File", "Select a file from the list first.", parent=dialog)

        def browse() -> None:
            selected = filedialog.askopenfilename(
                parent=dialog, title=f"Choose EXE / BAT File for {title}", initialdir=str(game_folder),
                filetypes=(("Game launchers", "*.exe *.bat"), ("EXE files", "*.exe"), ("BAT files", "*.bat")),
            )
            if selected:
                save(Path(selected))

        buttons = tk.Frame(dialog, bg=PANEL_BG)
        buttons.pack(fill="x", padx=24, pady=16)
        self._button(buttons, "Choose EXE / BAT File...", browse, "#292929").pack(side="left")
        self._button(buttons, "Set as PLAY", save_selected, ACCENT, "#111111").pack(side="right")
        self._button(buttons, "Rescan Files", rescan, "#292929").pack(side="right", padx=8)
        self._button(buttons, "Later", dialog.destroy, "#292929").pack(side="right")
        file_list.bind("<Double-Button-1>", save_selected)
        rescan()
        self.wait_window(dialog)
        return result[0] if result else None

    def _remove_library_game(self, title: str) -> None:
        if messagebox.askyesno("Remove from Library", f"Remove '{title}' from My Library?\n\nGame files will not be deleted."):
            self.game_executables.pop(title, None)
            self._save_game_mappings()
            self._render_library()

    def _open_game_folder(self, executable: Path) -> None:
        folder = executable.parent
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", "/select,", str(executable)])
            else:
                webbrowser.open(folder.as_uri())
        except OSError as exc:
            messagebox.showerror("Open Game Folder", str(exc))

    def _create_desktop_shortcut(self, title: str) -> None:
        executable = Path(self.game_executables.get(title, ""))
        if os.name != "nt" or not executable.is_file():
            messagebox.showerror("Desktop Shortcut", "A valid Windows game executable is required.")
            return
        safe_title = re.sub(r'[<>:"/\\|?*]+', "_", title).strip(" .") or "Game"
        environment = os.environ.copy()
        environment["DYNA_SHORTCUT_TARGET"] = str(executable)
        environment["DYNA_SHORTCUT_NAME"] = safe_title
        script = (
            "$desktop=[Environment]::GetFolderPath('Desktop');"
            "$link=Join-Path $desktop ($env:DYNA_SHORTCUT_NAME + '.lnk');"
            "$shell=New-Object -ComObject WScript.Shell;"
            "$shortcut=$shell.CreateShortcut($link);"
            "$shortcut.TargetPath=$env:DYNA_SHORTCUT_TARGET;"
            "$shortcut.WorkingDirectory=Split-Path $env:DYNA_SHORTCUT_TARGET;"
            "$shortcut.IconLocation=$env:DYNA_SHORTCUT_TARGET;"
            "$shortcut.Save()"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                env=environment, capture_output=True, text=True, timeout=15,
            )
            if result.returncode:
                raise OSError(result.stderr.strip() or "Windows could not create the shortcut.")
            self.status_var.set(f"Desktop shortcut created: {safe_title}.lnk")
            messagebox.showinfo("Desktop Shortcut", f"Created '{safe_title}.lnk' on your Desktop.")
        except (OSError, subprocess.SubprocessError) as exc:
            messagebox.showerror("Desktop Shortcut", str(exc))

    @staticmethod
    def _find_game_executable(game_folder: Path) -> Path | None:
        ignored_parts = {"redist", "redistributables", "_commonredist", "directx", "vcredist"}
        ignored_names = {"unins000.exe", "uninstall.exe", "setup.exe", "installer.exe"}
        candidates: list[Path] = []
        for folder, directories, files in os.walk(game_folder):
            current = Path(folder)
            depth = len(current.relative_to(game_folder).parts)
            directories[:] = [
                name for name in directories
                if not name.startswith((".", "$")) and name.casefold() not in ignored_parts
            ]
            if depth >= 4:
                directories.clear()
            candidates.extend(
                current / name for name in files
                if name.casefold().endswith(".exe") and name.casefold() not in ignored_names
            )
        if not candidates:
            return None
        folder_key = re.sub(r"[^a-z0-9]", "", game_folder.name.casefold())
        def score(path: Path) -> tuple[int, int]:
            exe_key = re.sub(r"[^a-z0-9]", "", path.stem.casefold())
            penalty = 50 if any(word in exe_key for word in ("crash", "report", "helper", "launcherconfig")) else 0
            name_match = 100 if folder_key and (folder_key in exe_key or exe_key in folder_key) else 0
            return name_match - penalty, path.stat().st_size
        return max(candidates, key=score)

    def _scan_library(self) -> None:
        root = Path(self.output_var.get()).expanduser()
        if not root.is_dir():
            messagebox.showwarning("Library Scan", f"Games folder was not found:\n{root}")
            return
        found = 0
        game_folders = [folder for folder in root.iterdir() if folder.is_dir() and not folder.name.startswith((".", "$"))]
        for game_folder in game_folders:
            executable = self._find_game_executable(game_folder)
            if executable is None:
                continue
            title = game_folder.name
            if self.game_executables.get(title) != str(executable):
                self.game_executables[title] = str(executable)
                found += 1
        self._save_game_mappings()
        self._render_library()
        self.status_var.set(f"Library scan complete: {found} new game(s)")

    def _update_download_artwork(self) -> None:
        title = self.name_var.get().strip()
        slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
        filename = next((value for key, value in self.game_cover_paths.items()
                         if key.casefold() == title.casefold()), f"custom-{slug}.png")
        path = Path(__file__).with_name("assets") / "covers" / filename
        if not path.is_file():
            path = Path(__file__).with_name("assets") / "covers" / "task-bar-hero.png"
        if Image is None or ImageTk is None or not path.is_file():
            self.download_artwork.configure(image="")
            self.download_title.pack(side="top", fill="x", padx=22, pady=(34, 0))
            return
        try:
            with Image.open(path) as source:
                cover = source.convert("RGB")
                picture = ImageOps.fit(cover, (520, 202), method=Image.Resampling.LANCZOS)
                cover_panel = ImageOps.fit(cover, (145, 202), method=Image.Resampling.LANCZOS)
            picture = picture.filter(ImageFilter.GaussianBlur(13)).convert("RGBA")
            picture.paste(cover_panel.convert("RGBA"), (375, 0))
            tint = Image.new("RGBA", (520, 202), (0, 0, 0, 0))
            tint_pixels = tint.load()
            for x in range(520):
                opacity = int(230 - 125 * x / 519)
                for y in range(202):
                    tint_pixels[x, y] = (11, 24, 37, opacity)
            picture = Image.alpha_composite(picture, tint).convert("RGB")
            font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeuib.ttf"
            font = ImageFont.truetype(str(font_path), 31) if font_path.is_file() else ImageFont.load_default()
            draw = ImageDraw.Draw(picture)
            lines = []
            for word in title.upper().split():
                candidate = f"{lines[-1]} {word}" if lines else word
                if lines and draw.textlength(candidate, font=font) > 330:
                    lines.append(word)
                elif lines:
                    lines[-1] = candidate
                else:
                    lines.append(word)
            for index, line in enumerate(lines[:2]):
                draw.text((22, 49 + index * 39), line, font=font, fill="white",
                          stroke_width=2, stroke_fill="#102031")
            self.download_artwork_image = ImageTk.PhotoImage(picture)
            self.download_artwork.configure(image=self.download_artwork_image)
            self.download_title.pack_forget()
        except (OSError, ValueError):
            self.download_artwork.configure(image="")
            self.download_title.pack(side="top", fill="x", padx=22, pady=(34, 0))

    def _build_download_view(self) -> None:
        view = tk.Frame(self.content, bg=APP_BG)
        self.views["Downloads"] = view
        hero = tk.Frame(view, bg="#151b23", height=202)
        hero.pack(fill="x", padx=24, pady=(20, 14))
        hero.pack_propagate(False)

        artwork = tk.Frame(hero, bg="#193b5a", width=520)
        artwork.pack(side="left", fill="y")
        artwork.pack_propagate(False)
        self.download_artwork = tk.Label(artwork, bg="#193b5a")
        self.download_artwork.place(x=0, y=0, relwidth=1, relheight=1)
        self.download_title = tk.Label(artwork, textvariable=self.name_var, bg="#193b5a", fg="#ffffff",
                                       font=("Segoe UI", 27, "bold"), anchor="w", wraplength=480)
        self.download_title.pack(side="top", fill="x", padx=22, pady=(34, 0))
        device_row = tk.Frame(artwork, bg="#172b3f")
        device_row.pack(side="bottom", anchor="w", padx=16, pady=(0, 13))
        tk.Label(device_row, text="MANAGING DOWNLOADS FOR", bg="#172b3f",
                 fg="#d7e7f5", font=("Segoe UI", 9, "bold"),
                 padx=9, pady=5).pack(side="left")
        tk.Label(device_row, text="This Device", bg="#267bd0", fg="#ffffff",
                 font=("Segoe UI", 9, "bold"), padx=12, pady=5).pack(side="left")
        self.name_var.trace_add("write", lambda *_: self._update_download_artwork())
        self._update_download_artwork()

        details = tk.Frame(hero, bg="#151b23", padx=22, pady=17)
        details.pack(side="left", fill="both", expand=True)
        metrics = tk.Frame(details, bg="#151b23")
        metrics.pack(fill="x", pady=(0, 20))
        for caption, variable, color in (
            ("NETWORK", self.download_speed_var, "#58a4df"),
            ("PEAK", self.download_peak_var, "#58a4df"),
            ("DISK USAGE", self.disk_speed_var, "#63cd5a"),
        ):
            group = tk.Frame(metrics, bg="#151b23")
            group.pack(side="left", padx=(0, 35))
            tk.Label(group, text=caption, bg="#151b23", fg="#aab3bf",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w")
            tk.Label(group, textvariable=variable, bg="#151b23", fg=color,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self._button(metrics, "⚙", lambda: self._show_view("Settings"),
                     "#343d49").pack(side="right")

        download_row = tk.Frame(details, bg="#151b23")
        download_row.pack(fill="x", padx=(0, 58))
        tk.Label(download_row, text="Downloading data", bg="#151b23", fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(download_row, textvariable=self.download_amount_var, bg="#151b23", fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(side="right")
        ttk.Progressbar(details, style="Download.Horizontal.TProgressbar",
                        variable=self.data_progress_var, maximum=100).pack(
                            fill="x", padx=(0, 58), pady=(4, 10))
        install_row = tk.Frame(details, bg="#151b23")
        install_row.pack(fill="x", padx=(0, 58))
        tk.Label(install_row, text="Installing files", bg="#151b23", fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(install_row, textvariable=self.install_percent_var, bg="#151b23",
                 fg=MUTED, font=("Segoe UI", 9, "bold")).pack(side="right")
        ttk.Progressbar(details, style="Install.Horizontal.TProgressbar",
                        variable=self.install_progress_var, maximum=100).pack(
                            fill="x", padx=(0, 58), pady=(4, 0))
        self.pause_button = self._button(details, "II", self.toggle_pause_download,
                                          "#1479d6", "#ffffff")
        self.pause_button.place(relx=1.0, rely=1.0, x=-8, y=-15,
                                anchor="se", width=38, height=36)
        self.pause_button.configure(state="disabled")
        self.download_tooltip = None
        self.download_tooltip_after = None
        self.pause_button.bind("<Enter>", self._schedule_download_tooltip, add="+")
        self.pause_button.bind("<Leave>", self._hide_download_tooltip, add="+")
        self.pause_button.bind("<Button-1>", self._hide_download_tooltip, add="+")

        form = tk.Frame(view, bg=PANEL_BG, padx=18, pady=16, highlightthickness=1,
                        highlightbackground="#343944")
        form.pack(fill="x", padx=24, pady=(0, 14))
        form.columnconfigure(1, weight=1)
        self._field(form, 0, "Display name", self.name_var)
        self._field(form, 1, "Save folder", self.output_var, browse=True)

        controls = tk.Frame(form, bg=PANEL_BG)
        controls.grid(row=2, column=1, sticky="ew", pady=(12, 0))
        ttk.Checkbutton(controls, text="Extract archives after download", variable=self.extract_var).pack(side="left")
        self.cancel_button = self._button(controls, "Cancel", self.cancel_download, "#3b404c")
        self.cancel_button.pack(side="right", padx=(8, 0))
        self.cancel_button.configure(state="disabled")
        self.start_button = self._button(controls, "Download", self.start_download, ACCENT, fg="#151515")
        self.start_button.pack(side="right")
        self.extract_again_button = self._button(
            controls, "Extract Again", self.extract_again, "#267bd0", fg="#ffffff"
        )
        self.extract_again_button.pack(side="right", padx=(0, 8))
        self.extract_again_button.configure(state="disabled")

        self.download_log_frame = tk.Frame(
            view, bg=PANEL_BG, highlightthickness=1, highlightbackground="#343944"
        )
        self.download_log_frame.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        tk.Label(self.download_log_frame, text="Download Logs", bg=PANEL_BG, fg=ACCENT,
                 font=("Segoe UI", 12, "bold"), padx=16, pady=10).pack(anchor="w")
        body = tk.Frame(self.download_log_frame, bg=PANEL_BG)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        scroll = tk.Scrollbar(body)
        scroll.pack(side="right", fill="y")
        self.log_text = tk.Text(body, bg="#14161b", fg="#e5e7eb", insertbackground=TEXT,
                                selectbackground="#434957", relief="flat", padx=10, pady=8,
                                font=("Consolas", 10), wrap="none", yscrollcommand=scroll.set)
        self.log_text.pack(fill="both", expand=True)
        scroll.configure(command=self.log_text.yview)
        self.log_text.tag_configure("error", foreground="#ff6b6b")
        self.log_text.tag_configure("success", foreground=GREEN)
        self.log_text.configure(state="disabled")

    def _build_info_views(self) -> None:
        settings = tk.Frame(self.content, bg=APP_BG, padx=22, pady=24)
        self.views["Settings"] = settings
        tk.Label(settings, text="Settings", bg=APP_BG, fg=ACCENT,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(settings, text="Version 2.0", bg=APP_BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 14))

        def setting_label(title: str, description: str) -> None:
            tk.Label(settings, text=title, bg=APP_BG, fg=TEXT,
                     font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8, 2))
            tk.Label(settings, text=description, bg=APP_BG, fg=MUTED,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 6))

        setting_label("Catalog Server", "Choose which catalog to browse.")
        ttk.Combobox(settings, textvariable=self.settings_server, state="readonly",
                     values=("Server 1", "Server 2"), width=35).pack(anchor="w", ipady=6)
        setting_label("Online Server URL", "Live Cloudflare or local server URL for game catalog and app updates.")
        server_url_row = tk.Frame(settings, bg=APP_BG)
        server_url_row.pack(anchor="w", fill="x")
        tk.Entry(server_url_row, textvariable=self.settings_server_url, bg=INPUT_BG, fg=TEXT,
                 insertbackground=TEXT, relief="flat", width=46).pack(side="left", ipady=8)
        self._button(server_url_row, "Sync Catalog", self._sync_online_server_action, "#343944").pack(side="left", padx=8)
        setting_label("Language", "Choose the app display language.")
        language_box = ttk.Combobox(settings, textvariable=self.settings_language, state="readonly",
                                    values=("English", "Khmer"), width=35)
        language_box.pack(anchor="w", ipady=6)
        language_box.bind("<<ComboboxSelected>>", self._apply_language)
        setting_label("Download / Games Folder", "All downloads and extracted games go here.")
        folder_row = tk.Frame(settings, bg=APP_BG)
        folder_row.pack(anchor="w", fill="x")
        tk.Entry(folder_row, textvariable=self.output_var, bg=INPUT_BG, fg=TEXT,
                 insertbackground=TEXT, relief="flat", width=62).pack(side="left", ipady=9)
        self._button(folder_row, "Browse...", self.choose_folder, "#343944").pack(side="left", padx=8)
        setting_label("Download Connections", "Parallel connection preference (1–64).")
        scale_row = tk.Frame(settings, bg=APP_BG)
        scale_row.pack(anchor="w", fill="x")
        tk.Scale(scale_row, from_=1, to=64, orient="horizontal", variable=self.settings_connections,
                 bg=APP_BG, fg=TEXT, troughcolor=INPUT_BG, activebackground=ACCENT,
                 highlightthickness=0, length=580).pack(side="left")
        tk.Label(scale_row, textvariable=self.settings_connections, bg=APP_BG, fg=ACCENT,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=8)
        checks = (
            ("Extract archives after download", self.extract_var),
            ("Show download logs panel", self.settings_show_logs),
            ("Disable announcement on startup", self.settings_disable_announcements),
            ("Add download folder to Microsoft Defender exclusions (all Windows users)",
             self.settings_defender_exclusion),
        )
        for text, variable in checks:
            tk.Checkbutton(settings, text=text, variable=variable, bg=APP_BG, fg=TEXT,
                           activebackground=APP_BG, activeforeground=TEXT,
                           selectcolor=INPUT_BG, font=("Segoe UI", 10)).pack(anchor="w", pady=3)
        actions = tk.Frame(settings, bg=APP_BG)
        actions.pack(anchor="w", pady=(14, 0))
        self._button(actions, "Save Settings", self.save_settings, ACCENT, "#111111").pack(side="left")

        help_view = tk.Frame(self.content, bg=APP_BG, padx=22, pady=26)
        self.views["Help"] = help_view
        tk.Label(help_view, text="Help & Support", bg=APP_BG, fg=ACCENT,
                 font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(help_view, text="Have a question or need help? Join our group or contact the admin.",
                 bg=APP_BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 22))

        support_links = (
            ("✈", "TELEGRAM GROUP", "t.me/+SXoEyjQ_WddhZjY1", "https://t.me/+SXoEyjQ_WddhZjY1"),
            ("●", "ADMIN TELEGRAM", "t.me/Maodyna0110", "https://t.me/Maodyna0110"),
        )
        for icon, service, account, url in support_links:
            card = tk.Button(
                help_view,
                text=f"{icon}     {service}\n       {account}\n       Click to open in browser",
                command=lambda address=url: webbrowser.open_new_tab(address),
                bg="#211f20", fg=TEXT, activebackground="#2b292a", activeforeground=TEXT,
                relief="flat", bd=0, highlightthickness=1, highlightbackground="#343234",
                justify="left", anchor="w", padx=20, pady=13,
                font=("Segoe UI", 11, "bold"), cursor="hand2", width=54,
            )
            card.pack(anchor="w", pady=(0, 12), ipady=4)

        tk.Label(help_view, text="Click a support card to open the official community link.",
                 bg=APP_BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(14, 0))

    def _build_admin_view(self) -> None:
        view = tk.Frame(self.content, bg=APP_BG, padx=30, pady=30)
        self.views["Admin"] = view
        top = tk.Frame(view, bg=APP_BG)
        top.pack(fill="x")
        tk.Label(top, text="Admin Dashboard", bg=APP_BG, fg=ACCENT,
                 font=("Segoe UI", 20, "bold")).pack(side="left")
        self._button(top, "Log out", self.admin_logout, "#343944").pack(side="right")
        self._button(top, "KeyAuth Applications", self._open_keyauth_admin,
                     "#6c4df6", "#ffffff").pack(side="right", padx=(0, 10))
        self._button(
            top,
            "Admin Telegram",
            lambda: webbrowser.open_new_tab("https://t.me/Maodyna0110"),
            "#229ed9",
            "#ffffff",
        ).pack(side="right", padx=(0, 10))

        panel = tk.Frame(view, bg=PANEL_BG, padx=20, pady=18,
                         highlightthickness=1, highlightbackground="#343944")
        panel.pack(fill="x", pady=(22, 0))
        tk.Label(panel, text="DYNA-STORE Administration", bg=PANEL_BG, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(panel, text="Manage downloads, game executables, videos, and application settings.",
                 bg=PANEL_BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(7, 0))

        form = tk.Frame(view, bg=PANEL_BG, padx=20, pady=18,
                        highlightthickness=1, highlightbackground="#343944")
        form.pack(fill="x", pady=(16, 0))
        form.columnconfigure(1, weight=1)
        tk.Label(form, text="Add Game", bg=PANEL_BG, fg=ACCENT,
                 font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        self.admin_game_name = tk.StringVar()
        self.admin_game_genre = tk.StringVar(value="Action")
        self.admin_download_url = tk.StringVar()
        self.admin_youtube_url = tk.StringVar()
        self.admin_cover_image = tk.StringVar()
        self.admin_cover_url = tk.StringVar()
        self._field(form, 1, "Game name", self.admin_game_name)
        tk.Label(form, text="Genre", bg=PANEL_BG, fg=MUTED,
                 font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", padx=(0, 14), pady=6)
        genre_box = ttk.Combobox(form, textvariable=self.admin_game_genre, state="readonly",
                                 values=("Action", "Adventure", "Simulation", "Horror", "RPG",
                                         "Strategy", "Indie", "Casual", "Racing", "Sports", "Other"))
        genre_box.grid(row=2, column=1, sticky="ew", ipady=6, pady=6)
        tk.Label(form, text="Download URL", bg=PANEL_BG, fg=MUTED,
                 font=("Segoe UI", 10)).grid(row=3, column=0, sticky="w", padx=(0, 14), pady=6)
        tk.Entry(form, textvariable=self.admin_download_url, show="•", bg=INPUT_BG, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=("Segoe UI", 10)).grid(
                     row=3, column=1, sticky="ew", ipady=8, pady=6)
        self._field(form, 4, "YouTube URL", self.admin_youtube_url)
        tk.Label(form, text="Cover image", bg=PANEL_BG, fg=MUTED,
                 font=("Segoe UI", 10)).grid(row=5, column=0, sticky="w", padx=(0, 14), pady=6)
        tk.Entry(form, textvariable=self.admin_cover_image, state="readonly", readonlybackground=INPUT_BG,
                 fg=TEXT, relief="flat", font=("Segoe UI", 10)).grid(
                     row=5, column=1, sticky="ew", ipady=8, pady=6)
        self._button(form, "Upload Image", self.admin_choose_cover, "#343944").grid(
            row=5, column=2, padx=(10, 0), pady=6)
        tk.Label(form, text="JPG, PNG, or GIF • automatically converted to 600 × 900 px",
                 bg=PANEL_BG, fg=MUTED,
                 font=("Segoe UI", 9)).grid(row=6, column=1, sticky="w", pady=(0, 4))
        self._field(form, 7, "Cover Image URL", self.admin_cover_url)
        buttons = tk.Frame(form, bg=PANEL_BG)
        buttons.grid(row=8, column=1, sticky="e", pady=(12, 0))
        self._button(buttons, "Delete Selected", self.admin_delete_game, "#8b3030").pack(
            side="left", padx=(0, 8))
        self._button(buttons, "Save Game", self.admin_add_game, ACCENT, "#111111").pack(side="left")

        self.admin_catalog_status = tk.StringVar(value="")
        tk.Label(form, textvariable=self.admin_catalog_status, bg=PANEL_BG, fg=GREEN,
                 font=("Segoe UI", 9)).grid(row=9, column=0, columnspan=3, sticky="w", pady=(8, 0))

        table_frame = tk.Frame(view, bg=PANEL_BG, padx=12, pady=12,
                               highlightthickness=1, highlightbackground="#343944")
        table_frame.pack(fill="both", expand=True, pady=(16, 0))
        columns = ("name", "genre", "download", "youtube", "image")
        self.admin_catalog_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=7)
        self.admin_catalog_tree.heading("name", text="Game")
        self.admin_catalog_tree.heading("genre", text="Genre")
        self.admin_catalog_tree.heading("download", text="Download")
        self.admin_catalog_tree.heading("youtube", text="YouTube URL")
        self.admin_catalog_tree.heading("image", text="Cover")
        self.admin_catalog_tree.column("name", width=180)
        self.admin_catalog_tree.column("genre", width=90)
        self.admin_catalog_tree.column("download", width=110)
        self.admin_catalog_tree.column("youtube", width=300)
        self.admin_catalog_tree.column("image", width=90)
        scroll = tk.Scrollbar(table_frame, command=self.admin_catalog_tree.yview)
        self.admin_catalog_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.admin_catalog_tree.pack(fill="both", expand=True)
        self.admin_catalog_tree.bind("<<TreeviewSelect>>", self._load_selected_catalog_game)
        self._refresh_admin_catalog()

    def _read_catalog(self) -> list[dict[str, str]]:
        try:
            entries = json.loads(self.catalog_file.read_text(encoding="utf-8"))
            if isinstance(entries, list):
                return [item for item in entries if isinstance(item, dict)]
        except (OSError, ValueError):
            pass
        return []

    def _refresh_admin_catalog(self) -> None:
        if not hasattr(self, "admin_catalog_tree"):
            return
        for item in self.admin_catalog_tree.get_children():
            self.admin_catalog_tree.delete(item)
        custom = {str(item.get("name", "")).casefold(): item for item in self._read_catalog()}
        for title, genre in self.games:
            entry = custom.get(title.casefold(), {})
            self.admin_catalog_tree.insert("", "end", values=(
                title, entry.get("genre", genre),
                "Configured" if self.game_download_links.get(title) else "Not set",
                self.youtube_links.get(title, ""),
                "Uploaded" if self.game_cover_paths.get(title) else "Default",
            ))

    def _load_selected_catalog_game(self, _event=None) -> None:
        selection = self.admin_catalog_tree.selection()
        if not selection:
            return
        values = self.admin_catalog_tree.item(selection[0], "values")
        if len(values) >= 5:
            self.admin_game_name.set(values[0])
            self.admin_game_genre.set(values[1])
            entry = next((item for item in self._read_catalog()
                          if str(item.get("name", "")).casefold() == str(values[0]).casefold()), {})
            self.admin_download_url.set(str(entry.get("download_url", self.game_download_links.get(values[0], ""))))
            self.admin_youtube_url.set(str(entry.get("youtube_url", self.youtube_links.get(values[0], ""))))
            cover = str(entry.get("cover_image", ""))
            self.admin_cover_image.set(str(Path(__file__).with_name("assets") / "covers" / cover) if cover else "")
            self.admin_cover_url.set(str(entry.get("cover_url", "")))
            self.admin_catalog_status.set(f"Editing: {values[0]}")

    def admin_delete_game(self) -> None:
        selection = self.admin_catalog_tree.selection()
        if not selection:
            messagebox.showinfo("Delete Game", "Select a game from the list first.")
            return
        title = str(self.admin_catalog_tree.item(selection[0], "values")[0])
        if not messagebox.askyesno("Delete Game", f"Permanently remove '{title}' from DYNA-STORE?"):
            return
        entries = [item for item in self._read_catalog()
                   if str(item.get("name", "")).casefold() != title.casefold()]
        try:
            self.catalog_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
            self.game_download_links.pop(title, None)
            self.youtube_links.pop(title, None)
            self.game_cover_paths.pop(title, None)
            self.deleted_games.add(title.casefold())
            self._save_deleted_games()
            self.games = [(game, genre) for game, genre in self.games
                          if game.casefold() != title.casefold()]
            self._write_json_mapping(self.youtube_map_file, self.youtube_links)
            self._render_games()
            self._refresh_admin_catalog()
            self.admin_catalog_status.set(f"Deleted: {title}")
            self.admin_game_name.set("")
            self.admin_download_url.set("")
            self.admin_youtube_url.set("")
            self.admin_cover_image.set("")
            self.admin_cover_url.set("")
        except OSError as exc:
            messagebox.showerror("Delete Game", f"Could not update catalog:\n{exc}")

    def admin_choose_cover(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select game cover image",
            filetypes=(("Supported images", "*.png *.jpg *.jpeg *.gif"),
                       ("JPEG images", "*.jpg *.jpeg"), ("PNG images", "*.png"),
                       ("GIF images", "*.gif")),
        )
        if not selected:
            return
        try:
            width, height = self._cover_image_dimensions(Path(selected))
            self.admin_cover_image.set(selected)
            if (width, height) == (COVER_IMAGE_WIDTH, COVER_IMAGE_HEIGHT):
                detail = "ready"
            else:
                detail = f"will convert {width} × {height} to {COVER_IMAGE_WIDTH} × {COVER_IMAGE_HEIGHT}"
            self.admin_catalog_status.set(f"Selected cover: {Path(selected).name} ({detail})")
        except (OSError, ValueError, tk.TclError):
            messagebox.showerror("Cover Image", "Choose a valid JPG, JPEG, PNG, or GIF image.")

    @staticmethod
    def _cover_image_dimensions(path: Path) -> tuple[int, int]:
        if Image is not None:
            with Image.open(path) as source:
                source.verify()
            with Image.open(path) as source:
                return source.size
        if path.suffix.casefold() in {".jpg", ".jpeg"}:
            raise ValueError("JPG images require Pillow.")
        probe = tk.PhotoImage(file=str(path))
        return probe.width(), probe.height()

    def admin_add_game(self) -> None:
        title = self.admin_game_name.get().strip()
        genre = self.admin_game_genre.get().strip() or "Other"
        download_url = self.admin_download_url.get().strip()
        youtube_url = self.admin_youtube_url.get().strip()
        cover_source = self.admin_cover_image.get().strip()
        cover_url = self.admin_cover_url.get().strip()
        if not title:
            messagebox.showerror("Add Game", "Game name is required.")
            return
        if title.casefold() in self.deleted_games:
            self.deleted_games.remove(title.casefold())
            try:
                self._save_deleted_games()
            except OSError as exc:
                messagebox.showerror("Add Game", f"Could not restore game:\n{exc}")
                return
        for label, url in (("Download", download_url), ("YouTube", youtube_url)):
            if url:
                parsed = urllib.parse.urlparse(url)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    messagebox.showerror("Add Game", f"{label} URL is invalid.")
                    return
        if youtube_url:
            host = (urllib.parse.urlparse(youtube_url).hostname or "").casefold()
            if host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}:
                messagebox.showerror("Add Game", "YouTube URL must use youtube.com or youtu.be.")
                return
        if cover_url:
            parsed_cover = urllib.parse.urlparse(cover_url)
            if parsed_cover.scheme != "https" or not parsed_cover.hostname:
                messagebox.showerror("Add Game", "Cover Image URL must be a valid HTTPS URL.")
                return

        entries = self._read_catalog()
        existing_cover = ""
        existing_entry = next((item for item in entries if isinstance(item, dict)
                               and str(item.get("name", "")).casefold() == title.casefold()), {})
        if existing_entry:
            existing_cover = str(existing_entry.get("cover_image", ""))
        cover_filename = existing_cover
        if cover_url:
            try:
                cover_filename = self._download_cover_image(cover_url, title)
                cover_source = ""
            except (OSError, ValueError, urllib.error.URLError) as exc:
                messagebox.showerror("Cover Image", f"Could not download cover image:\n{exc}")
                return
        if cover_source:
            try:
                source = Path(cover_source)
                covers_dir = Path(__file__).with_name("assets") / "covers"
                covers_dir.mkdir(parents=True, exist_ok=True)
                slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-") or "game"
                cover_filename = f"custom-{slug}.png" if Image is not None else f"custom-{slug}{source.suffix.casefold()}"
                destination = covers_dir / cover_filename
                if Image is not None and ImageOps is not None:
                    source_size = self._cover_image_dimensions(source)
                    if source.resolve() != destination.resolve() or source_size != (
                        COVER_IMAGE_WIDTH, COVER_IMAGE_HEIGHT
                    ):
                        with Image.open(source) as uploaded:
                            converted = uploaded.convert("RGB").resize(
                                (COVER_IMAGE_WIDTH, COVER_IMAGE_HEIGHT),
                                resample=Image.Resampling.LANCZOS,
                            )
                            converted.save(destination, format="PNG", optimize=True)
                elif source.resolve() != destination.resolve():
                    shutil.copy2(source, destination)
            except OSError as exc:
                messagebox.showerror("Cover Image", f"Could not copy cover image:\n{exc}")
                return
        record = {"name": title, "genre": genre, "download_url": download_url,
                  "youtube_url": youtube_url, "cover_image": cover_filename,
                  "cover_url": cover_url}
        match = next((index for index, item in enumerate(entries)
                      if isinstance(item, dict) and str(item.get("name", "")).casefold() == title.casefold()), None)
        if match is None:
            entries.append(record)
        else:
            entries[match] = record
        try:
            self.catalog_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
            if not any(game.casefold() == title.casefold() for game, _ in self.games):
                self.games.append((title, genre))
            else:
                self.games = [(game, genre if game.casefold() == title.casefold() else old_genre)
                              for game, old_genre in self.games]
            if download_url:
                self.game_download_links[title] = download_url
            else:
                self.game_download_links.pop(title, None)
            if youtube_url:
                self.youtube_links[title] = youtube_url
                self._write_json_mapping(self.youtube_map_file, self.youtube_links)
            else:
                self.youtube_links.pop(title, None)
            if cover_filename:
                self.game_cover_paths[title] = cover_filename
            self._render_games()
            self._refresh_admin_catalog()
            self.admin_catalog_status.set(f"Saved: {title}")
            self.admin_game_name.set("")
            self.admin_download_url.set("")
            self.admin_youtube_url.set("")
            self.admin_cover_image.set("")
            self.admin_cover_url.set("")
        except OSError as exc:
            messagebox.showerror("Add Game", f"Could not save catalog:\n{exc}")

    def _download_cover_image(self, url: str, title: str) -> str:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname or ""
        for address in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM):
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise ValueError("Private or local image URLs are not allowed.")
        request = urllib.request.Request(url, headers={"User-Agent": "DYNA-STORE/1.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"image/png", "image/gif", "image/jpeg"}:
                raise ValueError("Image URL must return a JPG, PNG, or GIF image.")
            limit = 8 * 1024 * 1024
            data = response.read(limit + 1)
            if len(data) > limit:
                raise ValueError("Cover image is larger than 8 MB.")
        extension = {"image/png": ".png", "image/gif": ".gif", "image/jpeg": ".jpg"}[content_type]
        if extension == ".png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Downloaded file is not a valid PNG image.")
        if extension == ".gif" and not data.startswith((b"GIF87a", b"GIF89a")):
            raise ValueError("Downloaded file is not a valid GIF image.")
        if extension == ".jpg" and not data.startswith(b"\xff\xd8\xff"):
            raise ValueError("Downloaded file is not a valid JPG image.")
        slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-") or "game"
        filename = f"custom-{slug}{extension}"
        destination = Path(__file__).with_name("assets") / "covers" / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        try:
            width, height = self._cover_image_dimensions(destination)
            if (width, height) != (COVER_IMAGE_WIDTH, COVER_IMAGE_HEIGHT):
                if Image is None or ImageOps is None:
                    raise ValueError("Pillow is required to resize this cover image.")
                converted_destination = destination.with_suffix(".png")
                with Image.open(destination) as downloaded:
                    converted = downloaded.convert("RGB").resize(
                        (COVER_IMAGE_WIDTH, COVER_IMAGE_HEIGHT),
                        resample=Image.Resampling.LANCZOS,
                    )
                    converted.save(converted_destination, format="PNG", optimize=True)
                if destination != converted_destination:
                    destination.unlink(missing_ok=True)
                destination = converted_destination
                filename = destination.name
        except (OSError, ValueError, tk.TclError) as exc:
            destination.unlink(missing_ok=True)
            if isinstance(exc, ValueError) and "Pillow is required" in str(exc):
                raise
            raise ValueError("Downloaded image could not be decoded.") from exc
        return filename

    def show_keyauth_login(self, lock_app: bool = False) -> None:
        if self.keyauth_user:
            if not messagebox.askyesno("KeyAuth", "Sign out from KeyAuth?"):
                return
            threading.Thread(target=self.keyauth_client.logout, daemon=True).start()
            self.keyauth_user = None
            self.keyauth_user_var.set("KeyAuth: signed out")
            self.keyauth_button.configure(text="KeyAuth Login")
            self.auth_gate_active = True
            self.after(80, lambda: self.show_keyauth_login(lock_app=True))
            return

        dialog = tk.Toplevel(self)
        dialog.title("DYNA-STORE - KeyAuth")
        auth_bg = "#090a0c"
        auth_input = "#1b1d21"
        auth_border = "#34373d"
        auth_accent = "#ffb000"
        dialog.configure(bg=auth_bg)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        if lock_app:
            dialog.protocol("WM_DELETE_WINDOW", self._close_app)
        form = tk.Frame(dialog, bg=auth_bg, padx=42, pady=28, width=500, height=690)
        form.pack(fill="both", expand=True)
        form.grid_propagate(False)
        form.columnconfigure(1, weight=1)
        brand = tk.Canvas(form, width=300, height=190, bg=auth_bg,
                          highlightthickness=0, bd=0)
        brand.grid(row=0, column=0, columnspan=2, pady=(12, 6))
        # Circular DYNA-STORE mark based on the supplied red/blue identity.
        brand.create_oval(92, 139, 208, 151, fill="#020204", outline="", tags="logo-shadow")
        brand.create_oval(77, 2, 223, 148, outline="#f10d20", width=4,
                          tags=("logo-ring", "logo3d"))
        brand.create_oval(84, 9, 216, 141, outline="#3928b9", width=4, tags="logo3d")
        brand.create_oval(91, 16, 209, 134, fill="#f3f3f8", outline="", tags="logo3d")
        # Interlocking double-D monogram.
        brand.create_line(116, 43, 151, 43, 178, 45, 192, 57, 199, 76,
                          199, 88, 193, 106, 178, 117, 151, 119, 116, 119,
                          116, 43, fill="#f50046", width=12, joinstyle="round",
                          tags=("logo3d", "logo-red"))
        brand.create_line(130, 59, 153, 59, 168, 61, 180, 71, 183, 81,
                          181, 93, 169, 102, 153, 103, 130, 103, 130, 59,
                          fill="#f50046", width=8, joinstyle="round",
                          tags=("logo3d", "logo-red"))
        brand.create_rectangle(110, 105, 125, 120, fill="#3625ee", outline="",
                               tags="logo3d")
        brand.create_text(150, 162, text="DYNA -STORE", fill="#cbc9fa",
                          font=("Segoe UI", 15, "bold"))
        brand.create_text(150, 181, text="PLAY  •  DOWNLOAD  •  CONNECT", fill="#7f848e",
                          font=("Segoe UI", 7, "bold"))
        particle_data = [
            [32, 136, 0.7], [54, 65, 1.1], [244, 125, 0.9], [270, 48, 1.3],
            [20, 30, 0.8], [257, 174, 1.0], [232, 20, 0.6],
        ]
        particle_ids: list[int] = []
        for x, y, _speed in particle_data:
            particle_ids.append(brand.create_oval(
                x - 4, y - 4, x + 4, y + 4, fill="#5d0610", outline="#a50b1d",
                width=1, tags="particle",
            ))
        brand.tag_lower("particle")
        title_label = tk.Label(form, text="KeyAuth Access", bg=PANEL_BG, fg=ACCENT,
                               font=("Segoe UI", 17, "bold"))
        title_label.configure(bg=auth_bg, fg=auth_accent)
        title_label.grid(row=1, column=0, columnspan=2)
        tk.Label(form, text="Buy account ADMIN     •     Telegram: @Maodyna0110",
                 bg=auth_bg, fg="#aeb5c4", font=("Segoe UI", 10)).grid(
                     row=2, column=0, columnspan=2, pady=(3, 14))
        mode = tk.StringVar(value="Login")
        modes = tk.Frame(form, bg=auth_bg)
        modes.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        for label in ("Login",):
            tk.Radiobutton(modes, text=label, value=label, variable=mode, bg=auth_bg, fg=TEXT,
                           selectcolor=auth_input, activebackground=auth_bg,
                           activeforeground=TEXT, font=("Segoe UI", 14, "bold")).pack(
                               side="left", padx=(0, 12))

        values = {name: tk.StringVar() for name in ("Username", "Password", "License key", "Email", "2FA code")}
        field_widgets: dict[str, tuple[tk.Label, tk.Entry]] = {}
        for row, name in enumerate(values, start=4):
            label = tk.Label(form, text=name, bg=auth_bg, fg="#c5caD4",
                             font=("Segoe UI", 10, "bold"))
            label.grid(row=row, column=0, sticky="w", padx=(0, 18), pady=8)
            entry = tk.Entry(
                form, textvariable=values[name], show="•" if name == "Password" else "",
                bg=auth_input, fg=TEXT, insertbackground=TEXT, relief="flat", width=34,
                highlightthickness=2, highlightbackground=auth_border, highlightcolor=auth_accent,
                font=("Segoe UI", 11), selectbackground="#5940d6", selectforeground="#ffffff",
            )
            entry.grid(row=row, column=1, pady=8, ipady=8, sticky="ew")
            entry.bind("<FocusIn>", lambda _event, item=entry:
                       item.configure(highlightbackground=auth_accent))
            entry.bind("<FocusOut>", lambda _event, item=entry:
                       item.configure(highlightbackground=auth_border))
            field_widgets[name] = (label, entry)
        status = tk.StringVar()
        tk.Label(form, textvariable=status, bg=auth_bg, fg="#ffcf66", wraplength=390,
                 justify="left").grid(row=9, column=0, columnspan=2, sticky="w", pady=(10, 0))
        submit_button = self._button(form, "CONNECT KEYAUTH", lambda: submit(), "#303238")
        submit_button.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(14, 0), ipady=5)
        self._button(
            form, "Use DYNA-STORE Local Admin",
            lambda: (dialog.destroy(), self.show_admin_login(gate=lock_app)), "#202227", "#ffffff",
        ).grid(row=11, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        connecting = {"active": False}

        def finish(result: dict[str, object] | None, error: str = "") -> None:
            if not dialog.winfo_exists():
                return
            connecting["active"] = False
            submit_button.configure(state="normal")
            if error:
                normalized_error = error.casefold()
                if "no active subscription" in normalized_error:
                    status.set(
                        "This KeyAuth user has no active subscription. Assign an active license/subscription "
                        "to the user in KeyAuth, or switch to Register and redeem a valid license key."
                    )
                elif "invalid username" in normalized_error:
                    status.set(
                        "KeyAuth user was not found. Register it with a valid license key, "
                        "create the user in KeyAuth Applications, or use DYNA-STORE Local Admin below."
                    )
                else:
                    status.set(error)
                return
            info = dict((result or {}).get("info") or {})
            username = str(info.get("username") or values["Username"].get().strip() or "Licensed user")
            self.keyauth_user = info or {"username": username}
            self.auth_gate_active = False
            self.keyauth_user_var.set("KeyAuth: connected")
            self.keyauth_button.configure(text="KeyAuth Logout")
            self.status_var.set("KeyAuth connected successfully")
            dialog.destroy()

        def worker(selected_mode: str) -> None:
            try:
                if selected_mode == "Login":
                    result = self.keyauth_client.login(values["Username"].get().strip(),
                                                       values["Password"].get(), values["2FA code"].get().strip())
                elif selected_mode == "Register":
                    result = self.keyauth_client.register(values["Username"].get().strip(),
                                                          values["Password"].get(), values["License key"].get().strip(),
                                                          values["Email"].get().strip())
                else:
                    result = self.keyauth_client.license(values["License key"].get().strip(),
                                                         values["2FA code"].get().strip())
                self.after(0, finish, result, "")
            except KeyAuthError as exc:
                self.after(0, finish, None, str(exc))

        def submit() -> None:
            selected_mode = mode.get()
            if selected_mode == "Login" and not all((values["Username"].get().strip(), values["Password"].get())):
                status.set("Username and password are required.")
                return
            if selected_mode == "Register" and not all((values["Username"].get().strip(), values["Password"].get(), values["License key"].get().strip())):
                status.set("Username, password, and license key are required.")
                return
            if selected_mode == "License" and not values["License key"].get().strip():
                status.set("License key is required.")
                return
            submit_button.configure(state="disabled")
            connecting["active"] = True
            status.set("Connecting securely")
            threading.Thread(target=worker, args=(selected_mode,), daemon=True).start()

        visible_fields = {
            "Login": {"Username", "Password"},
            "Register": {"Username", "Password", "License key", "Email"},
            "License": {"License key", "2FA code"},
        }

        def update_mode(*_args: object) -> None:
            wanted = visible_fields[mode.get()]
            status.set("")
            for name, (label, entry) in field_widgets.items():
                if name in wanted:
                    label.grid()
                    entry.grid()
                else:
                    label.grid_remove()
                    entry.grid_remove()
            dialog.update_idletasks()
            first = next(field_widgets[name][1] for name in values if name in wanted)
            first.focus_set()

        mode.trace_add("write", update_mode)
        update_mode()

        # A short entrance transition keeps the authentication gate feeling
        # responsive without delaying keyboard or mouse input.
        dialog.update_idletasks()
        final_x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        final_y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        start_y = final_y + 24
        try:
            dialog.attributes("-alpha", 0.0)
        except tk.TclError:
            pass

        def animate_in(step: int = 0) -> None:
            if not dialog.winfo_exists():
                return
            progress = min(step / 12, 1.0)
            eased = 1 - (1 - progress) ** 3
            y = round(start_y + (final_y - start_y) * eased)
            dialog.geometry(f"+{final_x}+{y}")
            try:
                dialog.attributes("-alpha", eased)
            except tk.TclError:
                pass
            if progress < 1:
                dialog.after(16, animate_in, step + 1)

        logo_motion = {"scale": 1.0}

        def animate_title(step: int = 0) -> None:
            if not dialog.winfo_exists():
                return
            glow = (math.sin(step / 10) + 1) / 2
            color = f"#f5{int(150 + 28 * glow):02x}{int(35 + 25 * glow):02x}"
            title_label.configure(fg=color)
            if str(submit_button.cget("state")) != "disabled":
                pulse = int(36 + 22 * glow)
                submit_button.configure(bg=f"#{pulse:02x}{pulse:02x}{int(pulse + 4):02x}")
            if connecting["active"]:
                status.set(f"Connecting securely{'.' * ((step // 5) % 4)}")
            # Perspective coin rotation: compress the X axis as the logo turns
            # edge-on, then change its lighting while its reverse side passes.
            rotation = step / 18
            face = math.cos(rotation)
            scale_x = 0.12 + 0.88 * abs(face)
            brand.scale("logo3d", 150, 75, scale_x / logo_motion["scale"], 1)
            logo_motion["scale"] = scale_x
            front = face >= 0
            brand.itemconfigure("logo-ring", outline="#ff3045" if front else "#7b1225",
                                width=5 if abs(face) > .75 else 3)
            brand.itemconfigure("logo-red", fill="#f50046" if front else "#8d1432")
            shadow_width = 45 + int(55 * abs(face))
            shadow_shift = int(8 * math.sin(rotation))
            brand.coords("logo-shadow", 150 - shadow_width + shadow_shift, 139,
                         150 + shadow_width + shadow_shift, 151)
            pulse = (math.sin(step / 7) + 1) / 2
            for index, (particle_id, particle) in enumerate(zip(particle_ids, particle_data)):
                particle[1] -= particle[2]
                particle[0] += math.sin(step / 13 + index) * .25
                if particle[1] < 3:
                    particle[1] = 187
                radius = 3 + 2 * ((math.sin(step / 6 + index * 1.7) + 1) / 2)
                brand.coords(particle_id, particle[0] - radius, particle[1] - radius,
                             particle[0] + radius, particle[1] + radius)
                red = int(90 + 90 * ((math.sin(step / 8 + index) + 1) / 2))
                brand.itemconfigure(particle_id, fill=f"#{red:02x}0712")
            if str(submit_button.cget("state")) != "disabled":
                button_red = int(92 + 42 * pulse)
                submit_button.configure(bg=f"#{button_red:02x}0912",
                                        activebackground="#a30c19")
            dialog.after(45, animate_title, step + 1)

        dialog.bind("<Return>", lambda _event: submit())
        dialog.after(0, animate_in)
        dialog.after(220, animate_title)

    def show_admin_login(self, gate: bool = False) -> None:
        setup = not self.admin_file.is_file()
        dialog = tk.Toplevel(self)
        dialog.title("Create Local Admin" if setup else "DYNA-STORE Local Admin Login")
        dialog.configure(bg=PANEL_BG)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        if gate:
            dialog.protocol("WM_DELETE_WINDOW", self._close_app)

        frame = tk.Frame(dialog, bg=PANEL_BG, padx=28, pady=24)
        frame.pack()
        tk.Label(frame, text="Create Local Admin Password" if setup else "DYNA-STORE Local Admin Login",
                 bg=PANEL_BG, fg=ACCENT, font=("Segoe UI", 16, "bold")).grid(
                     row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))
        tk.Label(frame, text="Username", bg=PANEL_BG, fg=MUTED).grid(row=1, column=0, sticky="w", pady=6)
        username = tk.StringVar()
        user_entry = tk.Entry(frame, textvariable=username, show="•", bg=INPUT_BG, fg=TEXT,
                              insertbackground=TEXT, relief="flat", width=30)
        user_entry.grid(row=1, column=1, ipady=7, padx=(12, 0), pady=6)
        tk.Label(frame, text="Password", bg=PANEL_BG, fg=MUTED).grid(row=2, column=0, sticky="w", pady=6)
        password = tk.StringVar()
        password_entry = tk.Entry(frame, textvariable=password, show="•", bg=INPUT_BG,
                                  fg=TEXT, insertbackground=TEXT, relief="flat", width=30)
        password_entry.grid(row=2, column=1, ipady=7, padx=(12, 0), pady=6)
        confirm = tk.StringVar()
        if setup:
            tk.Label(frame, text="Confirm", bg=PANEL_BG, fg=MUTED).grid(row=3, column=0, sticky="w", pady=6)
            tk.Entry(frame, textvariable=confirm, show="•", bg=INPUT_BG, fg=TEXT,
                     insertbackground=TEXT, relief="flat", width=30).grid(
                         row=3, column=1, ipady=7, padx=(12, 0), pady=6)

        error = tk.StringVar()
        tk.Label(frame, textvariable=error, bg=PANEL_BG, fg="#ff6b6b").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        def submit() -> None:
            user = username.get().strip()
            secret = password.get()
            if setup:
                if user != ADMIN_USERNAME:
                    error.set(f"Username must be {ADMIN_USERNAME}.")
                    return
                if len(secret) < 8:
                    error.set("Password must contain at least 8 characters.")
                    return
                if secret != confirm.get():
                    error.set("Passwords do not match.")
                    return
                salt = secrets.token_bytes(16)
                digest = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, 300_000)
                try:
                    self.admin_file.write_text(json.dumps({
                        "username": ADMIN_USERNAME, "salt": salt.hex(), "password_hash": digest.hex(),
                        "iterations": 300_000,
                    }, indent=2), encoding="utf-8")
                except OSError as exc:
                    error.set(str(exc))
                    return
            elif not self._verify_admin(user, secret):
                error.set("Incorrect username or password.")
                password.set("")
                return
            self.admin_authenticated = True
            self.auth_gate_active = False
            dialog.destroy()
            self._show_view("Admin")

        self._button(frame, "Create Admin" if setup else "Login", submit, ACCENT, "#111111").grid(
            row=5, column=1, sticky="e", pady=(15, 0))
        self._button(frame, "Open KeyAuth Website", self._open_keyauth_admin,
                     "#6c4df6", "#ffffff").grid(row=5, column=0, sticky="w", pady=(15, 0))
        password_entry.bind("<Return>", lambda _event: submit())
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        password_entry.focus_set()

    def _verify_admin(self, username: str, password: str) -> bool:
        try:
            data = json.loads(self.admin_file.read_text(encoding="utf-8"))
            salt = bytes.fromhex(data["salt"])
            expected = bytes.fromhex(data["password_hash"])
            iterations = int(data.get("iterations", 300_000))
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
            return username == data.get("username") and hmac.compare_digest(actual, expected)
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def _open_keyauth_admin(self) -> None:
        try:
            webbrowser.open_new_tab("https://keyauth.cc/app/")
            self.status_var.set("Opened KeyAuth Applications admin login")
        except webbrowser.Error as exc:
            messagebox.showerror("KeyAuth Applications", str(exc))

    def admin_logout(self) -> None:
        self.admin_authenticated = False
        self.status_var.set("Admin logged out")
        self._show_view("Browse")

    def _field(self, parent: tk.Widget, row: int, label: str, variable: tk.StringVar,
               browse: bool = False, masked: bool = False) -> None:
        tk.Label(parent, text=label, bg=PANEL_BG, fg=MUTED,
                 font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=6)
        entry = tk.Entry(parent, textvariable=variable, bg=INPUT_BG, fg=TEXT,
                         insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
                         show="•" if masked else "", highlightthickness=1,
                         highlightbackground=INPUT_BG, highlightcolor=ACCENT)
        entry.grid(row=row, column=1, sticky="ew", ipady=8, pady=6)
        entry.bind("<FocusIn>", lambda _e: entry.configure(highlightbackground=ACCENT))
        entry.bind("<FocusOut>", lambda _e: entry.configure(highlightbackground=INPUT_BG))
        if browse:
            self._button(parent, "Browse", self.choose_folder, "#3b404c").grid(
                row=row, column=2, padx=(10, 0), pady=6)

    @staticmethod
    def _button(parent: tk.Widget, text: str, command, bg: str, fg: str = TEXT) -> tk.Button:
        button = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                           activebackground=bg, activeforeground=fg, relief="flat",
                           padx=16, pady=7, cursor="hand2", font=("Segoe UI", 10, "bold"))
        if bg.startswith("#") and len(bg) == 7:
            rgb = tuple(int(bg[index:index + 2], 16) for index in (1, 3, 5))
            hover = "#" + "".join(f"{min(255, int(value + (255 - value) * .16)):02x}" for value in rgb)
            button.bind("<Enter>", lambda _e: button.configure(bg=hover)
                        if str(button.cget("state")) != "disabled" else None)
            button.bind("<Leave>", lambda _e: button.configure(bg=bg)
                        if str(button.cget("state")) != "disabled" else None)
        return button

    def _animate_ui(self) -> None:
        try:
            self.animation_phase = (self.animation_phase + 1) % 240
            wave = (math.sin(self.animation_phase / 12) + 1) / 2
            orange = (245, int(145 + 30 * wave), int(30 + 12 * wave))
            accent = "#" + "".join(f"{value:02x}" for value in orange)
            self.logo_label.configure(fg="#FF2B00")
            glow = (
                255,
                int(145 + 48 * wave),
                int(22 + 34 * (1 - wave)),
            )
            glow_color = "#" + "".join(f"{value:02x}" for value in glow)
            for widget in getattr(self, "animated_font_widgets", ()):
                if widget.winfo_exists():
                    widget.configure(fg=glow_color)
            shimmer = (math.sin(self.animation_phase / 9) + 1) / 2
            self.video_banner.configure(
                fg=f"#ff{int(195 + 60 * (1 - shimmer)):02x}{int(55 + 200 * (1 - shimmer)):02x}"
            )
            active_page = getattr(self, "current_page", "")
            for page, button in self.nav_buttons.items():
                if page == active_page:
                    button.configure(fg=accent)
            self.play_icon.configure(fg=accent, font=("Segoe UI Symbol", int(54 + 4 * wave)))

            hero_bg = f"#{int(42 + 12 * wave):02x}{int(27 + 9 * wave):02x}13"
            self.detail_hero.configure(bg=hero_bg)
            self.hero_title_label.configure(bg=hero_bg, fg=f"#{int(105 + 28 * wave):02x}542b")

            if self.worker and self.worker.is_alive():
                ttk.Style(self).configure("TProgressbar", background=accent)
            else:
                ttk.Style(self).configure("TProgressbar", background=ACCENT)
            self.after(60, self._animate_ui)
        except tk.TclError:
            return

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.output_var.get())
        if folder:
            self.output_var.set(folder)

    def start_download(self) -> None:
        if not self.keyauth_user:
            messagebox.showwarning("KeyAuth Required", "Log in to KeyAuth before downloading a game.")
            self.show_keyauth_login(lock_app=True)
            return
        url = self.url_var.get().strip()
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            messagebox.showerror("Invalid URL", "Enter a valid http:// or https:// URL.")
            return
        output = Path(self.output_var.get()).expanduser()
        try:
            output = self._writable_download_folder(output)
        except OSError as exc:
            messagebox.showerror("Folder error", str(exc))
            return

        self.cancel_event.clear()
        self.pause_event.clear()
        self.retry_archive = None
        self.extract_again_button.configure(state="disabled")
        self.progress_var.set(0)
        self.data_progress_var.set(0)
        self.install_progress_var.set(0)
        self.install_percent_var.set("0%")
        self.download_speed_var.set("0 bps")
        self.download_peak_var.set("0 bps")
        self.disk_speed_var.set("0 bps")
        self.download_amount_var.set("0.0 MB / -- MB")
        self._peak_download_speed = 0.0
        self._installation_active = False
        self.download_progress_var.set("0%  •  0.00 MB / -- MB")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.pause_button.configure(state="normal", text="II")
        self.status_var.set("Downloading…")
        args = (url, self.name_var.get().strip() or "Download", output, self.extract_var.get())
        self.worker = threading.Thread(target=self._download_worker, args=args, daemon=True)
        self.worker.start()

    def extract_again(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        archive_info = getattr(self, "retry_archive", None)
        if not archive_info:
            return
        archive, destination, display_name = archive_info
        if not archive.is_file():
            self.retry_archive = None
            self.extract_again_button.configure(state="disabled")
            messagebox.showerror("Extract Again", f"Archive no longer exists: {archive}")
            return
        self.cancel_event.clear()
        self.pause_event.clear()
        self.extract_again_button.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.install_progress_var.set(0)
        self.install_percent_var.set("0%")
        self.worker = threading.Thread(
            target=self._extract_again_worker,
            args=(archive, destination, display_name),
            daemon=True,
        )
        self.worker.start()

    def _extract_again_worker(self, archive: Path, destination: Path, display_name: str) -> None:
        try:
            self._emit("installing", archive.name)
            self._emit("log", (display_name, f"Retrying extraction from {archive}", "normal"))
            if zipfile.is_zipfile(archive):
                self._safe_extract(archive, destination, display_name)
            else:
                destination.mkdir(parents=True, exist_ok=True)
                self._extract_external(archive, destination, display_name)
                self._emit("install_progress", 100)
                self._remove_unwanted_files(destination, display_name)
            archive.unlink()
            executable = self._find_game_executable(destination)
            self._emit("library_add", (display_name, str(executable) if executable else "", str(destination)))
            self._emit("extract_retry_clear", None)
            self._emit("log", (display_name, "Extraction complete", "success"))
            self._emit("done", "Download complete")
        except Cancelled:
            self._emit("log", (display_name, "Extraction cancelled; archive kept for retry", "error"))
            self._emit("done", "Cancelled")
        except Exception as exc:
            self._emit("log", (display_name, f"ERROR: {exc}", "error"))
            self._emit("done", "Extraction failed")

    def _writable_download_folder(self, requested: Path) -> Path:
        """Return a writable folder on the drive selected by the user."""
        requested = requested.resolve()
        try:
            requested.mkdir(parents=True, exist_ok=True)
            self._verify_folder_is_writable(requested)
            return requested
        except OSError as requested_error:
            drive_root = Path(requested.anchor)
            candidates = [(drive_root / "DYNA-STORE").resolve()]
            if requested.drive.casefold() == Path.home().drive.casefold():
                candidates.append((Path.home() / "Downloads" / "DYNA-STORE").resolve())

            fallback = None
            fallback_error: OSError = requested_error
            for candidate in candidates:
                if candidate == requested:
                    continue
                try:
                    candidate.mkdir(parents=True, exist_ok=True)
                    self._verify_folder_is_writable(candidate)
                    fallback = candidate
                    break
                except OSError as exc:
                    fallback_error = exc

            if fallback is None:
                raise OSError(
                    f"Cannot write to drive {requested.drive or requested.anchor}. "
                    "Choose a folder on that drive where your Windows account has write permission "
                    f"({fallback_error})."
                ) from fallback_error

            self.output_var.set(str(fallback))
            if self.settings_language.get() == "Khmer":
                warning = (
                    f"Windows មិនអនុញ្ញាតឱ្យរក្សាទុកត្រង់៖\n{requested}\n\n"
                    f"ហ្គេមនឹងត្រូវរក្សាទុកក្នុង drive ដដែល ត្រង់៖\n{fallback}"
                )
                title = "បានប្តូរថតទាញយក"
            else:
                warning = (
                    f"Windows does not allow DYNA-STORE to write directly to:\n{requested}\n\n"
                    f"The download will stay on the selected drive and be saved to:\n{fallback}"
                )
                title = "Download folder changed"
            messagebox.showwarning(title, warning)
            return fallback

    @staticmethod
    def _verify_folder_is_writable(folder: Path) -> None:
        probe = folder / f".quickplay-write-test-{secrets.token_hex(8)}"
        try:
            with probe.open("xb"):
                pass
        finally:
            try:
                probe.unlink()
            except FileNotFoundError:
                pass

    def cancel_download(self) -> None:
        self.cancel_event.set()
        self.pause_event.clear()
        self.status_var.set("Cancelling…")

    def toggle_pause_download(self) -> None:
        if not self.worker or not self.worker.is_alive():
            return
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_button.configure(text="II")
            self.status_var.set("Downloading…")
            self._emit("log", (self.name_var.get() or "Download", "Download resumed", "success"))
        else:
            self.pause_event.set()
            self.pause_button.configure(text=">")
            self.status_var.set("Download paused")
            self._emit("log", (self.name_var.get() or "Download", "Download paused by user", "normal"))

    def _schedule_download_tooltip(self, _event=None) -> None:
        self._hide_download_tooltip()
        if str(self.pause_button.cget("state")) == "normal":
            self.download_tooltip_after = self.after(400, self._show_download_tooltip)

    def _show_download_tooltip(self) -> None:
        self.download_tooltip_after = None
        if str(self.pause_button.cget("state")) != "normal":
            return
        tip = tk.Toplevel(self)
        tip.overrideredirect(True)
        tip.configure(bg="#d8d8d8")
        label = tk.Label(tip, text="Resume download" if self.pause_event.is_set()
                         else "Pause download", bg="#d8d8d8", fg="#454545",
                         padx=9, pady=6, font=("Segoe UI", 9))
        label.pack()
        tip.update_idletasks()
        x = self.pause_button.winfo_rootx() - tip.winfo_width() + self.pause_button.winfo_width()
        y = self.pause_button.winfo_rooty() - tip.winfo_height() - 8
        tip.geometry(f"+{x}+{y}")
        self.download_tooltip = tip

    def _hide_download_tooltip(self, _event=None) -> None:
        if self.download_tooltip_after is not None:
            self.after_cancel(self.download_tooltip_after)
            self.download_tooltip_after = None
        if self.download_tooltip is not None:
            self.download_tooltip.destroy()
            self.download_tooltip = None

    def _emit(self, kind: str, value: object) -> None:
        self.events.put((kind, value))

    def _download_worker(self, url: str, display_name: str, output: Path, extract: bool,
                         retry_count: int = 0) -> None:
        partial: Path | None = None
        metadata: Path | None = None
        try:
            self._emit("log", (display_name, "Resolving download link", "normal"))
            request = urllib.request.Request(url, headers={"User-Agent": "DYNA-STORE/1.0"})
            with contextlib.ExitStack() as responses:
                response = responses.enter_context(urllib.request.urlopen(request, timeout=30))
                final_url = response.geturl()
                filename = self._filename(response, final_url)
                filename = self._brand_download_filename(filename)
                target = output / filename
                partial = target.with_suffix(target.suffix + ".part")
                metadata = Path(str(partial) + ".json")
                validator = response.headers.get("ETag") or response.headers.get("Last-Modified")
                saved = {}
                if partial.exists() and metadata.exists():
                    try:
                        saved = json.loads(metadata.read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        pass
                offset = 0
                range_total = 0
                if (partial.exists() and partial.stat().st_size and validator
                        and saved.get("url") == url and saved.get("final_url") == final_url
                        and saved.get("validator") == validator):
                    offset = partial.stat().st_size
                    range_request = urllib.request.Request(
                        final_url,
                        headers={"User-Agent": "DYNA-STORE/1.0", "Range": f"bytes={offset}-",
                                 "If-Range": validator},
                    )
                    response.close()
                    try:
                        resumed = responses.enter_context(urllib.request.urlopen(range_request, timeout=30))
                        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)",
                                             resumed.headers.get("Content-Range", ""))
                        if resumed.status == 206 and match and int(match.group(1)) == offset:
                            response = resumed
                            range_total = int(match.group(3))
                            self._emit("log", (display_name, f"Resuming at {self._size(offset)}", "normal"))
                        else:
                            offset = 0
                            resumed.close()
                            response = responses.enter_context(urllib.request.urlopen(request, timeout=30))
                    except urllib.error.HTTPError as exc:
                        if exc.code != 416:
                            raise
                        offset = 0
                        response = responses.enter_context(urllib.request.urlopen(request, timeout=30))
                total = range_total or (int(response.headers.get("Content-Length", 0)) + offset)
                metadata.write_text(json.dumps({"url": url, "final_url": final_url,
                                                "validator": validator}), encoding="utf-8")
                self._emit("download_stats", (offset, total, 0.0))
                self._emit("log", (display_name, f"Download started → {target}", "normal"))
                downloaded = offset
                started = time.monotonic()
                last_update = started
                with partial.open("ab" if offset else "wb") as stream:
                    while True:
                        if self.cancel_event.is_set():
                            raise Cancelled()
                        while self.pause_event.is_set():
                            if self.cancel_event.wait(0.1):
                                raise Cancelled()
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        stream.write(chunk)
                        downloaded += len(chunk)
                        now = time.monotonic()
                        if now - last_update >= 0.2 or (total and downloaded >= total):
                            percent = downloaded * 100 / total if total else 0
                            speed = (downloaded - offset) / max(now - started, 0.01)
                            self._emit("progress", percent)
                            self._emit("download_stats", (downloaded, total, speed))
                            self._emit("status", f"{percent:.0f}%  •  {self._size(downloaded)}  •  {self._size(speed)}/s")
                            last_update = now
                if total and downloaded != total:
                    raise IOError(
                        f"Incomplete download: received {self._size(downloaded)} of "
                        f"{self._size(total)}. Check the download link and try again."
                    )
                if not downloaded:
                    raise IOError("The download server returned an empty file.")
                final_speed = (downloaded - offset) / max(time.monotonic() - started, 0.01)
                self._emit("download_stats", (downloaded, total or downloaded, final_speed))
                if target.suffix.casefold() == ".zip" and not zipfile.is_zipfile(partial):
                    raise ValueError(
                        f"Downloaded file is not a valid ZIP archive: {partial}. "
                        "Check the download link or server; the partial file was kept."
                    )
                partial.replace(target)
                metadata.unlink(missing_ok=True)

            if target.suffix.casefold() == ".zip" and not zipfile.is_zipfile(target):
                raise ValueError(
                    f"{target.name} is not a valid ZIP archive. The server may have returned "
                    "an error page or an incomplete file. Check the download URL. "
                    f"The file was kept at {target}."
                )
            self._emit("log", (display_name, f"Download finished ({self._size(target.stat().st_size)})", "success"))
            installation = target
            archive_type = target.suffix.casefold()
            external_archive = archive_type in {".rar", ".7z", ".tar", ".tgz", ".gz", ".bz2", ".xz"}
            if extract and (zipfile.is_zipfile(target) or external_archive):
                folder_name = re.sub(r"\.(?:part\d+|tar)$", "", target.stem, flags=re.IGNORECASE)
                destination = output / folder_name
                self._emit("extract_retry_available", (target, destination, display_name))
                self._emit("installing", target.name)
                if zipfile.is_zipfile(target):
                    self._safe_extract(target, destination, display_name)
                else:
                    destination.mkdir(parents=True, exist_ok=True)
                    self._emit("log", (display_name, f"Starting {archive_type[1:].upper()} extraction → {destination}", "normal"))
                    self._extract_external(target, destination, display_name)
                    self._emit("install_progress", 100)
                    self._emit("log", (display_name, "Extraction complete", "success"))
                    self._remove_unwanted_files(destination, display_name)
                target.unlink()
                self._emit("extract_retry_clear", None)
                installation = destination
                self._emit("log", (display_name, f"Removed archive: {target.name}", "success"))

            executable: Path | None = None
            if installation.is_dir():
                executable = self._find_game_executable(installation)
            elif installation.suffix.casefold() == ".exe" and installation.is_file():
                executable = installation
            self._emit("library_add", (display_name, str(executable) if executable else "", str(installation)))
            self._emit("progress", 100)
            self._emit("log", (display_name, "Everything is OK", "success"))
            self._emit("done", "Download complete")
        except Cancelled:
            if partial and partial.exists():
                partial.unlink()
            if metadata:
                metadata.unlink(missing_ok=True)
            self._emit("log", (display_name, "Download cancelled", "error"))
            self._emit("done", "Cancelled")
        except urllib.error.HTTPError as exc:
            if exc.code == 410:
                message = (
                    "This download link has expired (HTTP 410 Gone). "
                    "The catalog administrator must replace it with a new direct-download URL."
                )
                self._emit("log", (display_name, f"ERROR: {message}", "error"))
                self._emit("download_error", ("Download link expired", message))
                self._emit("done", "Download link expired")
            else:
                message = f"The download server returned HTTP {exc.code}: {exc.reason}"
                self._emit("log", (display_name, f"ERROR: {message}", "error"))
                self._emit("download_error", ("Download server error", message))
                self._emit("done", "Download failed")
        except Exception as exc:
            reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
            transient = isinstance(reason, (TimeoutError, ConnectionResetError,
                                            ConnectionAbortedError, BrokenPipeError))
            if transient and retry_count < 4 and not self.cancel_event.is_set():
                delay = 2 ** (retry_count + 1)
                self._emit("log", (display_name,
                    f"Connection interrupted ({exc}). Retrying in {delay}s "
                    f"({retry_count + 1}/4); downloaded bytes are saved.", "normal"))
                self._emit("status", f"Connection interrupted; retrying in {delay}s...")
                if self.cancel_event.wait(delay):
                    self._emit("done", "Cancelled")
                    return
                self._download_worker(url, display_name, output, extract, retry_count + 1)
                return
            self._emit("log", (display_name, f"ERROR: {exc}", "error"))
            if partial and partial.exists():
                self._emit("log", (display_name, f"Partial download kept for retry: {partial}", "normal"))
            self._emit("done", "Download failed")

    def _safe_extract(self, archive: Path, destination: Path, name: str) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        root = destination.resolve()
        self._emit("log", (name, f"Starting extraction → {destination}", "normal"))
        with zipfile.ZipFile(archive) as zipped:
            members = zipped.infolist()
            supported = {
                zipfile.ZIP_STORED,
                zipfile.ZIP_DEFLATED,
                zipfile.ZIP_BZIP2,
                zipfile.ZIP_LZMA,
            }

            # Validate every output path before either Python or an external
            # extractor is allowed to write anything.
            for member in members:
                target = (destination / member.filename).resolve()
                if root != target and root not in target.parents:
                    raise ValueError(f"Unsafe ZIP path blocked: {member.filename}")

            unsupported = sorted({member.compress_type for member in members} - supported)
            seven_zip = self._find_seven_zip()
            if seven_zip:
                self._emit("log", (
                    name,
                    "Using 7-Zip for fast, multithreaded extraction",
                    "normal",
                ))
                self._extract_external(archive, destination, name, seven_zip=seven_zip)
                self._emit("install_progress", 100)
                self._emit("log", (name, "Extraction complete", "success"))
                self._remove_unwanted_files(destination, name)
                return

            if unsupported and (unsupported != [93] or zstandard is None):
                methods = ", ".join(map(str, unsupported))
                raise RuntimeError(
                    f"ZIP method {methods} is not supported by this installation. "
                    "Install 7-Zip or use a DYNA-STORE build with Zstandard support."
                )

            total = max(len(members), 1)
            for index, member in enumerate(members, 1):
                if self.cancel_event.is_set():
                    raise Cancelled()
                if member.compress_type == 93:
                    self._extract_zstandard_member(archive, member, (destination / member.filename).resolve())
                else:
                    zipped.extract(member, destination)
                percent = index * 100 / total
                self._emit("install_progress", percent)
                self._emit("log", (name, f"{percent:.0f}% {index}/{total} - {member.filename}", "normal"))
        self._emit("log", (name, "Extraction complete", "success"))
        self._remove_unwanted_files(destination, name)

    def _extract_zstandard_member(self, archive: Path, member: zipfile.ZipInfo, target: Path) -> None:
        if zstandard is None:
            raise RuntimeError("Zstandard support is not installed.")
        if member.flag_bits & 1:
            raise RuntimeError("Encrypted ZIP entries are not supported.")
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open("rb") as source:
            source.seek(member.header_offset)
            header = source.read(30)
            if len(header) != 30 or header[:4] != b"PK\x03\x04":
                raise ValueError(f"Invalid ZIP header for {member.filename}")
            filename_length, extra_length = struct.unpack_from("<HH", header, 26)
            source.seek(filename_length + extra_length, os.SEEK_CUR)
            compressed = _LimitedReader(source, member.compress_size)
            checksum = 0
            size = 0
            with zstandard.ZstdDecompressor().stream_reader(compressed) as reader:
                with target.open("wb") as output:
                    while chunk := reader.read(1024 * 1024):
                        if self.cancel_event.is_set():
                            raise Cancelled()
                        output.write(chunk)
                        checksum = zlib.crc32(chunk, checksum)
                        size += len(chunk)
            if size != member.file_size or checksum != member.CRC:
                target.unlink(missing_ok=True)
                raise ValueError(f"ZIP entry failed integrity check: {member.filename}")

    def _remove_unwanted_files(self, destination: Path, name: str) -> None:
        """Silently remove known promotional files after extraction."""
        unwanted_names = {
            "ankergames - free pre-installed pc games.url",
            "read me.txt",
            "run me!.bat",
            "skidrowreloaded.com",
            "skidrowreloaded.com.txt",
        }
        for path in destination.rglob("*"):
            if not path.is_file() or path.name.casefold() not in unwanted_names:
                continue
            try:
                path.unlink()
            except OSError as exc:
                self._emit("log", (name, f"Could not remove {path.name}: {exc}", "error"))

    @staticmethod
    def _find_seven_zip() -> str | None:
        seven_zip = shutil.which("7z") or shutil.which("7zz") or shutil.which("7za")
        if not seven_zip:
            app_directory = Path(__file__).resolve().parent
            executable_directory = Path(sys.executable).resolve().parent
            for candidate in (
                app_directory / "7z.exe",
                app_directory / "7-Zip" / "7z.exe",
                executable_directory / "7z.exe",
                executable_directory / "7-Zip" / "7z.exe",
                Path(os.environ.get("ProgramFiles", "")) / "7-Zip" / "7z.exe",
                Path(os.environ.get("ProgramFiles(x86)", "")) / "7-Zip" / "7z.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "7-Zip" / "7z.exe",
            ):
                if candidate.is_file():
                    seven_zip = str(candidate)
                    break
        return seven_zip

    def _extract_external(
        self,
        archive: Path,
        destination: Path,
        name: str,
        seven_zip: str | None = None,
    ) -> None:
        seven_zip = seven_zip or self._find_seven_zip()
        if seven_zip:
            command = [seven_zip, "x", str(archive), f"-o{destination}", "-y", "-mmt=on", "-bsp1"]
            extractor = "7-Zip"
        else:
            winrar = shutil.which("UnRAR") or shutil.which("WinRAR")
            if not winrar:
                for candidate in (
                    Path(os.environ.get("ProgramFiles", "")) / "WinRAR" / "UnRAR.exe",
                    Path(os.environ.get("ProgramFiles(x86)", "")) / "WinRAR" / "UnRAR.exe",
                    Path(os.environ.get("ProgramFiles", "")) / "WinRAR" / "WinRAR.exe",
                    Path(os.environ.get("ProgramFiles(x86)", "")) / "WinRAR" / "WinRAR.exe",
                ):
                    if candidate.is_file():
                        winrar = str(candidate)
                        break
            tar = shutil.which("tar")
            is_rar = archive.suffix.casefold() == ".rar"
            if tar and not is_rar:
                command = [tar, "-xf", str(archive), "-C", str(destination)]
                extractor = "Windows tar"
            elif winrar:
                if Path(winrar).name.casefold() == "winrar.exe":
                    command = [
                        winrar, "x", "-ibck", "-inul", "-o+",
                        str(archive), str(destination) + os.sep,
                    ]
                    extractor = "WinRAR (background)"
                else:
                    command = [winrar, "x", "-inul", "-o+", str(archive), str(destination) + os.sep]
                    extractor = "UnRAR"
            elif tar:
                command = [tar, "-xf", str(archive), "-C", str(destination)]
                extractor = "Windows tar"
            else:
                raise RuntimeError(
                    f"No extractor is available for {archive.suffix.upper()} files. "
                    "Install 7-Zip or WinRAR and try again."
                )

        self._emit("log", (name, f"Running {extractor}…", "normal"))
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        assert process.stdout is not None
        def report_output(line: str) -> None:
            line = line.strip()
            if not line:
                return
            if extractor == "7-Zip":
                match = re.search(r"(?:^|\s)(\d{1,3})%", line)
                if match:
                    self._emit("install_progress", min(99, int(match.group(1))))
                    return
            self._emit("log", (name, line, "normal"))

        while process.poll() is None:
            if self.cancel_event.is_set():
                process.terminate()
                process.wait()
                raise Cancelled()
            report_output(process.stdout.readline())

        for line in process.stdout.read().splitlines():
            report_output(line)
        if process.returncode:
            raise RuntimeError(
                f"{extractor} could not extract this archive (exit code {process.returncode}). "
                "The archive may be damaged, password-protected, or use an unsupported method."
            )

    @staticmethod
    def _filename(response, url: str) -> str:
        disposition = response.headers.get("Content-Disposition", "")
        candidate = ""

        # RFC 5987 form: filename*=UTF-8''my%20file.zip
        encoded = re.search(r"filename\*\s*=\s*([^;]+)", disposition, re.IGNORECASE)
        if encoded:
            value = encoded.group(1).strip().strip('"')
            if "''" in value:
                _charset, value = value.split("''", 1)
            candidate = urllib.parse.unquote(value)

        # Traditional form: filename="my file.zip"
        if not candidate:
            plain = re.search(r"filename\s*=\s*(?:\"([^\"]+)\"|([^;]+))", disposition, re.IGNORECASE)
            if plain:
                candidate = (plain.group(1) or plain.group(2)).strip()

        if not candidate:
            candidate = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name

        # Some servers incorrectly put the RFC 5987 prefix in filename=.
        if candidate.upper().startswith("UTF-8''"):
            candidate = urllib.parse.unquote(candidate[7:])
        candidate = os.path.basename(candidate) or "download.bin"
        return "".join(c for c in candidate if c not in '<>:"/\\|?*') or "download.bin"

    @staticmethod
    def _brand_download_filename(filename: str) -> str:
        # Correct the malformed duplicate name returned for Schedule I.
        filename = re.sub(
            r"Schedule\.I(?:chedule\.I)+",
            "Schedule.I",
            filename,
            flags=re.IGNORECASE,
        )
        filename = re.sub(
            r"[-_. ]*SteamRIP(?:\.com)?",
            "-DYNA-STORE",
            filename,
            flags=re.IGNORECASE,
        )
        return re.sub("ankergames", "DYNA-STORE", filename, flags=re.IGNORECASE)

    @staticmethod
    def _size(value: float) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}"
            value /= 1024
        return "0 B"

    @staticmethod
    def _format_bit_rate(bits_per_second: float) -> str:
        for unit in ("bps", "Kbps", "Mbps", "Gbps"):
            if bits_per_second < 1000 or unit == "Gbps":
                return f"{bits_per_second:.1f} {unit}" if bits_per_second else "0 bps"
            bits_per_second /= 1000

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    name, message, tag = value  # type: ignore[misc]
                    stamp = datetime.now().strftime("%H:%M:%S")
                    line = f"[{stamp}] [INFO] [{name}] {message}\n"
                    self.log_text.configure(state="normal")
                    self.log_text.insert("end", line, tag)
                    self.log_text.see("end")
                    self.log_text.configure(state="disabled")
                elif kind == "progress":
                    self.progress_var.set(float(value))
                    self.data_progress_var.set(float(value))
                elif kind == "status":
                    self.status_var.set(str(value))
                elif kind == "download_stats":
                    downloaded, total, bytes_per_second = value  # type: ignore[misc]
                    speed = max(0.0, float(bytes_per_second) * 8)
                    self._peak_download_speed = max(self._peak_download_speed, speed)
                    self.download_speed_var.set(self._format_bit_rate(speed))
                    self.download_peak_var.set(self._format_bit_rate(self._peak_download_speed))
                    self.disk_speed_var.set(self._format_bit_rate(speed))
                    percent = downloaded * 100 / total if total else 0
                    self.data_progress_var.set(min(100, percent))
                    if not self._installation_active:
                        self.install_progress_var.set(0)
                        self.install_percent_var.set("0%")
                    total_text = f"{total / (1024 * 1024):.2f} MB" if total else "-- MB"
                    self.download_amount_var.set(
                        f"{downloaded / (1024 * 1024):.1f} MB / {total_text}"
                    )
                    self.download_progress_var.set(
                        f"{percent:.0f}%  •  {downloaded / (1024 * 1024):.2f} MB / {total_text}"
                    )
                elif kind == "installing":
                    self._installation_active = True
                    self.progress_var.set(0)
                    self.install_progress_var.set(0)
                    self.install_percent_var.set("0%")
                    self.download_speed_var.set("0 bps")
                    self.disk_speed_var.set("0 bps")
                    if self.settings_language.get() == "Khmer":
                        self.status_var.set("កំពុងដំឡើង…")
                        self.download_progress_var.set("កំពុងដំឡើង… 0%")
                    else:
                        self.status_var.set("Installing…")
                        self.download_progress_var.set("Installing… 0%")
                    self.pause_button.configure(state="disabled", text="II")
                elif kind == "extract_retry_available":
                    self.retry_archive = value
                elif kind == "extract_retry_clear":
                    self.retry_archive = None
                    self.extract_again_button.configure(state="disabled")
                elif kind == "install_progress":
                    self._installation_active = True
                    percent = float(value)
                    self.progress_var.set(percent)
                    self.install_progress_var.set(percent)
                    self.install_percent_var.set(f"{percent:.0f}%")
                    label = "កំពុងដំឡើង" if self.settings_language.get() == "Khmer" else "Installing"
                    self.download_progress_var.set(f"{label}… {percent:.0f}%")
                elif kind == "library_add":
                    title, executable, installation = value  # type: ignore[misc]
                    if executable:
                        self.game_executables[str(title)] = str(executable)
                        self._save_game_mappings()
                        if hasattr(self, "library_grid"):
                            self._render_library()
                        self.status_var.set(f"Added to My Library: {title}")
                    else:
                        self._emit("log", (
                            str(title),
                            f"Downloaded to {installation}, but no game EXE was found; use My Library → Re-scan folder",
                            "normal",
                        ))
                elif kind == "done":
                    self.status_var.set(str(value))
                    self.download_speed_var.set("0 bps")
                    self.disk_speed_var.set("0 bps")
                    if str(value) == "Download complete":
                        self.progress_var.set(100)
                        self.data_progress_var.set(100)
                        if self._installation_active:
                            self.install_progress_var.set(100)
                            self.install_percent_var.set("100%")
                        if self.settings_language.get() == "Khmer":
                            self.status_var.set("បានដំឡើងរួចរាល់")
                            self.download_progress_var.set("បានដំឡើងរួចរាល់ • 100%")
                        else:
                            complete_text = "Installation complete" if self._installation_active else "Download complete"
                            self.status_var.set(complete_text)
                            self.download_progress_var.set(f"{complete_text} • 100%")
                    self.start_button.configure(
                        state="disabled" if str(value) == "Download link expired" else "normal"
                    )
                    self.cancel_button.configure(state="disabled")
                    self.extract_again_button.configure(
                        state="normal" if getattr(self, "retry_archive", None)
                        and self.retry_archive[0].is_file() else "disabled"
                    )
                    self.pause_event.clear()
                    self.pause_button.configure(state="disabled", text="II")
                elif kind == "download_error":
                    title, message = value  # type: ignore[misc]
                    messagebox.showerror(str(title), str(message))
                elif kind == "google_login":
                    profile = value  # type: ignore[assignment]
                    self.google_user = profile  # type: ignore[assignment]
                    label = profile.get("name") or profile.get("email")  # type: ignore[union-attr]
                    self.google_user_var.set(str(label))
                    self.google_button.configure(state="normal", text="Sign out")
                    self.status_var.set("Signed in with Google")
                elif kind == "google_error":
                    self.google_button.configure(state="normal", text="Sign in with Google")
                    self.status_var.set("Google sign-in failed")
                    messagebox.showerror("Google Sign-In", str(value))
                elif kind == "youtube_preview":
                    title, data = value  # type: ignore[misc]
                    if (title == getattr(self, "selected_game", "") and Image is not None
                            and ImageTk is not None and not self.youtube_stream_playing):
                        picture = Image.open(io.BytesIO(data)).convert("RGB")
                        picture = ImageOps.fit(picture, (720, 300), method=Image.Resampling.LANCZOS)
                        picture = ImageEnhance.Brightness(picture).enhance(1.35)
                        picture = ImageEnhance.Contrast(picture).enhance(1.08)
                        self.youtube_preview_image = ImageTk.PhotoImage(picture)
                        self.youtube_preview_label.configure(image=self.youtube_preview_image)
                        self.detail_video_var.set("Click ▶ to watch on YouTube")
                elif kind == "youtube_preview_error":
                    title, error = value  # type: ignore[misc]
                    if title == getattr(self, "selected_game", ""):
                        self.detail_video_var.set(f"YouTube preview unavailable: {error}")
                elif kind == "youtube_stream_ready":
                    title, capture = value  # type: ignore[misc]
                    self.youtube_stream_resolving = False
                    if title != getattr(self, "selected_game", ""):
                        capture.release()
                        continue
                    self.youtube_stream_capture = capture
                    self.youtube_stream_playing = True
                    self.play_icon.place_forget()
                    self.detail_video_var.set("Playing in DYNA-STORE (video only)")
                    self._update_youtube_stream()
                elif kind == "youtube_stream_error":
                    title, error = value  # type: ignore[misc]
                    self.youtube_stream_resolving = False
                    if title == getattr(self, "selected_game", ""):
                        self.detail_video_var.set("Could not play video in DYNA-STORE")
                        messagebox.showerror("YouTube Player", str(error))
                elif kind == "youtube_auth_required":
                    title, url = value  # type: ignore[misc]
                    self.youtube_stream_resolving = False
                    if title != getattr(self, "selected_game", ""):
                        continue
                    allowed = messagebox.askyesno(
                        "YouTube Sign-In Required",
                        "YouTube requires signed-in browser cookies for this video.\n\n"
                        "Allow DYNA-STORE/yt-dlp to read your Chrome cookies for this playback? "
                        "Cookies will not be exported or saved by DYNA-STORE.\n\n"
                        "Choose No to open the official YouTube player instead.",
                    )
                    if allowed:
                        self.youtube_cookie_browser = "chrome"
                        self.youtube_stream_resolving = True
                        self.detail_video_var.set("Retrying with Chrome sign-in…")
                        threading.Thread(target=self._resolve_youtube_stream,
                                         args=(title, url), daemon=True).start()
                    else:
                        self.detail_video_var.set("Opening official YouTube player…")
                        webbrowser.open(url)
        except queue.Empty:
            pass
        self.after(80, self._drain_events)


if __name__ == "__main__":
    QuickPlay().mainloop()

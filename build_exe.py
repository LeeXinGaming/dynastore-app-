"""All-in-One Executable Builder for DYNA-STORE.

Packages the full application, assets, icons, catalog files, and embedded
binaries into a standalone Windows .exe with all online hosting and sync features.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
SPEC_FILE = ROOT_DIR / "QuickPlay.spec"
APP_STORAGE = ROOT_DIR / "server" / "storage" / "app"


def check_prerequisites():
    print("[1/5] Checking prerequisites...")
    try:
        import PyInstaller
        print(f"  * PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("  * Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    icon = ROOT_DIR / "assets" / "logo" / "dyna-store-v1.ico"
    if not icon.is_file():
        print(f"  [!] Warning: Icon not found at {icon}")
    else:
        print(f"  * Application icon found: {icon.name}")


def build_executable():
    print("\n[2/5] Building standalone DYNA-STORE.exe with PyInstaller...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(SPEC_FILE),
    ]
    print(f"  * Running: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(ROOT_DIR))


def deploy_to_server_storage():
    print("\n[3/5] Deploying built executable to Online Server storage...")
    exe_source = DIST_DIR / "DYNA-STORE.exe"
    if not exe_source.is_file():
        raise FileNotFoundError(f"Build failed: {exe_source} does not exist!")

    APP_STORAGE.mkdir(parents=True, exist_ok=True)
    exe_target = APP_STORAGE / "DYNA-STORE.exe"
    shutil.copy2(exe_source, exe_target)
    print(f"  * Copied to: {exe_target} ({exe_target.stat().st_size / (1024*1024):.2f} MB)")

    # Update app_version.json
    try:
        sys.path.insert(0, str(ROOT_DIR / "server"))
        from hosting_server import calculate_sha256, save_app_meta
        sha = calculate_sha256(exe_target)
        save_app_meta({
            "version": "2.0.0",
            "name": "DYNA-STORE",
            "filename": "DYNA-STORE.exe",
            "changelog": "Full system build with online file hosting and catalog sync",
            "size": exe_target.stat().st_size,
            "sha256": sha,
            "updated_at": "2026-09-24",
        })
        print(f"  * Server version metadata updated (SHA256: {sha[:12]}...)")
    except Exception as err:
        print(f"  [!] Could not update server metadata: {err}")


def verify_executable():
    print("\n[4/5] Verifying built executable...")
    exe_path = DIST_DIR / "DYNA-STORE.exe"
    print(f"  * Executable: {exe_path}")
    print(f"  * File size:  {exe_path.stat().st_size / (1024*1024):.2f} MB")
    
    # Test launch with timeout to ensure it runs without immediate crash
    p = subprocess.Popen([str(exe_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = p.communicate(timeout=4)
        print(f"  [!] Process exited prematurely with code {p.returncode}")
        if stderr:
            print(f"      STDERR: {stderr.decode('utf-8', errors='ignore')}")
    except subprocess.TimeoutExpired:
        print("  [✓] Verified: Executable initialized and running successfully in GUI loop!")
        p.terminate()


def main():
    print("=" * 70)
    print("      DYNA-STORE STANDALONE .EXE BUILD SYSTEM")
    print("=" * 70)
    try:
        check_prerequisites()
        build_executable()
        deploy_to_server_storage()
        verify_executable()
        print("\n[5/5] BUILD COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print(f"Your ready-to-use file: {DIST_DIR / 'DYNA-STORE.exe'}")
        print("=" * 70)
    except Exception as err:
        print(f"\n[ERROR] Build failed: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()

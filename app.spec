# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Video Downloader.

Builds a standalone Windows executable with bundled Deno and FFmpeg.
"""

from PyInstaller.utils.hooks import collect_data_files
import sys
from pathlib import Path

block_cipher = None

# Get project root
project_root = Path(SPECPATH)

# Data files to bundle
datas = []

# Add config example if it exists
if (project_root / 'config.example.toml').exists():
    datas.append((str(project_root / 'config.example.toml'), '.'))
elif (project_root / 'config.toml').exists():
    datas.append((str(project_root / 'config.toml'), '.'))

# External executables to bundle
binaries = []
if (project_root / 'bin' / 'deno.exe').exists():
    binaries.append((str(project_root / 'bin' / 'deno.exe'), 'bin'))
if (project_root / 'bin' / 'ffmpeg.exe').exists():
    binaries.append((str(project_root / 'bin' / 'ffmpeg.exe'), 'bin'))
if (project_root / 'bin' / 'ffprobe.exe').exists():
    binaries.append((str(project_root / 'bin' / 'ffprobe.exe'), 'bin'))

# Collect CustomTkinter data files
datas += collect_data_files('customtkinter')

a = Analysis(
    ['src/video_downloader/__main__.py'],
    pathex=[str(project_root), str(project_root / 'src')],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'yt_dlp',
        'yt_dlp.extractor',
        'yt_dlp.extractor.youtube',
        'yt_dlp.extractor.vimeo',
        'yt_dlp.extractor.common',
        'yt_dlp.postprocessor',
        'customtkinter',
        'typer',
        'rich',
        'PIL',
        'PIL._tkinter_finder',
    ],
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=['hooks/runtime_hook.py'] if (project_root / 'hooks' / 'runtime_hook.py').exists() else [],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
        'mypy',
        'ruff',
        'unittest',
        'test',
        'setuptools',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VideoDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'resources' / 'icon.ico') if (project_root / 'resources' / 'icon.ico').exists() else None,
    version='file_version_info.txt' if Path('file_version_info.txt').exists() else None,
    uac_admin=False,
    manifest=str(project_root / 'resources' / 'app.manifest') if (project_root / 'resources' / 'app.manifest').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['deno.exe', 'ffmpeg.exe', 'ffprobe.exe'],  # Don't compress large binaries
    name='VideoDownloader',
)

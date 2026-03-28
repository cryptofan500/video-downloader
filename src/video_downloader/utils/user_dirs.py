# src/video_downloader/utils/user_dirs.py
"""
Windows Known Folder resolution via Shell API.

Uses SHGetKnownFolderPath to get the REAL Downloads folder location,
even if relocated by the user, OneDrive, or Group Policy.
"""

import ctypes
import sys
from pathlib import Path


def get_windows_downloads_folder() -> Path:
    """Get the user's Downloads folder via the Windows Shell API.

    Uses SHGetKnownFolderPath with GUID {374DE290-123F-4565-9164-39C4925E467B}.
    Falls back to Path.home() / "Downloads" on failure or non-Windows.

    Returns:
        Path to the user's real Downloads folder.
    """
    if sys.platform != "win32":
        return Path.home() / "Downloads"

    try:

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        # Downloads folder GUID: {374DE290-123F-4565-9164-39C4925E467B}
        downloads_guid = GUID(
            0x374DE290,
            0x123F,
            0x4565,
            (ctypes.c_ubyte * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B),
        )

        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32

        path_ptr = ctypes.c_wchar_p()

        # SHGetKnownFolderPath(rfid, dwFlags=0, hToken=None, ppszPath)
        result = shell32.SHGetKnownFolderPath(
            ctypes.byref(downloads_guid),
            0,  # KF_FLAG_DEFAULT
            None,  # Current user
            ctypes.byref(path_ptr),
        )

        if result == 0:  # S_OK
            path = path_ptr.value
            ole32.CoTaskMemFree(path_ptr)  # CRITICAL: prevent memory leak
            if path:
                return Path(path)

    except OSError:
        pass

    # Fallback
    return Path.home() / "Downloads"


def get_downloads_folder() -> Path:
    """Cross-platform Downloads folder resolution.

    Returns:
        Path to Downloads folder (uses home dir as last resort).
    """
    downloads = get_windows_downloads_folder()
    if not downloads.exists():
        downloads = Path.home() / "Downloads"
    if not downloads.exists():
        downloads = Path.home()
    return downloads

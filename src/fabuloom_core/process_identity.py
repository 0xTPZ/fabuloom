"""Non-destructive process identity queries for job supervision.

Windows PID values are reusable.  A PID probe must therefore never be used as
the identity of a process by itself, especially before a cancellation request.
The Windows implementation opens a limited-information handle, reads the
exit state, creation time and image basename, and closes the handle.  Unix
keeps the usual ``kill(pid, 0)`` existence probe while adding a procfs start
token when available.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _valid_pid(pid: object) -> int | None:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return None
    return pid


def _identity_matches(actual: dict[str, Any] | None, expected: dict[str, Any] | None) -> bool:
    if actual is None:
        return False
    if expected is None:
        return True
    compared = False
    for key in ("pid", "creation_time_100ns", "start_time_ticks", "image_name"):
        if key in expected:
            compared = True
            if actual.get(key) != expected.get(key):
                return False
    return compared


def _windows_process_identity(pid: int) -> dict[str, Any] | None:
    """Query a Windows process without sending it a signal."""

    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME)]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)) or exit_code.value != STILL_ACTIVE:
            return None
        creation = FILETIME()
        exit_time = FILETIME()
        kernel_time = FILETIME()
        user_time = FILETIME()
        if not kernel32.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel_time), ctypes.byref(user_time)):
            return None
        buffer_size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(buffer_size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(buffer_size)):
            return None
        image_name = Path(buffer.value[: buffer_size.value]).name.casefold()
        creation_time = (int(creation.dwHighDateTime) << 32) | int(creation.dwLowDateTime)
        return {"pid": pid, "creation_time_100ns": creation_time, "image_name": image_name}
    finally:
        kernel32.CloseHandle(handle)


def _unix_process_identity(pid: int) -> dict[str, Any] | None:
    """Check Unix process existence and use procfs start time when present."""

    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return None
    identity: dict[str, Any] = {"pid": pid}
    stat_path = Path(f"/proc/{pid}/stat")
    if stat_path.is_file():
        try:
            tail = stat_path.read_text(encoding="utf-8", errors="replace").rsplit(")", 1)[1].split()
            identity["start_time_ticks"] = int(tail[19])
        except (OSError, ValueError, IndexError):
            pass
    exe_path = Path(f"/proc/{pid}/exe")
    try:
        identity["image_name"] = Path(os.readlink(exe_path)).name.casefold()
    except (OSError, ValueError):
        pass
    return identity


def process_identity(pid: object) -> dict[str, Any] | None:
    """Return a non-destructive identity token, or ``None`` if unavailable."""

    valid = _valid_pid(pid)
    if valid is None:
        return None
    if os.name == "nt":
        return _windows_process_identity(valid)
    return _unix_process_identity(valid)


def process_is_alive(pid: object, expected_identity: dict[str, Any] | None = None) -> bool:
    """Return whether PID exists and, when supplied, is the same process."""

    actual = process_identity(pid)
    return _identity_matches(actual, expected_identity)


__all__ = ["process_identity", "process_is_alive"]

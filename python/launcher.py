"""Launch the 32-bit Rust host DLL and return its protocol connection."""
import ctypes
import os
import secrets
import subprocess
from eloquence_native import NativeHostConnection

def launch(dll_path):
    """Return (process, connection); call off the UI thread with a timeout."""
    dll_path = os.path.abspath(dll_path)
    if not os.path.isfile(dll_path):
        raise FileNotFoundError(dll_path)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    get_dir = kernel.GetSystemWow64DirectoryW
    get_dir.argtypes = (ctypes.c_wchar_p, ctypes.c_uint)
    get_dir.restype = ctypes.c_uint
    size = get_dir(None, 0)
    if not size:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_unicode_buffer(size + 1)
    if not get_dir(buffer, len(buffer)):
        raise ctypes.WinError(ctypes.get_last_error())
    key = secrets.token_bytes(16)
    proc = subprocess.Popen([os.path.join(buffer.value, "rundll32.exe"),
        dll_path + ",EloquenceHost", "--auth-key", key.hex()],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        return proc, NativeHostConnection(proc.stdout, proc.stdin, key)
    except BaseException:
        proc.kill()
        proc.wait()
        raise

"""
Run this app as a background process so it never competes with a game.
Windows only. Failures are logged and ignored.
"""

import ctypes
import os

_BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
_PROCESS_POWER_THROTTLING = 4        # ProcessPowerThrottling info class
_THROTTLING_EXECUTION_SPEED = 0x1    # "Efficiency mode" (EcoQoS)


class _PowerThrottlingState(ctypes.Structure):
    _fields_ = [
        ("Version", ctypes.c_uint32),
        ("ControlMask", ctypes.c_uint32),
        ("StateMask", ctypes.c_uint32),
    ]


def lower_priority():
    """Below-normal CPU priority, plus efficiency mode where supported."""
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel32.SetPriorityClass.restype = ctypes.c_int
        kernel32.SetProcessInformation.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
        ]
        kernel32.SetProcessInformation.restype = ctypes.c_int
        process = kernel32.GetCurrentProcess()
    except Exception as e:
        print(f"[Perf] Could not lower priority: {e}")
        return

    priority_ok = bool(kernel32.SetPriorityClass(process, _BELOW_NORMAL_PRIORITY_CLASS))

    try:
        state = _PowerThrottlingState(1, _THROTTLING_EXECUTION_SPEED, _THROTTLING_EXECUTION_SPEED)
        eco_ok = bool(kernel32.SetProcessInformation(
            process, _PROCESS_POWER_THROTTLING, ctypes.byref(state), ctypes.sizeof(state),
        ))
    except Exception:
        eco_ok = False  # older Windows without this API

    print(f"[Perf] Background mode - priority: {'ok' if priority_ok else 'failed'}, "
          f"efficiency: {'ok' if eco_ok else 'not available'}")

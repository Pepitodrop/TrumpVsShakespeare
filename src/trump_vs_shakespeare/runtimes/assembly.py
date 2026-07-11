from __future__ import annotations

import ctypes
import os
from pathlib import Path


class AssemblyRuntimeError(RuntimeError):
    """Raised when the mandatory native combat library is unavailable."""


class AssemblyCombatRuntime:
    def __init__(self, library_path: str | Path):
        path = Path(library_path)
        if not path.is_file():
            raise AssemblyRuntimeError(f"Assembly combat library not found: {path}")
        self.path = path
        self._lib = ctypes.CDLL(str(path))
        self._lib.tvs_next_random.argtypes = [ctypes.c_uint64]
        self._lib.tvs_next_random.restype = ctypes.c_uint64
        self._lib.tvs_hit.argtypes = [ctypes.c_int32, ctypes.c_int32]
        self._lib.tvs_hit.restype = ctypes.c_int32
        self._lib.tvs_compute_damage.argtypes = [
            ctypes.c_int32,
            ctypes.c_int32,
            ctypes.c_int32,
            ctypes.c_int32,
        ]
        self._lib.tvs_compute_damage.restype = ctypes.c_int32

    @classmethod
    def discover(cls) -> AssemblyCombatRuntime:
        candidates = []
        if configured := os.getenv("TVS_NATIVE_LIB"):
            candidates.append(Path(configured))
        package_file = Path(__file__).resolve()
        candidates.extend(
            [
                Path.cwd() / "native" / "libcombat.so",
                package_file.parents[3] / "native" / "libcombat.so",
                Path("/app/native/libcombat.so"),
            ]
        )
        for candidate in candidates:
            if candidate.is_file():
                return cls(candidate)
        raise AssemblyRuntimeError(
            "No native Assembly combat library found. Run scripts/build_native.sh or use Docker."
        )

    def next_random(self, seed: int) -> int:
        return int(self._lib.tvs_next_random(ctypes.c_uint64(seed)))

    def hit(self, accuracy: int, roll: int) -> bool:
        return bool(self._lib.tvs_hit(int(accuracy), int(roll)))

    def compute_damage(self, base: int, guard: int, roll: int, crit_chance: int = 10) -> int:
        return int(self._lib.tvs_compute_damage(int(base), int(guard), int(roll), int(crit_chance)))

"""Cached telemetry; unavailable GPU counters are represented by null, never zero."""
import ctypes as c
from ctypes import wintypes as w
import os
import re
import threading
import time
import psutil


class GPUCounters:
    def __init__(self):
        self.query = c.c_void_p()
        self.counters = {}
        self.dll = c.WinDLL("pdh")
        self.dll.PdhOpenQueryW.argtypes = [w.LPCWSTR, c.c_size_t, c.POINTER(c.c_void_p)]
        self.dll.PdhAddEnglishCounterW.argtypes = [c.c_void_p, w.LPCWSTR, c.c_size_t, c.POINTER(c.c_void_p)]
        self.dll.PdhCollectQueryData.argtypes = [c.c_void_p]
        self.dll.PdhGetFormattedCounterArrayW.argtypes = [c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.POINTER(w.DWORD), c.c_void_p]
        if self.dll.PdhOpenQueryW(None, 0, c.byref(self.query)):
            raise OSError("GPU counters unavailable")
        for key, path in {"engines": r"\GPU Engine(*)\Utilization Percentage",
                          "dedicated": r"\GPU Adapter Memory(*)\Dedicated Usage",
                          "shared": r"\GPU Adapter Memory(*)\Shared Usage"}.items():
            handle = c.c_void_p()
            if not self.dll.PdhAddEnglishCounterW(self.query, path, 0, c.byref(handle)):
                self.counters[key] = handle
        self.dll.PdhCollectQueryData(self.query)

    def values(self, handle):
        class Value(c.Structure):
            _fields_ = [("status", w.DWORD), ("value", c.c_double)]
        class Item(c.Structure):
            _fields_ = [("name", w.LPWSTR), ("value", Value)]
        size, count = w.DWORD(), w.DWORD()
        self.dll.PdhGetFormattedCounterArrayW(handle, 0x200, c.byref(size), c.byref(count), None)
        if not size.value:
            return []
        buffer = c.create_string_buffer(size.value)
        if self.dll.PdhGetFormattedCounterArrayW(handle, 0x200, c.byref(size), c.byref(count), buffer):
            return []
        items = c.cast(buffer, c.POINTER(Item))
        return [(items[i].name, items[i].value.value) for i in range(count.value) if items[i].value.status in (0, 1)]

    def sample(self):
        if self.dll.PdhCollectQueryData(self.query):
            return {}
        result, engines = {}, {}
        for key, handle in self.counters.items():
            for name, value in self.values(handle):
                match = re.search(r"luid_(0x[\da-f]+_0x[\da-f]+)", name, re.I)
                if not match:
                    continue
                luid = match.group(1).lower()
                record = result.setdefault(luid, {})
                if key == "engines":
                    engine = name.split("_phys_")[-1]
                    engine = engine.split("_engtype_")[0]
                    slot = engines.setdefault(luid, {})
                    slot[engine] = slot.get(engine, 0) + value
                else:
                    record[key + "_bytes"] = max(0, int(value))
        for luid, values in engines.items():
            result[luid]["utilization_percent"] = round(min(100, max(values.values(), default=0)), 1)
        return result


class Telemetry:
    def __init__(self):
        self.lock = threading.Lock()
        self.latest = {}
        self.thread = None

    def start(self):
        with self.lock:
            if self.thread is None:
                self.thread = threading.Thread(target=self._run, daemon=True)
                self.thread.start()

    def _run(self):
        process = psutil.Process()
        process.cpu_percent()
        psutil.cpu_percent()
        try:
            gpu = GPUCounters() if os.name == "nt" else None
        except Exception:
            gpu = None
        while True:
            try:
                memory = psutil.virtual_memory()
                data = {"sampled_at": time.time(), "cpu_percent": psutil.cpu_percent(),
                        "app_cpu_percent": round(process.cpu_percent() / (psutil.cpu_count() or 1), 1),
                        "ram_used_bytes": memory.used, "ram_total_bytes": memory.total,
                        "app_ram_bytes": process.memory_info().rss, "gpus": gpu.sample() if gpu else {}}
                with self.lock:
                    self.latest = data
            except Exception:
                pass
            time.sleep(1)

    def snapshot(self):
        self.start()
        with self.lock:
            return dict(self.latest)

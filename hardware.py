"""Enumerate DXGI adapters in DirectML order; classify by D3D12 UMA support."""
import ctypes as c
from ctypes import wintypes as w
import os
import uuid


class GUID(c.Structure):
    _fields_ = [("data", c.c_ubyte * 16)]

    @classmethod
    def parse(cls, value):
        return cls((c.c_ubyte * 16).from_buffer_copy(uuid.UUID(value).bytes_le))


def adapters():
    if os.name != "nt":
        return []
    class LUID(c.Structure):
        _fields_ = [("LowPart", w.DWORD), ("HighPart", w.LONG)]
    class Desc(c.Structure):
        _fields_ = [("Description", w.WCHAR * 128), ("VendorId", w.UINT), ("DeviceId", w.UINT),
                    ("SubSysId", w.UINT), ("Revision", w.UINT), ("DedicatedVideoMemory", c.c_size_t),
                    ("DedicatedSystemMemory", c.c_size_t), ("SharedSystemMemory", c.c_size_t),
                    ("AdapterLuid", LUID), ("Flags", w.UINT)]
    class Architecture(c.Structure):
        _fields_ = [("NodeIndex", w.UINT), ("TileBasedRenderer", w.BOOL), ("UMA", w.BOOL), ("CacheCoherentUMA", w.BOOL)]
    def method(obj, index, restype, *args):
        address = c.cast(obj, c.POINTER(c.POINTER(c.c_void_p))).contents[index]
        return c.WINFUNCTYPE(restype, c.c_void_p, *args)(address)
    factory = c.c_void_p()
    result = []
    dxgi = c.WinDLL("dxgi")
    d3d = c.WinDLL("d3d12")
    create = dxgi.CreateDXGIFactory1
    create.argtypes = [c.POINTER(GUID), c.POINTER(c.c_void_p)]
    create.restype = c.c_long
    iid = GUID.parse("770aae78-f26f-4dba-a829-253c83d1b387")
    if create(c.byref(iid), c.byref(factory)) < 0:
        return []
    try:
        for index in range(32):
            adapter = c.c_void_p()
            if method(factory, 12, c.c_long, w.UINT, c.POINTER(c.c_void_p))(factory, index, c.byref(adapter)) < 0:
                break
            device = c.c_void_p()
            try:
                desc = Desc()
                if method(adapter, 10, c.c_long, c.POINTER(Desc))(adapter, c.byref(desc)) < 0 or desc.Flags & 2:
                    continue
                create_device = d3d.D3D12CreateDevice
                create_device.argtypes = [c.c_void_p, w.UINT, c.POINTER(GUID), c.POINTER(c.c_void_p)]
                create_device.restype = c.c_long
                device_iid = GUID.parse("189819f1-1db6-4b57-be54-1821339b85f7")
                compatible = create_device(adapter, 0xb000, c.byref(device_iid), c.byref(device)) >= 0
                architecture = Architecture()
                classified = compatible and method(device, 13, c.c_long, w.UINT, c.c_void_p, w.UINT)(
                    device, 1, c.byref(architecture), c.sizeof(architecture)) >= 0
                luid = f"0x{desc.AdapterLuid.HighPart & 0xffffffff:08x}_0x{desc.AdapterLuid.LowPart:08x}"
                result.append({"id": f"gpu:{luid}", "name": desc.Description, "index": index,
                               "luid": luid, "kind": ("integrated" if architecture.UMA else "dedicated") if classified else "unknown",
                               "directx12": compatible, "dedicated_bytes": desc.DedicatedVideoMemory,
                               "shared_bytes": desc.SharedSystemMemory, "vendor_id": desc.VendorId})
            finally:
                if device.value:
                    method(device, 2, w.ULONG)(device)
                method(adapter, 2, w.ULONG)(adapter)
    finally:
        method(factory, 2, w.ULONG)(factory)
    return result


def inventory():
    import onnxruntime as ort
    import platform
    providers = ort.get_available_providers()
    model_exists = (__import__('pathlib').Path(__file__).parent / "models" / "yolov8n.onnx").is_file()
    devices = [{"id": "cpu", "name": platform.processor() or "CPU", "kind": "cpu",
                "provider": "CPUExecutionProvider", "available": model_exists,
                "reason": "Ready" if model_exists else "Model not packaged. Run the model export step."}]
    try:
        graphics = adapters()
    except Exception:
        graphics = []
    for adapter in graphics:
        available = model_exists and adapter["directx12"] and adapter["kind"] != "unknown" and "DmlExecutionProvider" in providers
        adapter.update(provider="DmlExecutionProvider", available=available,
                       reason="Ready for validation" if available else "Requires a packaged model, DirectML runtime, and compatible DirectX 12 driver.")
        devices.append(adapter)
    return devices

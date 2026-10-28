# Requirements

## Packaged application

| Component | Requirement / validation status |
| --- | --- |
| OS | Windows x64 on compatible Intel/AMD processors. Windows 11 is the primary tested platform. Windows ARM, Linux and macOS packages are not provided. |
| Installation | MSI or fully extracted portable ZIP in a writable local folder. |
| Runtimes | Bundled Python/dependencies. No separate Python, Node.js, Rust, Git, Docker or CUDA installation. |
| Storage | Allow for extraction, private runtime, original images, outputs and Photoshop recovery copies. Usage depends on the collection. |
| Memory | No universal app minimum has been benchmarked. Test a representative collection. Repair pauses below 512 MiB reported available in Photoshop; this guard is not Photoshop's system requirement. |
| CPU | ONNX Runtime CPU-compatible x64 hardware. Intel was tested locally; AMD acceptance is pending. |
| GPU | Compatible DirectX 12 adapter and driver for DirectML. Intel iGPU/NVIDIA tested locally; AMD remains untested. |
| Photoshop | Separate optional installation for repair only. Regular Photoshop 27.11.0 was tested on Windows. Sign in separately. |
| Network | Runtime setup is offline from the full package. Photoshop Remove may require Adobe network access. |

Packages are unsigned. Drivers and Adobe applications are not bundled. A clean
second-PC installation remains an acceptance check; every-machine compatibility is not claimed.

## Source dependencies

Use **Python 3.11 x64** in an isolated virtual environment. Choose one runtime:

| File | Purpose |
| --- | --- |
| `requirements.txt` | Pinned Windows dependencies, including `onnxruntime-directml` for CPU and supported GPU execution. |
| `requirements-cpu.txt` | Pinned alternative with `onnxruntime` for CPU-only development. |
| `package-manifest.json` | Exact offline Windows wheels, public package URLs and SHA-256 values; not the desktop version. |
| `runtime-manifest.json` | Python 3.11.9 x64 archive and checksum. |
| `desktop/package-lock.json` | Electron/build-tool lock; install with `npm ci`. |

Do not install both ONNX Runtime distributions in one environment. Packaged
inference does not require PyTorch/torchvision/Ultralytics/CUDA. Model re-export
and historical experiments require a separate Ultralytics/PyTorch/ONNX environment;
those dependencies are not part of the validated runtime lock. Normal development
uses the shipped ONNX model and checksum manifest.

## Windows builds

- Python 3.11 x64 and the selected runtime dependencies.
- Node.js **22.12+** for the locked packager; Node 24.11.1 was used locally.
- `npm ci` inside `desktop/`.
- WiX **6.0.2**, its matching UI extension and .NET prerequisites.
- Verified Python archive, manifest wheels and app-local x64 Visual C++ CRT files from an appropriately licensed build-tools installation.
- Rust/Cargo only for the optional historical launcher, not the Electron desktop build.

See [Build and release](BUILD_AND_RELEASE.md).

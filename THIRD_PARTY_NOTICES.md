# Included components

This distribution includes Python, ONNX Runtime DirectML, Pillow, NumPy, Flask,
Waitress, psutil, their pinned dependencies, and Microsoft Visual C++ runtime
redistributable DLLs. Their respective licenses and notices apply. Python's
license is included in its runtime archive; Python package license notices are
included in the dependency wheels and their installed dist-info directories.

The desktop distribution also includes Electron and its Chromium/Node.js
components. Their LICENSE and third-party notice files are shipped beside the
executable. The application icon and documentation preview are drawn by the
project's code; the preview contains synthetic artwork, not customer images.

The detection model is an ONNX export of the repository's Ultralytics YOLOv8n
weights. Exporting the model does not change its license terms.

- Python: https://docs.python.org/3/license.html
- ONNX Runtime: https://github.com/microsoft/onnxruntime/blob/main/LICENSE
- Electron: https://github.com/electron/electron/blob/main/LICENSE
- Ultralytics: https://www.ultralytics.com/license
- Visual C++ redistributable files: https://learn.microsoft.com/visualstudio/releases/2022/redistribution

Release preparation uses an installed Microsoft Visual Studio Build Tools
redistributable directory for app-local CRT deployment; no GPU driver is bundled.

No new license for the application's own source is assigned by this release.
Bundled model and component notices do not grant additional rights to Janvi
branding or replace the respective upstream terms.

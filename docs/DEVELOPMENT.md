# Development

## Processing service

From a Windows checkout, choose the DirectML runtime:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe launch.py
```

For CPU-only source development, use `requirements-cpu.txt` instead in a separate
environment. `launch.py` checks the model hash and opens a loopback service on a
free port. Use `--no-browser --port 5056` for an explicit development port.
The browser alone does not expose Electron-only folder dialogs or Photoshop IPC.

## Desktop shell

Prepare the [offline build assets](BUILD_AND_RELEASE.md) first; Electron starts
`Start.ps1 -Offline`:

```powershell
Push-Location desktop
npm ci
Pop-Location
$env:JANVI_BACKEND_ROOT = $PWD.Path
.\desktop\node_modules\.bin\electron.cmd desktop
```

Do not set `JANVI_BACKEND_ROOT` for packaged use. Packages use their own
`resources/backend`. Source and installed applications can retain different settings.

## Checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
Get-ChildItem static,desktop -Filter *.js -File | ForEach-Object {
    node --check $_.FullName
    if ($LASTEXITCODE -ne 0) { throw 'JavaScript syntax check failed' }
}
git diff --check
```

Tests use temporary/generated images and `.build` state. They cover crop geometry,
queues, jobs, export planning, logo composition, path validation and failure handling.
They do not run Photoshop or prove GPU compatibility. Do not test with customer originals.

## Source map

| Paths | Responsibility |
| --- | --- |
| `app.py`, `launch.py` | Local API, UI and service entry point. |
| `processing.py`, `jobs.py` | Batches, progress, cancellation and manifests. |
| `inference.py`, `hardware.py`, `telemetry.py` | Detector, adapter inventory and usage. |
| `subject_aware_resize.py` | Crop policy and geometry; also retains a historical standalone entry point. |
| `logo_processing.py`, `move_to_shopify.py` | Logo composition and product naming. |
| `photoshop_repair.py`, `photoshop/` | Queue metadata, JSX template and launchers. |
| `templates/`, `static/` | Guided workspace and logo editor. |
| `desktop/` | Electron window, secure preload/IPC and folder handoff. |
| `models/`, `assets/` | Model/manifest, default logo and icons. |
| `tests/`, `tools/` | Regression suite, packaging and verification. |
| `launcher/` | Optional earlier Rust browser launcher. |

Root-level normalisation, audit, rename, `test_yolo*`, `test_detect.py` and
`test_outpaint.py` files are historical experiments. They are not the maintained
desktop entry point or regression suite, and can contain local example paths.
The `.pt` weights remain for explicit model export.

## Local data

Source settings/logs live in `data/`; desktop settings/logs live in
`resources/backend/data/`. Runtime files use `.runtime/`; build caches use `.build/`.
All are excluded from Git, as are image reports and generated repair queues.
Previously tracked reports/settings are removed from current snapshots while
their local files are preserved. Git history is not rewritten.

Docker files remain for CPU service experiments. They are not a substitute for
the validated Windows desktop/Photoshop workflow.

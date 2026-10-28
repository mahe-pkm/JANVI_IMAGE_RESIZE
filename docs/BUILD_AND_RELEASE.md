# Build and release

Build from reviewed source on Windows x64. Binaries belong in GitHub Releases.
Do not distribute a working installation containing settings or runtime caches.

## Prepare assets

Use the [development environment](DEVELOPMENT.md) and run `npm ci` in `desktop/`.
Prepare:

```text
.build/
├── runtime-python.zip        # runtime-manifest.json archive
├── wheels/                  # all package-manifest.json wheels, including pip
├── redist/                  # licensed app-local x64 VC++ CRT DLLs
└── wix/wix.exe              # WiX 6.0.2; matching UI extension available
```

Download and verify the public runtime/wheels using the manifests:

```powershell
New-Item -ItemType Directory -Force .build/wheels | Out-Null
$runtime = Get-Content runtime-manifest.json -Raw | ConvertFrom-Json
Invoke-WebRequest $runtime.url -OutFile .build/runtime-python.zip
if ((Get-FileHash .build/runtime-python.zip -Algorithm SHA256).Hash -ne $runtime.sha256) {
    throw 'Python archive checksum mismatch'
}
$manifest = Get-Content package-manifest.json -Raw | ConvertFrom-Json
foreach ($wheel in $manifest.wheels) {
    $destination = Join-Path .build/wheels $wheel.file
    Invoke-WebRequest $wheel.url -OutFile $destination
    if ((Get-FileHash $destination -Algorithm SHA256).Hash -ne $wheel.sha256) {
        throw "Wheel checksum mismatch: $($wheel.file)"
    }
}
```

Install WiX from its official .NET tool distribution into `.build/wix`, with
`WixToolset.UI.wixext` 6.0.2 available. Copy the x64 CRT DLLs from an installed
Visual Studio Build Tools redistributable directory into `.build/redist`.
See [third-party notices](../THIRD_PARTY_NOTICES.md). Builders recheck the runtime
and wheel hashes. This repository does not include the build-tools installation.

## Version and build

Update `desktop/package.json` and the root/package entries in its lockfile
together. Update the changelog and desktop docs. That version controls MSI/ZIP
names; the older backend `package-manifest.json` does not. Preserve MSI upgrade identity.

Run the [development checks](DEVELOPMENT.md#checks), then:

```powershell
.\.venv\Scripts\python.exe tools/build_desktop.py
```

Expected outputs:

```text
dist/v0.6.3/
├── Janvi-Image-Studio-0.6.3-win-x64.msi
├── Janvi-Image-Studio-0.6.3-win-x64.msi.sha256
├── Janvi-Image-Studio-0.6.3-win-x64.zip
└── Janvi-Image-Studio-0.6.3-win-x64.zip.sha256
```

Staging lives in unique `.build/desktop-builds/` directories. Builders refuse to
replace an existing version. Use a new patch version when correcting a package.
Model export and the optional Rust launcher are separate, unnecessary for this build.

## Verify and deliver

1. Verify both SHA-256 sidecars, ZIP integrity and the payload; reject user data, private runtimes, customer images or secrets.
2. Check executable version/icon, native folder selection, `janvi .`, Explorer handoff, and idle shutdown.
3. Use disposable images for resize → Photoshop → logo → export. Record actual checks and gaps in `desktop/VERIFICATION.md`.
4. Check MSI upgrade data retention and portable setup from a fresh extraction. Packages are unsigned and do not auto-update.
5. Review staged source/docs, commit and push normally without rewriting history. Tag the exact release commit.
6. Create a GitHub Release with the MSI, ZIP, SHA-256 files, release notes and verification record. Use `gh release create --notes-file` to preserve Markdown.
7. Verify the published tag and asset list, then download the published binaries and compare their hashes.

Never upload `dist/` through Git or attach a working application directory.
See [Windows updates](WINDOWS_RELEASE_UPDATES.md) for the installed-app update flow.

# Desktop verification

## 0.6.3 source and release preparation — 28 October 2026

- 52 Python tests passed again in the local DirectML development environment.
- Python dependency consistency and JavaScript syntax checks passed.
- Processing, desktop launch/IPC and Photoshop repair code are unchanged from
  0.6.2. This patch updates the desktop version, documentation, source exclusions,
  CI configuration and the packaging documentation payload.
- The repository preview is synthetic SVG artwork, not a customer photograph or
  a screenshot with private filesystem paths.
- Previously tracked working settings, reports and duplicate artwork are removed
  from current snapshots, with local copies preserved. Existing Git history is
  retained. Dependencies, runtime/cache files and downloads remain untracked.

See the release's VERIFICATION.md asset for checks performed after building the
final MSI and ZIP. Previous manual workflow evidence is detailed below. No clean
second-PC or AMD hardware acceptance result is claimed for this patch.

## 0.6.2 Windows workspace and launch integration

- 52 Python tests passed. Frontend and Electron JavaScript syntax checks passed.
- New crop-frame icon is included in the desktop executable, MSI shortcut assets,
  browser favicon and workspace branding. Installed 0.6.2 executable version and
  bundled source/icon hashes matched the release staging files.
- Installed 0.6.1 completed a synthetic image through resize, the desktop
  **Open Photoshop & Repair** button, Photoshop 27.11 Remove, logo placement and
  Shopify export. The final 0.6.2 package contains the same processing code.
  Repair completed 1/1, dimensions remained 1200 x 1800, the repair checksum
  matched the saved image, and exported Product_1.png matched the logo output.
  The Adobe script warning and completion dialog were acknowledged manually.
- The generated JSX had previously completed the two padded Chartreuse Rose
  product images. Those customer source images were preserved.
- Final 0.6.2 second-instance folder handoff was checked in the desktop window.
  The installed Explorer background context-menu command was clicked and the
  app's Source Root Folder visibly changed to the selected test input folder.
- MSI 0.6.2 upgrade completed with exit code 0 and retained application data and
  the private runtime. The per-user PATH and Explorer commands were inspected.
- A fresh 0.6.1 portable extraction installed its bundled offline Python runtime
  and opened its own Electron window on this PC, without using system Python or
  Node. Final 0.6.2 ZIP integrity, source contents and MSI/ZIP SHA-256 sidecars
  were verified. A fresh-runtime launch of the exact 0.6.2 ZIP and a clean second
  Windows PC have not been tested.
- The final installed workspace screenshot is retained under
  `.build/release-proof/Janvi-Studio-0.6.2.png`. Guided steps, size controls,
  thumbnail navigation, full view and the Photoshop repair status were reviewed.

Limitations: packages remain unsigned; AMD hardware and clean-PC acceptance are
pending. Photoshop must be installed and signed in separately. Close Beta and
other documents before repair. Adobe may require script confirmation. A service
operation that hangs cannot be forcibly timed out by synchronous JSX. Generated
repair quality still requires visual review. No automatic GitHub updater is
included, and no release was pushed or published.

## 0.5.0 Photoshop padding repair

- 44 Python tests passed, including exact odd-pixel geometry, queue/index merging,
  Unicode metadata, generated-script API, reports, legacy outputs and repair locks.
- Contextual Remove manually completed on a synthetic selection in Photoshop
  27.11.0. The recorded event `removeButton` was then replayed from JSX; it returned
  after the edit completed (18.4 seconds in the first proof).
- Generated sequential runner processed PNG left/right padding, JPEG with uneven
  top/bottom padding and a nested TIFF. Filenames, dimensions and hierarchy were
  preserved. Recovery copies matched original files. PNG content outside the
  padding remained pixel-identical after clipping the generated edit layer.
- Rerunning a completed queue skipped completed outputs. A missing second file
  paused after saving the first; restoring the file and rerunning completed it
  without resubmitting the first. Diagnostic notifier was removed and its previous
  disabled setting restored. Existing user actions were not modified or shipped.
- ES3 SHA-256 proved slow for larger TIFFs. Final runner uses bounded streaming
  CRC32 + size, tested against known vectors/chunk boundaries and Python results.
  The final PNG/TIFF queue completed with matching output checksums. Python keeps
  SHA-256 in the resize manifest for auditing. PNG compression 9 reduced test
  output to about 240 KiB rather than an uncompressed 6.5 MB.
- Real app resize of two development fixtures generated one padded entry with
  exact top 562 / bottom 563 pixel bounds. Review displayed the queue and script.
- JSX runs one document at a time, rejects other open documents, checks available
  Photoshop memory and preserves per-file checkpoints. No action file required.

Limits: no representative garment acceptance batch, clean second-PC Photoshop
test, actual service outage, forced crash recovery or low-memory injection yet.
Automatic save supports JPEG/PNG/TIFF; other formats stop for manual attention.
Synchronous JSX cannot impose a hard timeout on an Adobe operation that hangs.
Retouch quality needs visual review; JPEG recompression affects encoded pixels.

## 0.4.1 sidebar hardware widgets

- Live CPU/RAM readings and selected Intel integrated/NVIDIA dedicated GPU
  readings checked in the browser; GPU widget opens processing settings.
- Readings stayed live during a controlled 250-image CPU resize job, while device
  settings were locked. Only development fixtures were processed.
- Dark/light themes and a short window around 851 x 600 CSS pixels inspected.
  Sidebar scrolls, widgets collapse, navigation remains accessible and no page
  horizontal overflow was reported. Duplicate main-panel usage cards removed.
- Counters use existing telemetry polling. Missing, invalid or stale values hide
  their meter instead of presenting a zero reading as a valid measurement.

## 0.4.0 connected workflow

- 35 Python tests passed; app, logo and workflow JavaScript syntax passed.
- Browser-driven controlled image completed resize, logo application and Shopify
  export using one selected input and one output location with no folder reselection.
- Refresh retained the connected folder configuration. Logo stage refreshed its
  preview list after resizing. Export preview found the generated logo output.
- Disabling resize and logo routed export directly to the original input;
  disabled stages were unavailable in the step bar. Full workflow was restored.
- Hardware controls collapse; custom folder/Lightroom operation remains available
  by disabling connected folders. Existing output files are preserved, not cleared.
- In-progress jobs do not resume automatically after the service restarts.
  This release does not add a per-file retry queue or a job-specific export manifest.

## 0.3.1 desktop foundation

Verified locally on Windows x64 with controlled test images:

- 35 Python tests passed; frontend and Electron JavaScript syntax checks passed.
- Standalone Electron window launched with the bundled offline Python runtime.
- Native folder dialog selected a folder; cancelling preserved the current path.
- User confirmed dragging a File Explorer folder populated the folder field.
- Logo processing displayed progress messages and saved a persistent job report.
- A 250-image CPU resize completed successfully. Closing during processing showed
  the active-job protection message. Idle shutdown stopped the local service.
- MSI 0.3.0 installed into an isolated test location. Upgrading to 0.3.1 retained
  the test data and private runtime, and reused the remembered installation path.
- Restarting 0.3.1 reused its saved local service port.
- Uninstall returned exit code 0, removed the executable and desktop shortcut,
  and retained the test data. The isolated test installation was removed.
- Final MSI/ZIP SHA-256 values match their sidecar files. ZIP integrity passed;
  its 134 entries contain no user data, installed runtime cache or node_modules.

The packages are unsigned. A genuinely clean second PC and AMD hardware remain
untested. Existing browser releases and user image folders were preserved.

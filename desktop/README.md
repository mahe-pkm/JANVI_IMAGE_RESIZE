# Janvi Image Studio 0.6.5 — Windows x64 desktop edition

Built for Buzl.

Install the MSI, then open **Janvi Image Studio** from the Start menu or desktop.
The ZIP alternative must be extracted completely into a writable local folder;
open **Janvi Image Studio.exe** inside it. This edition opens its own window.

The gold crop-frame icon identifies this release. The guided workspace includes
a large image preview, filmstrip, original toggle, zoom and full comparison view.
The default output remains 2:3 at 1200 × 1800. Choose another preset or custom
dimensions before resizing; logo placement checks the selected output dimensions.

After MSI installation, use `janvi .` in a newly opened terminal, or
`janvi "D:\Photos\Collection"`. Explorer also offers **Open with Janvi Image Studio**
on folders and folder backgrounds (under Show more options on Windows 11).
The portable ZIP has `janvi.cmd` in its root; use its full path from another folder.
Bare `janvi` in Explorer's address bar is not claimed to pass the visible folder.

First launch installs the bundled Python runtime and wheels offline. No separate
Python or Node installation is needed. A branded Janvi startup screen stays open
with progress text while local setup runs, instead of showing a blank window.
Allow a few minutes for the first setup.
The app stores its private runtime, image folders, presets and job reports under
`resources/backend/`. Keep the full folder together when using the ZIP.

Use Browse to open the Windows folder chooser attached to the app window, or drag
one folder from File Explorer onto a source/output field. Source and output must
be separate and cannot contain each other. Processing logs appear on the Logo
Placement screen; complete reports are saved under `resources/backend/data/job-logs`.

In Run Pipeline, enable **Use connected workflow folders**. Select the input
and one output location, then follow Folders, Resize, Review, Logo and Export.
The app creates Resized, With Logo and Final For Shopify under the output location.
Disable an unwanted processing stage in Folders; subsequent stages use the
appropriate earlier output or original input. Each processing step is started
explicitly, and Shopify export still requires its file preview. Folder settings
are remembered in this desktop app. Disable connected folders for custom paths
or Lightroom export. Changing paths invalidates the export preview; existing
output files remain on disk. Use a separate output location for a new collection.

Live CPU, memory and selected GPU widgets sit below the sidebar navigation.
System usage can be collapsed; the sidebar scrolls in short windows. Click the
GPU widget to open processing settings. GPU readings show total adapter use.
Unavailable or stale readings are cleared instead of displayed as current data.

After resizing, Review includes Photoshop padding repair. Resizing generates
the `.janvi` companion folder with `manual_patch_list.md`, exact bounds,
`padding_manifest.json`, and one `Repair_Padding.jsx`. The companion folder is
kept separate from the image hierarchy. Run the generated script from
Photoshop's File > Scripts > Browse, or use **Open Photoshop & Repair** in the
desktop window. The button selects a single regular Photoshop installation;
save and close a different version such as Beta first. Photoshop asks whether
to run the script; choose Yes. Keep the completion alert acknowledged so the
queue lock can be released. The app refreshes repair status automatically. It processes
one padded image at a time, saves under the same name/format, and checkpoints
completed files. No action file is required. See `resources/backend/photoshop/README.md`
for memory, recovery, supported formats and tested Photoshop version details.

Closing the app while a job is active is blocked. Finish or cancel processing,
then close the app so it can stop its local processing service. Close the app
before updating or uninstalling. The installer retains generated data/runtime
files on uninstall. It installs separately from the older browser-based package.

Supported package target: Intel/AMD Windows x64. Other PCs and GPU drivers still
need hardware testing. This package is unsigned. The code and packaging tools do
not install a GPU driver. Component notices are in the backend folder and the
Electron license files included beside the executable.

See `resources/backend/docs/INSTALLATION.md` for full first-install, update,
Photoshop, Smart App Control and troubleshooting guidance.

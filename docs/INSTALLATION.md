# Install Janvi Image Studio on Windows

Janvi Image Studio is a local Windows x64 application. The MSI and portable ZIP
already contain its Python runtime, image-processing dependencies and subject
model. You do not need to install Python, Node.js, Git, Docker or CUDA.

## Choose a package

| Package | Best for | Install method |
| --- | --- | --- |
| **MSI** | Your normal workstation | Download the Windows x64 MSI, close Janvi if it is open, then run the installer. |
| **Portable ZIP** | Testing or a machine where you do not want an installation | Extract the entire ZIP to a writable local folder. Keep every extracted file together. |

The app opens in its own window. The first launch prepares its bundled runtime
locally. The startup screen remains visible with a status message while this
happens; a first run may take a few minutes.

## First workflow

1. Open **Janvi Image Studio** from the Start menu, or run `janvi .` in a new
   Command Prompt/PowerShell window opened in the folder you want to process.
2. Select the source collection and a separate output location. Do not put one
   inside the other. You can use Browse or drag one folder onto a folder field.
3. Keep the default **2:3 · 1200 × 1800** preset, or choose a resolution before
   resizing. Review crop/padding decisions before continuing.
4. If padding is queued, choose **Open Photoshop & Repair**. Photoshop is a
   separate Adobe installation; confirm its prompt to run the repair script.
   The repair processes one image at a time and saves into the same resized copy.
5. Apply the logo, preview Shopify filenames, then export. Source images are
   preserved. New repair metadata is stored under `Resized\.janvi`, separate
   from product folders.

## Photoshop requirement

Photoshop is needed only for the optional padded-area cleanup. Use a regular
installed Photoshop version, not a second open Beta instance. Save/close other
documents before starting the batch. Adobe Remove can require the user to be
signed in and online. JPEG, PNG and TIFF can save automatically; other formats
are marked for manual review.

## Updating from an earlier Janvi release

1. Finish or cancel active work and close Janvi.
2. Download the newer MSI and install it over the existing MSI. Do not uninstall
   first. Your generated image folders are not part of the application install.
3. For portable use, extract the new ZIP into a new folder. Keep the prior copy
   until the new one opens successfully.
4. Existing root-level Photoshop queues continue to work. New queues live in
   `Resized\.janvi` so image folders remain clean.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| First launch takes time | Keep Janvi open; it is preparing the included local runtime. The startup screen should show the current stage. |
| Smart App Control blocks the app | Current packages are unsigned. Keep Smart App Control enabled; use a future publisher-signed release rather than disabling system protection. |
| GPU is unavailable | Select CPU. GPU requires a compatible DirectX 12 adapter/driver; it accelerates detection only. |
| Photoshop does not start | Close other Photoshop versions/documents and use **Open Photoshop & Repair** again. The manual fallback is Photoshop → File → Scripts → Browse, then select `Resized\.janvi\Repair_Padding.jsx`. |
| Export says a file conflicts | Janvi does not overwrite different existing files. Choose a new output folder or resolve the named conflict. |
| Export preview has a stage name | Use the connected workflow from Resize onward. The exporter refuses an unsafely generic stage folder such as `With Logo` without saved product identity. |

## Hardware support

Windows x64 Intel/AMD PCs are supported by the packaged runtime. CPU mode is the
safe baseline. Intel integrated graphics and NVIDIA DirectML were tested locally;
AMD GPU and a clean second-PC installation require acceptance testing. Linux,
macOS and Windows ARM packages are not currently provided.

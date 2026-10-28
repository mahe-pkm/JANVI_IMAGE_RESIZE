# Historical verification — 27 October 2026

This is the earlier development record. For the current desktop release, see
[desktop verification](desktop/VERIFICATION.md) and the GitHub release assets.

Scope: only the pulled `data.git` checkout. The original application and image
folders beside the checkout were not modified. No Git commit, push or deployment
was performed during that historical verification pass.

## Passed

- Shopify Lightroom preview against the supplied input and cleaned output found
  all 63 images already present at the expected paths with matching SHA-256.
  Automated tests cover native and Lightroom selection, conflicts, repeat runs,
  source preservation and rejecting a plan changed after preview. A browser sample
  export copied a test image into its parent product folder.
- Janvi defaults from the supplied preset use the bundled identical PNG with its
  full transparent canvas, top-left anchor, 15% width, 88.1% opacity and zero
  insets. Preview and batch share the same compositor. A Lightroom export has not
  been compared, so pixel-for-pixel Lightroom equivalence is not established.
- Windows native folder chooser starts successfully, but interactive selection
  and cancellation could not be checked through the automation surface. API
  handling for selection, cancellation, and failure is covered by mocked tests.
- Nested duplicate image names and extensions, empty folders, and existing
  output collision handling are covered by automated logo batch tests.

- Watermark editor layout was checked in the browser with a large live image
  preview and controls alongside it. Anchor, rotation, slider-to-number updates,
  original-image toggle and the batch action were exercised. Existing logo output
  remained available for Shopify export after a server restart. The 28-test suite
  includes rotation, old preset compatibility and JPEG logo upload.

- The default logo controls were updated from the provided Lightroom screenshot:
  top-left position, 88% opacity, size 15 and zero offsets. The interpretation of
  size as 15% of image width remains an approximation pending a reference export.

- Logo placement: 24 passing tests cover placement, opacity, input validation,
  uploaded logos, saved presets, preview-to-PNG parity, output collisions,
  unsupported hard-link fallback, folder structure, source preservation,
  corrupt-image continuation, EXIF orientation and ICC profile retention.
  The local browser workflow was exercised from preview and preset saving through
  batch processing and connecting the result to Shopify export.

- Shopify export now preserves nested and empty folders. The updated suite has
  17 passing tests, including repeated exports, collision handling and unchanged
  original image content in separate branches of the source hierarchy.

- 16 regression tests (`python -m unittest discover -s tests -v`): atomic job
  admission, cancellation retaining the worker slot, completion-based progress,
  log-buffer rollover, empty batches, Windows filename-case deduplication,
  input/output containment checks, atomic image writes, successful and failed
  export source preservation, legacy failed-copy protection, corrupt-image
  continuation, local-origin mutation checks, shared monitor placement,
  unavailable-device rejection, explicit GPU/CPU fallback rejection, and failed
  hardware jobs reaching a terminal state.
- JavaScript syntax checks for `static/app.js` and `static/monitor.js`.
- Real inference on Intel Core i7-14650HX CPU, Intel UHD integrated graphics,
  and NVIDIA GeForce RTX 5070 Laptop GPU using the shipped ONNX model.
- ONNX profiling showed CPUExecutionProvider events for CPU and
  DmlExecutionProvider events for each selected GPU.
- Comparison with the old YOLO engine on the packaged Ultralytics bus/zidane
  example photos: largest-person bounding-box IoU approximately 0.980–0.994.
  These examples are development fixtures, excluded from the release.
- Dashboard-driven integrated-GPU resize: two successful 1200 × 1800 outputs,
  persistent completion panel, correct adapter displayed, padded-image gallery
  updated, device selector locked while processing and unlocked afterward.
- Windows live CPU, RAM, GPU engine and dedicated/shared GPU memory counters.
- Rust release launcher compiled successfully.
- Offline first installation from bundled dependency wheels into private Python
  3.11.9 x64; the runtime had no PyTorch installation.
- Portable candidate HTTP resize jobs on all three devices: two outputs per
  method, verified dimensions/readability and unchanged SHA256 for source images.
- Repeat launch reused the existing server rather than opening another one.
- Moving the installed candidate into a different folder containing spaces,
  then launching it again without reinstalling its runtime.
- All 18 bundled wheels matched their SHA256 values in official PyPI index
  metadata. Python archive and ONNX model have separate SHA256 manifests.

Machine-readable development evidence is retained in ignored `.build/` files:
`device-smoke.json`, `detection-parity.json`, `provider-proof.json`, and
`portable-validation.json`.

## Limits of this verification

This is a Windows x64 portable release candidate, not a universal-hardware
certification. AMD CPU/iGPU/dGPU and a genuinely clean second PC were not
available for testing. Windows 10 and other OS/architecture variants were not
exercised. Docker compatibility files were updated but Docker was not run.
Large garment batches, apparel-specific detection/crop quality, out-of-memory
behavior and driver-reset recovery still need representative acceptance testing.
The two example photos do not establish identical detections for all inputs;
static ONNX letterboxing differs from the old dynamic rectangular preprocessing.

Processing is local. GPU inference still involves CPU image preparation and
output work. GPU usage readings are adapter-wide and can include other apps.
Live job state is held in the server process; browser refresh is supported,
process-restart job resumption is not implemented. The launcher is unsigned.

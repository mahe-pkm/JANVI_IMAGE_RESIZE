# Photoshop padding repair

Tested with the installed **Photoshop 27.11.0** on Windows x64. The exact
contextual Remove operation is `removeButton`, which was replayed from JSX and
returned after the edit completed. No .atn action or Photoshop plugin installation
is required for this implementation. Existing user actions are not modified.

## Run a batch

Windows direct launcher: double-click `Start_Photoshop_Repair.cmd` beside the
generated JSX. Its PowerShell helper selects a single regular Photoshop install
under Program Files/Adobe and passes the script directly to Photoshop.exe. Save
and close a different Photoshop version first; the launcher refuses to start if
another version is running. Photoshop may display its own script warning; choose
Yes to start. That confirmation is intentionally retained. For a custom install,
run the PS1 with `-PhotoshopPath` set to its Photoshop.exe. Manual Browse remains
available. Do not rename JSX to JS or PSJS: those extensions use different launch
or scripting environments. No registry or file association changes are needed.

The direct launcher and the installed desktop button completed a synthetic
1-image repair on regular Photoshop 27.11.0, including its native script
confirmation. The installed workflow continued through logo placement and export.

1. Complete resizing in Janvi. The resized folder contains `manual_patch_list.md`,
   `padding_manifest.json` and one generated `Repair_Padding.jsx`.
2. Open Review in Janvi to see the script path and its status. Close other
   Photoshop documents, then use **File > Scripts > Browse** in Photoshop to run
   the generated script. A downloaded copy can locate the original output folder
   on the same PC. When moving to another PC, keep the generated script and
   manifest alongside the complete resized folder hierarchy.
3. Confirm processing. The script opens one image, selects its recorded padding,
   performs Remove, clips the generated edit layer to the exact padding bounds,
   saves and validates a temporary output, then replaces the resized file under
   its existing name and extension. It closes its document before opening another.
4. Refresh Photoshop status in Janvi, review the results, and continue to Logo.

There is no fixed 500-image limit. Only indexed padded files with known bounds
and matching checksums are processed. Old filename-only indexes require a new
resize from the original files to obtain reliable bounds. Failed resize files
are not newly admitted into the queue.

## Formats, memory and recovery

- Automatic save supports JPEG (quality 12), PNG (lossless, compression 9), and
  TIFF (LZW). Other input/output formats are flagged for manual review. JPEG
  recompression can change pixels throughout the encoded image.
- The whole batch is not opened together. File hashing reads 64 KiB chunks and
  Photoshop's available memory is checked before opening each file; below
  512 MiB the queue pauses. This is a basic guard, not a prediction of how much
  memory Adobe's Remove processing will need. No global history/cache purge occurs.
- Remove may use network processing and variable time. The script waits for the
  command return and confirms an edit layer before saving. It does not advance
  after a fixed timer or automatically resubmit an uncertain cloud operation.
- **Stop after current image** takes effect between files. During Remove use
  Photoshop's own Cancel control if available. A hung Photoshop/network operation
  cannot be given a reliable hard timeout by this synchronous JSX.
- Recovery originals live beside the resized folder under
  `.janvi-photoshop-backups/<queue fingerprint>/`, outside the sources used for
  logo placement/export. Temporary rendered files also stay there. Transaction
  files inside the resized tree have non-image `.pending`/`.hold` suffixes.
- Runtime change detection uses streaming CRC32 plus byte count for speed in
  ExtendScript. The app also records SHA-256 of each resize output for auditing.
  CRC32 is for accidental changes/corruption, not adversarial tamper detection.
- The JSON report is checkpointed per file. Rerun the same script to skip outputs
  whose recorded output hashes still match and resume pending files. Missing,
  changed or unsupported files stop the queue for attention. Correct the cause
  and rerun; completed images are not submitted again.
- If Photoshop crashes, close it fully before clearing the empty
  `.janvi-photoshop-running` lock folder in the resized output. Keep the report,
  any `.hold` file and recovery copies; the next run can restore an interrupted
  rename when the checkpoint records that transaction. Do not clear the lock
  while a Photoshop run might still be active.

Processing does not guarantee visually correct reconstruction. Garments, hands,
patterns and background edges still need review. Creative Cloud access and any
required Adobe components belong to the destination machine. Photoshop itself
and credentials are not bundled. A separate clean PC, large garment collection,
real network outage and forced crash recovery have not yet been tested.

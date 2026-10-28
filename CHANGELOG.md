# Changelog

User-visible changes to Janvi Image Studio. Earlier versions below were local
development builds; 0.6.3 is the first GitHub desktop release from this checkout.

## [0.6.4] - 2026-10-28

### Added
- Branded native startup screen with local runtime and workspace status, replacing
  the blank first-launch window.
- Offline installation, update, Photoshop and troubleshooting guide.

### Changed
- New Photoshop repair queues and workflow metadata now live in `Resized\\.janvi`
  rather than beside product image folders. Existing root-level queues remain
  usable.
- Shopify export carries direct-folder product identity through the workflow and
  rejects generic stage-folder names when that identity is unavailable.

## [0.6.3] - 2026-10-28

### Added
- Public source delivery of the Windows desktop app, processing modules, Photoshop
  queue templates, regression tests, model manifest and packaging tools.
- Illustrated README, requirements, developer setup, build/release guide and changelog.
- Windows CI for CPU tests, JavaScript syntax and model checksum checks.

### Changed
- Aligned desktop version and bundled documentation for GitHub MSI/ZIP distribution.
- Documented the separate pinned CPU/DirectML dependencies and build prerequisites.
- Excluded previously tracked local settings, image reports and duplicate working
  artwork from current source snapshots; local copies are preserved.

Processing behaviour is carried forward from 0.6.2. See the verification report
for automated checks, package checks and manual workflow evidence.

## [0.6.2]
- Fixed folder handoff when another invocation opens a folder in the running app.
- Verified installed Explorer launch and terminal `janvi .` integration.

## [0.6.1]
- Improved output-size control layout and desktop workflow validation.
- Checked installed Photoshop cleanup through logo placement and export with a synthetic image.

## [0.6.0]
- Guided charcoal/gold workspace and distinct crop-frame icon.
- Filmstrip navigation, original comparison, zoom and full image review.
- Ratio/resolution presets with the existing 2:3, 1200 × 1800 default.
- Direct Photoshop launch, folder command and Explorer integration.

## [0.5.1]
- Preserved correct-ratio composition; added subject margins and padding on missing detection.
- Removed selected-folder markers from exported image names.

## [0.5.0]
- Exact padding metadata and a sequential Photoshop JSX queue.
- Per-file checkpoints, recovery copies, queue locks and repair status.

## [0.4.1]
- Collapsible sidebar CPU, RAM and selected GPU widgets.

## [0.4.0]
- Connected workflow folders, optional stages and guided stepper.

## [0.3.1]
- Reused the desktop service port for folder and theme preferences.

## [0.3.0]
- Electron window, native folder chooser, folder drop fields and logo logs.

## [0.2.1]
- Application icon for the earlier browser-based installer.

## [0.2.0]
- Portable offline setup, CPU/DirectML selection, shared progress and local export modes.

[0.6.3]: https://github.com/mahe-pkm/JANVI_IMAGE_RESIZE/releases/tag/v0.6.3

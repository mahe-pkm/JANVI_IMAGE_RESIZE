# Local releases

Downloadable MSI/ZIP files and SHA-256 files are organized under versioned
directories in `dist/`. The current Windows release is `dist/v0.6.3/`.
The `dist/` directory is excluded from Git.

Earlier root-level download paths are retained as compatibility aliases so
existing links keep working. On this NTFS workspace, version-folder entries for
the older downloads are hard links, so they do not duplicate the file contents.
Do not replace a published file in place; publish a new version or revision.

- **0.6.3:** GitHub source/release delivery, refreshed README, requirements, changelog and build instructions; same processing behaviour as 0.6.2. See CHANGELOG.md for the complete version history.
- **0.6.2:** Guided gold/charcoal workspace, filmstrip image review, new crop-frame icon, ratio/size presets, direct Photoshop launcher, folder commands and Explorer integration. Includes reliable folder handoff when the app is already open. Versions 0.6.0 and 0.6.1 were local validation builds.
- **0.5.1:** Preserve correct-ratio images, add crop safety margins, pad undetected subjects and remove selected suffixes from export names.
- **0.5.0:** Exact padding metadata, generated sequential Photoshop JSX, recovery/checkpointing and Review status.
- **0.4.1:** Sidebar CPU, RAM and selected GPU widgets; settings opened from the GPU widget.
- **0.4.0:** Connected folder workflow, guided steps and collapsible hardware controls.
- **0.3.1:** Desktop release with a remembered service port for folder/theme preferences.
- **0.3.0 candidate:** Electron desktop window, native attached folder dialog, folder drop
  fields, visible logo processing log and saved per-job reports.
- **0.2.1:** Browser-based MSI with the Janvi application icon.
- **0.2.0:** Earlier portable browser releases, including Shopify export modes.

The running browser package and historical extracted test copies have been left
at their existing locations. They may contain local settings and output files;
they are not release inputs. New builds use explicit clean staging under `.build`.

Build scripts, launcher code, frontend/backend source and lockfiles belong in Git.
Application data, virtual environments, node_modules, MSI/ZIP packages, WiX
downloads and temporary build output do not. No commit or push is performed by
the release builders.

After MSI installation, open a new terminal in the image folder and run
`janvi .`, or right-click the folder / folder background and choose
**Show more options > Open with Janvi Image Studio**. Bare `janvi` in a browser
address bar is not a supported folder command. The portable ZIP can be launched
with its executable or its bundled `janvi.cmd`.

The Photoshop button targets regular Photoshop directly without relying on JSX
file associations. Close Photoshop Beta first. If Adobe asks to run the script,
choose **Yes**, then acknowledge the completion dialog before continuing to logo
placement. Review the repaired images before proceeding. GitHub automatic
updates are not implemented in this release.

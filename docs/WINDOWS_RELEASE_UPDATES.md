# Windows release updates

Source changes and installed-app updates are separate steps. A Git push does not
update an installed MSI or a previously extracted portable ZIP.

1. Test the source and build a new version of the MSI and portable ZIP.
2. Review and commit only application source; never commit output images,
   local settings, runtime state or customer files.
3. Push the reviewed commit and create a matching Git tag and GitHub Release.
4. Attach the versioned MSI, ZIP and SHA-256 files and publish release notes.
5. MSI users close Janvi and install the new MSI. Portable users extract the new
   ZIP to a separate folder and transfer only their intended settings; keep old
   copies until the new one is verified. Image output folders remain separate.

The current app does not check GitHub or install updates automatically. GitHub
release creation and publication require a separate authorized release action.
MSI upgrades and preservation of settings need verification before a release is
offered to users. Electron's built-in autoUpdater does not directly update this
WiX MSI. Any future update checker should display the version and release notes,
verify publisher/integrity, and avoid silently replacing portable installations.

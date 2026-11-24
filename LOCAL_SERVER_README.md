# Janvi Image Studio Local Server

Built for Buzl.

This is the browser-based edition of Janvi Image Studio. It runs entirely on
your Windows PC and opens the workspace in your default browser. Images, models,
settings and processing stay local to this computer; the server only accepts
connections from `127.0.0.1`.

## Start

1. Extract the entire ZIP to a writable local folder, for example
   `C:\Janvi Image Studio Local Server`.
2. Double-click **START_JANVI_LOCAL_SERVER.cmd**.
3. Wait for the browser to open. The first run prepares the bundled offline
   runtime and can take a few minutes.
4. Keep the branded **Janvi Server Console** open while Janvi is running. Press
   **O** to reopen the browser and **Q** to stop Janvi safely after processing.

No separate Python, Node.js, Git, Docker or CUDA installation is required.

## Stop

Press **Q** in the Janvi Server Console once no processing job is active. The
separate **STOP_JANVI_LOCAL_SERVER.cmd** is available if the console was closed.
Both stop methods refuse to interrupt a running resize, logo or export job.

## Browser address

Janvi automatically chooses an available local port and opens the matching
`http://127.0.0.1:<port>` address. The port may change after a restart. Use the
browser tab opened by the launcher rather than bookmarking a port number.

## First workflow

Choose the source collection and a separate output location, then use the same
steps as the desktop edition: resize/review, Photoshop repair when padding is
queued, logo placement, and local Shopify export. The selected source images are
not changed.

## Important Windows note

This release is currently unsigned. Windows Smart App Control can block
unrecognized launchers on protected PCs. Do not disable Windows protection.
A publisher-signed release is needed for consistent use on those devices.

For processing, Photoshop repair, hardware and folder-layout details, see
`README.md` and `docs\INSTALLATION.md` in this package.

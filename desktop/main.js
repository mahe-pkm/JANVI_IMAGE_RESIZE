const {app, BrowserWindow, dialog, ipcMain, session} = require('electron');
const {spawn, execFile} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const net = require('node:net');
const {promisify} = require('node:util');
const run = promisify(execFile);
const powershellEnv = {...process.env};
delete powershellEnv.PSModulePath;

const backend = process.env.JANVI_BACKEND_ROOT || path.join(process.resourcesPath, 'backend');
const stateFile = path.join(backend, 'data', 'server.json');
const powershell = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
let mainWindow, splashWindow, origin = '', ready = false, closing = false;
let pickerOpen = false;
let repairProcess = null;
let repairLaunchTime = 0;
let pendingFolder = '';

function folderArgument(args, cwd) {
  const index = args.indexOf('--folder');
  if (index < 0 || !args[index + 1]) return '';
  try { const folder = path.resolve(cwd, args[index + 1]); return fs.statSync(folder).isDirectory() ? folder : ''; } catch (_) { return ''; }
}

async function availablePort(preferred) {
  return new Promise((resolve, reject) => {
    const socket = net.createServer();
    socket.once('error', reject);
    socket.listen(preferred, '127.0.0.1', () => { const port = socket.address().port; socket.close(() => resolve(port)); });
  });
}

function requestJson(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, {timeout: 2000}, res => {
      let data = '';
      res.on('data', chunk => { data += chunk; if (data.length > 1024 * 1024) req.destroy(); });
      res.on('end', () => { try { resolve(JSON.parse(data)); } catch (err) { reject(err); } });
    });
    req.on('timeout', () => req.destroy(new Error('Timed out')));
    req.on('error', reject);
  });
}

function authorized(event) {
  try { return event.sender === mainWindow.webContents && event.senderFrame === mainWindow.webContents.mainFrame && new URL(event.senderFrame.url).origin === origin; }
  catch (_) { return false; }
}

function createStartupScreen() {
  const markup = `<!doctype html><html><head><meta charset="utf-8"><style>
    *{box-sizing:border-box} body{margin:0;background:#17191b;color:#f7f1e5;font-family:"Segoe UI",sans-serif;overflow:hidden}
    main{height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 78% 15%,#3e3320 0,transparent 32%),radial-gradient(circle at 15% 90%,#20343a 0,transparent 34%),#17191b}
    section{width:390px;text-align:center}.mark{width:68px;height:68px;margin:0 auto 22px;border:1px solid #d6ad65;border-radius:17px;display:grid;place-items:center;color:#e6bf78;font:bold 30px Georgia;box-shadow:0 0 0 8px #d6ad6510;animation:rise .7s ease-out both}
    h1{margin:0;font:600 25px Georgia,serif;letter-spacing:.3px}.label{margin:9px 0 30px;color:#d6ad65;font-size:10px;font-weight:700;letter-spacing:2px}.track{height:3px;border-radius:4px;background:#ffffff18;overflow:hidden}.track i{display:block;width:42%;height:100%;border-radius:inherit;background:linear-gradient(90deg,transparent,#e5bd76,transparent);animation:load 1.45s ease-in-out infinite}.status{min-height:24px;margin:16px 0 0;color:#c8ccd0;font-size:13px}.credit{margin:26px 0 0;color:#8f9497;font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase}@keyframes load{from{transform:translateX(-115%)}to{transform:translateX(340%)}}@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
  </style></head><body><main><section><div class="mark">J</div><h1>Janvi Image Studio</h1><div class="label">LOCAL IMAGE WORKSPACE</div><div class="track"><i></i></div><p id="status" class="status">Preparing local image tools…</p><p class="credit">Built for Buzl</p></section></main></body></html>`;
  splashWindow = new BrowserWindow({width: 500, height: 340, frame: false, resizable: false, movable: true,
    alwaysOnTop: true, center: true, show: false, backgroundColor: '#17191b',
    webPreferences: {contextIsolation: true, nodeIntegration: false, sandbox: true}});
  splashWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(markup));
  splashWindow.once('ready-to-show', () => splashWindow && splashWindow.show());
}

function startupMessage(message) {
  if (!splashWindow || splashWindow.isDestroyed()) return;
  splashWindow.webContents.executeJavaScript(`document.getElementById('status').textContent=${JSON.stringify(message)};`).catch(() => {});
}

function closeStartupScreen() {
  if (splashWindow && !splashWindow.isDestroyed()) splashWindow.close();
  splashWindow = null;
}

async function startBackend() {
  const script = path.join(backend, 'Start.ps1');
  if (!fs.existsSync(script)) throw new Error('Bundled processing backend is missing.');
  const portFile = path.join(backend, 'data', 'desktop-port.json');
  let preferred = 0;
  try { const saved = JSON.parse(fs.readFileSync(portFile, 'utf8')).port; if (Number.isInteger(saved) && saved > 1024 && saved <= 65535) preferred = saved; } catch (_) {}
  let port;
  try { port = await availablePort(preferred); } catch (_) { port = await availablePort(0); }
  let output = '';
  startupMessage('Preparing bundled offline runtime…');
  await new Promise((resolve, reject) => {
    const child = spawn(powershell, ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script, '-Offline', '-NoBrowser', '-Port', String(port)], {cwd: backend, windowsHide: true, env: powershellEnv});
    child.stdout.on('data', data => { output = (output + data.toString()).slice(-5000); });
    child.stderr.on('data', data => { output = (output + data.toString()).slice(-5000); });
    child.on('error', reject);
    child.on('exit', code => code === 0 ? resolve() : reject(new Error(`Backend setup failed (${code}).\n${output}`)));
  });
  startupMessage('Checking local workspace…');
  const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
  const url = new URL(state.url);
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || !url.port) throw new Error('Backend returned an invalid local address.');
  origin = url.origin;
  fs.writeFileSync(portFile, JSON.stringify({port: Number(url.port)}));
  const health = await requestJson(origin + '/api/health');
  if (health.app !== 'janvi-image-resize' || !health.ready) throw new Error('Backend is not ready.');
  startupMessage('Opening your workspace…');
}

async function stopBackend() {
  await run(powershell, ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', path.join(backend, 'Stop.ps1')], {cwd: backend, windowsHide: true, timeout: 10000, env: powershellEnv});
}

async function main() {
  pendingFolder = folderArgument(process.argv, process.cwd());
  if (!app.requestSingleInstanceLock({folder: pendingFolder})) { app.quit(); return; }
  app.on('second-instance', (_event, args, cwd, data) => {
    pendingFolder = data && typeof data.folder === 'string' ? folderArgument(['--folder', data.folder], cwd) : folderArgument(args, cwd);
    if (mainWindow) { if (mainWindow.isMinimized()) mainWindow.restore(); mainWindow.show(); mainWindow.focus(); if (ready && pendingFolder) mainWindow.webContents.send('open-folder', pendingFolder); }
  });
  await app.whenReady();
  session.defaultSession.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  createStartupScreen();
  mainWindow = new BrowserWindow({width: 1440, height: 960, minWidth: 850, minHeight: 600, title: 'Janvi Image Studio',
    backgroundColor: '#1c1e20', icon: path.join(__dirname, 'janvi-app.ico'),
    show: false,
    webPreferences: {preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true}});
  mainWindow.setMenuBarVisibility(false);
  mainWindow.webContents.setWindowOpenHandler(() => ({action: 'deny'}));
  mainWindow.webContents.on('will-navigate', (event, target) => { try { if (new URL(target).origin !== origin) event.preventDefault(); } catch (_) { event.preventDefault(); } });
  mainWindow.on('close', async event => {
    if (closing) return;
    event.preventDefault();
    if (!ready) { await dialog.showMessageBox(mainWindow, {type: 'info', message: 'The app is starting. Please wait for setup to finish.', buttons: ['OK']}); return; }
    try {
      const status = await requestJson(origin + '/api/status');
      if (status.active) { await dialog.showMessageBox(mainWindow, {type: 'info', message: 'A job is running. Wait for it to finish or cancel it before closing.', buttons: ['OK']}); return; }
      await stopBackend(); closing = true; mainWindow.close();
    } catch (_) {
      const result = await dialog.showMessageBox(mainWindow, {type: 'warning', message: 'The processing service could not be reached. Closing this window will leave any service process unchanged.', buttons: ['Keep open', 'Close window'], defaultId: 0, cancelId: 0});
      if (result.response === 1) { closing = true; mainWindow.close(); }
    }
  });
  ipcMain.handle('select-folder', async (event, initial) => {
    if (!authorized(event) || typeof initial !== 'string') throw new Error('Invalid folder request.');
    if (pickerOpen) return {selected_path: ''};
    const options = {title: 'Select folder', properties: ['openDirectory', 'createDirectory']};
    if (initial && fs.existsSync(initial) && fs.statSync(initial).isDirectory()) options.defaultPath = initial;
    pickerOpen = true;
    try {
      const result = await dialog.showOpenDialog(mainWindow, options);
      return {selected_path: result.canceled ? '' : result.filePaths[0] || ''};
    } finally { pickerOpen = false; }
  });
  ipcMain.handle('validate-dropped-folder', async (event, selected) => {
    if (!authorized(event) || typeof selected !== 'string' || !selected) throw new Error('Choose a folder from File Explorer.');
    try { if (fs.statSync(selected).isDirectory()) return selected; } catch (_) {}
    throw new Error('Drop one existing folder.');
  });
  ipcMain.handle('initial-folder', event => { if (!authorized(event)) throw new Error('Invalid request'); const folder = pendingFolder; pendingFolder = ''; return folder; });
  ipcMain.handle('photoshop-repair', async (event, directory) => {
    if (!authorized(event) || typeof directory !== 'string') throw new Error('Invalid folder request.');
    if (repairProcess || Date.now() - repairLaunchTime < 60000) throw new Error('A Photoshop repair was just launched. Check Photoshop for its script confirmation before starting again.');
    const root = path.resolve(directory);
    const status = await requestJson(origin + '/api/photoshop/status?' + new URLSearchParams({dest_dir: root}));
    const script = status.script, queue = script ? path.dirname(script) : '';
    const relativeQueue = queue ? path.relative(root, queue) : '..';
    if (!queue || (relativeQueue && relativeQueue.startsWith('..')) || !fs.existsSync(path.join(queue, 'padding_manifest.json')) || !fs.statSync(script).isFile()) throw new Error('No generated Photoshop repair queue was found in this folder.');
    if (!status.valid_script || !status.total) throw new Error('The Photoshop script does not match the generated queue, or the queue is empty. Regenerate it by resizing.');
    if (fs.existsSync(path.join(queue, '.janvi-photoshop-running'))) throw new Error('This Photoshop queue is already running.');
    const launcher = path.join(backend, 'photoshop', 'Start_Photoshop_Repair.ps1');
    const child = spawn(powershell, ['-NoProfile', '-NonInteractive', '-File', launcher, '-QueueDirectory', queue], {windowsHide: true, env: powershellEnv});
    repairProcess = child;
    repairLaunchTime = Date.now();
    const previous = JSON.stringify(status.report || {});
    const timer = setTimeout(async () => {
      try {
        const current = await requestJson(origin + '/api/photoshop/status?' + new URLSearchParams({dest_dir: root}));
        if (JSON.stringify(current.report || {}) !== previous) return;
      } catch (_) {}
      if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send('photoshop-launch-error', 'Repair has not reported progress yet. In Photoshop, confirm that you want to run Repair_Padding.jsx. If another Photoshop version is open, save and close it first.');
    }, 60000);
    child.on('error', error => { clearTimeout(timer); repairProcess=null; repairLaunchTime=0; if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send('photoshop-launch-error', error.message); });
    let stderr=''; child.stderr.on('data', data => { stderr += data.toString(); });
    child.on('exit', code => { repairProcess=null; if (code) { clearTimeout(timer); repairLaunchTime=0; if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send('photoshop-launch-error', stderr || `Photoshop launch failed (${code}).`); } });
    return true;
  });
  try {
    await startBackend();
    ready = true;
    const pageReady = new Promise(resolve => mainWindow.webContents.once('did-finish-load', resolve));
    await mainWindow.loadURL(origin + '/');
    await pageReady;
    mainWindow.show();
    closeStartupScreen();
  }
  catch (error) {
    startupMessage('Janvi could not start. Showing details…');
    dialog.showErrorBox('Janvi Image Studio could not start', error.message);
    closeStartupScreen(); closing = true; mainWindow.close();
  }
}
app.on('window-all-closed', () => app.quit());
main().catch(error => { dialog.showErrorBox('Janvi Image Studio could not start', error.message); app.quit(); });

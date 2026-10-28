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
let mainWindow, origin = '', ready = false, closing = false;
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

async function startBackend() {
  const script = path.join(backend, 'Start.ps1');
  if (!fs.existsSync(script)) throw new Error('Bundled processing backend is missing.');
  const portFile = path.join(backend, 'data', 'desktop-port.json');
  let preferred = 0;
  try { const saved = JSON.parse(fs.readFileSync(portFile, 'utf8')).port; if (Number.isInteger(saved) && saved > 1024 && saved <= 65535) preferred = saved; } catch (_) {}
  let port;
  try { port = await availablePort(preferred); } catch (_) { port = await availablePort(0); }
  let output = '';
  await new Promise((resolve, reject) => {
    const child = spawn(powershell, ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script, '-Offline', '-NoBrowser', '-Port', String(port)], {cwd: backend, windowsHide: true, env: powershellEnv});
    child.stdout.on('data', data => { output = (output + data.toString()).slice(-5000); });
    child.stderr.on('data', data => { output = (output + data.toString()).slice(-5000); });
    child.on('error', reject);
    child.on('exit', code => code === 0 ? resolve() : reject(new Error(`Backend setup failed (${code}).\n${output}`)));
  });
  const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
  const url = new URL(state.url);
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || !url.port) throw new Error('Backend returned an invalid local address.');
  origin = url.origin;
  fs.writeFileSync(portFile, JSON.stringify({port: Number(url.port)}));
  const health = await requestJson(origin + '/api/health');
  if (health.app !== 'janvi-image-resize' || !health.ready) throw new Error('Backend is not ready.');
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
  mainWindow = new BrowserWindow({width: 1440, height: 960, minWidth: 850, minHeight: 600, title: 'Janvi Image Studio',
    backgroundColor: '#1c1e20', icon: path.join(__dirname, 'janvi-app.ico'),
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
    const root = path.resolve(directory), script = path.join(root, 'Repair_Padding.jsx');
    if (!fs.existsSync(path.join(root, 'padding_manifest.json')) || !fs.statSync(script).isFile()) throw new Error('No generated Photoshop repair queue was found in this folder.');
    const status = await requestJson(origin + '/api/photoshop/status?' + new URLSearchParams({dest_dir: root}));
    if (!status.valid_script || !status.total) throw new Error('The Photoshop script does not match the generated queue, or the queue is empty. Regenerate it by resizing.');
    if (fs.existsSync(path.join(root, '.janvi-photoshop-running'))) throw new Error('This Photoshop queue is already running.');
    const launcher = path.join(backend, 'photoshop', 'Start_Photoshop_Repair.ps1');
    const child = spawn(powershell, ['-NoProfile', '-NonInteractive', '-File', launcher, '-QueueDirectory', root], {windowsHide: true, env: powershellEnv});
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
  await mainWindow.loadURL('data:text/html,<body style="background:%231c1e20;color:white;font:16px Segoe UI;padding:40px">Starting Janvi Image Studio. First-time setup may take a few minutes.</body>');
  try { await startBackend(); ready = true; await mainWindow.loadURL(origin + '/'); }
  catch (error) { dialog.showErrorBox('Janvi Image Studio could not start', error.message); closing = true; mainWindow.close(); }
}
app.on('window-all-closed', () => app.quit());
main().catch(error => { dialog.showErrorBox('Janvi Image Studio could not start', error.message); app.quit(); });

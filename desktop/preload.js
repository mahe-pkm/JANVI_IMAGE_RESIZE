const {contextBridge, ipcRenderer, webUtils} = require('electron');

contextBridge.exposeInMainWorld('JanviDesktop', {
  selectFolder: initial => ipcRenderer.invoke('select-folder', initial),
  initialFolder: () => ipcRenderer.invoke('initial-folder'),
  onOpenFolder: callback => ipcRenderer.on('open-folder', (_event, folder) => callback(folder)),
  startPhotoshopRepair: folder => ipcRenderer.invoke('photoshop-repair', folder),
  onPhotoshopError: callback => ipcRenderer.on('photoshop-launch-error', (_event, error) => callback(error)),
  validateDroppedFolder: file => {
    const path = webUtils.getPathForFile(file);
    return ipcRenderer.invoke('validate-dropped-folder', path);
  }
});

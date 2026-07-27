// Application Controller for Logo Processor Dashboard

document.addEventListener('DOMContentLoaded', () => {
    // Nav Elements
    const navDash = document.getElementById('nav-dash');
    const navPipe = document.getElementById('nav-pipe');
    const navPad = document.getElementById('nav-pad');
    
    // Section Elements
    const secDash = document.getElementById('sec-dashboard');
    const secPipe = document.getElementById('sec-pipeline');
    const secPad = document.getElementById('sec-padded');
    
    // Status Elements
    const systemDot = document.getElementById('system-dot');
    const systemStatusText = document.getElementById('system-status-text');
    const padBadge = document.getElementById('pad-badge');
    
    // Dashboard Stats
    const statsFoldersCount = document.getElementById('stats-folders-count');
    const statsImagesCount = document.getElementById('stats-images-count');
    const statsPaddedCount = document.getElementById('stats-padded-count');
    const foldersTableBody = document.getElementById('folders-table-body');
    
    // Directory Settings Elements
    const rootDirInput = document.getElementById('root-dir-input');
    const rootValidationBadge = document.getElementById('root-validation-badge');
    const btnBrowseRoot = document.getElementById('btn-browse-root');
    const recentFoldersSelect = document.getElementById('recent-folders-select');
    const useDefaultOutput = document.getElementById('use-default-output');
    const destDirGroup = document.getElementById('dest-dir-group');
    const destDirInput = document.getElementById('dest-dir-input');
    const btnBrowseDest = document.getElementById('btn-browse-dest');
    
    // Shopify Export Configuration Elements
    const exportSrcInput = document.getElementById('export-src-input');
    const btnBrowseExportSrc = document.getElementById('btn-browse-export-src');
    const exportDestInput = document.getElementById('export-dest-input');
    const btnBrowseExportDest = document.getElementById('btn-browse-export-dest');
    
    // Folder Browser Modal Elements
    const browserModal = document.getElementById('browser-modal');
    const browserModalClose = document.getElementById('browser-modal-close');
    const browserCurrentPath = document.getElementById('browser-current-path');
    const btnBrowserUp = document.getElementById('btn-browser-up');
    const browserDirList = document.getElementById('browser-dir-list');
    const btnBrowserConfirm = document.getElementById('btn-browser-confirm');
    const btnBrowserCancel = document.getElementById('btn-browser-cancel');
    
    // Control Elements
    const folderSelect = document.getElementById('folder-select');
    const btnAudit = document.getElementById('btn-audit');
    const btnResize = document.getElementById('btn-resize');
    const btnExport = document.getElementById('btn-export');
    
    // Task Progress Card
    const activeTaskCard = document.getElementById('active-task-card');
    const taskTitle = document.getElementById('task-title');
    const taskFilename = document.getElementById('task-filename');
    const taskProgressBar = document.getElementById('task-progress-bar');
    const taskProgressText = document.getElementById('task-progress-text');
    const taskCountText = document.getElementById('task-count-text');
    const btnCancel = document.getElementById('btn-cancel');
    
    // Logs Terminal
    const logTerminal = document.getElementById('log-terminal');
    const btnClearLogs = document.getElementById('btn-clear-logs');
    
    // Padded Gallery Elements
    const galleryGrid = document.getElementById('padded-gallery');
    const galleryCount = document.getElementById('gallery-count');
    
    // Modal Elements
    const imageModal = document.getElementById('image-modal');
    const modalClose = document.getElementById('modal-close');
    const modalTitle = document.getElementById('modal-title');
    const modalImgOrig = document.getElementById('modal-img-orig');
    const modalImgResized = document.getElementById('modal-img-resized');
    
    // Theme Toggle State & Elements
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeToggleIcon = themeToggleBtn.querySelector('.theme-toggle-icon');
    
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
        themeToggleIcon.textContent = '☀️';
    } else {
        document.body.classList.remove('light-mode');
        themeToggleIcon.textContent = '🌙';
    }
    
    themeToggleBtn.addEventListener('click', () => {
        document.body.classList.toggle('light-mode');
        const isLight = document.body.classList.contains('light-mode');
        localStorage.setItem('theme', isLight ? 'light' : 'dark');
        themeToggleIcon.textContent = isLight ? '☀️' : '🌙';
        
        // Soft bounce animation
        themeToggleIcon.style.transform = 'scale(0.8) rotate(360deg)';
        setTimeout(() => {
            themeToggleIcon.style.transform = 'scale(1) rotate(0deg)';
        }, 200);
    });

    let currentStatus = 'idle';
    let loadedLogsCount = 0;
    
    // Directory Settings State
    let rootDir = localStorage.getItem('root_dir') || 'c:\\Users\\rough\\Desktop\\Logo Processing\\May-20261\\Resizing';
    let destDir = localStorage.getItem('dest_dir') || 'c:\\Users\\rough\\Desktop\\Logo Processing\\May-20261\\Re-sized';
    let isDefaultOutput = localStorage.getItem('use_default_output') !== 'false';
    let recentFolders = JSON.parse(localStorage.getItem('recent_folders') || '[]');
    
    // Shopify Export State
    let exportSrc = localStorage.getItem('export_src') || 'c:\\Users\\rough\\Desktop\\Logo Processing\\May-20261\\Re-sized\\With Logo';
    let exportDest = localStorage.getItem('export_dest') || 'c:\\Users\\rough\\Desktop\\Logo Processing\\May-20261\\Re-sized\\Final For Shopify';
    
    // Browser Modal State
    let activeBrowserTarget = 'root'; // 'root', 'dest', 'export_src', 'export_dest'
    let currentBrowsePath = '';

    // Initialize UI from State
    rootDirInput.value = rootDir;
    destDirInput.value = destDir;
    useDefaultOutput.checked = isDefaultOutput;
    exportSrcInput.value = exportSrc;
    exportDestInput.value = exportDest;
    
    if (isDefaultOutput) {
        destDirGroup.classList.add('hidden');
    } else {
        destDirGroup.classList.remove('hidden');
    }
    
    // Toggle Output Folder visibility
    useDefaultOutput.addEventListener('change', () => {
        isDefaultOutput = useDefaultOutput.checked;
        localStorage.setItem('use_default_output', isDefaultOutput);
        if (isDefaultOutput) {
            destDirGroup.classList.add('hidden');
        } else {
            destDirGroup.classList.remove('hidden');
        }
        validateAndReload();
        loadPatchList();
    });

    // ----------------------------------------------------
    // Section Switching Logic
    // ----------------------------------------------------
    const sections = [
        { nav: navDash, sec: secDash },
        { nav: navPipe, sec: secPipe },
        { nav: navPad, sec: secPad }
    ];

    function showSection(targetSec) {
        sections.forEach(item => {
            if (item.sec === targetSec) {
                item.sec.classList.add('active');
                item.nav.classList.add('active');
            } else {
                item.sec.classList.remove('active');
                item.nav.classList.remove('active');
            }
        });
    }

    navDash.addEventListener('click', (e) => { e.preventDefault(); showSection(secDash); });
    navPipe.addEventListener('click', (e) => { e.preventDefault(); showSection(secPipe); });
    navPad.addEventListener('click', (e) => { e.preventDefault(); showSection(secPad); });

    // Handle hash routing on load
    if (window.location.hash === '#pipeline') showSection(secPipe);
    else if (window.location.hash === '#padded') showSection(secPad);

    // ----------------------------------------------------
    // Directory Settings & Recents History
    // ----------------------------------------------------
    function addRecentFolder(path) {
        if (!path) return;
        const normalized = path.replace(/\//g, '\\');
        recentFolders = recentFolders.filter(f => f.toLowerCase() !== normalized.toLowerCase());
        recentFolders.unshift(normalized);
        if (recentFolders.length > 5) {
            recentFolders.pop();
        }
        localStorage.setItem('recent_folders', JSON.stringify(recentFolders));
        updateRecentFoldersDropdown();
    }
    
    function updateRecentFoldersDropdown() {
        recentFoldersSelect.innerHTML = '';
        if (recentFolders.length === 0) {
            recentFoldersSelect.innerHTML = '<option value="">-- No Recent History --</option>';
            return;
        }
        
        recentFoldersSelect.innerHTML = '<option value="">-- Select Recent Folder --</option>';
        recentFolders.forEach(folder => {
            const opt = document.createElement('option');
            opt.value = folder;
            opt.textContent = folder;
            recentFoldersSelect.appendChild(opt);
        });
    }
    
    recentFoldersSelect.addEventListener('change', () => {
        const val = recentFoldersSelect.value;
        if (val) {
            rootDirInput.value = val;
            validateAndReload();
        }
    });

    // ----------------------------------------------------
    // Path Validation & Folder Listing
    // ----------------------------------------------------
    let validationTimeout = null;
    
    async function validateAndReload() {
        const val = rootDirInput.value.trim();
        rootDir = val;
        localStorage.setItem('root_dir', rootDir);
        
        rootValidationBadge.className = 'status-badge status-checking';
        rootValidationBadge.textContent = 'Checking...';
        
        try {
            const queryParam = encodeURIComponent(val);
            const res = await fetch(`/api/folders?root_dir=${queryParam}`);
            const data = await res.json();
            
            if (data.valid) {
                rootValidationBadge.className = 'status-badge status-valid';
                rootValidationBadge.textContent = 'Valid';
                
                // Add folder to recent folders list
                addRecentFolder(data.resolved_path);
                
                // Populate collections dropdown & table
                populateCollections(data.folders);
            } else {
                rootValidationBadge.className = 'status-badge status-invalid';
                rootValidationBadge.textContent = 'Invalid';
                clearFoldersTable(data.error);
            }
        } catch (err) {
            rootValidationBadge.className = 'status-badge status-invalid';
            rootValidationBadge.textContent = 'Error';
            clearFoldersTable(err.message);
        }
    }
    
    rootDirInput.addEventListener('input', () => {
        clearTimeout(validationTimeout);
        validationTimeout = setTimeout(validateAndReload, 800);
    });
    
    rootDirInput.addEventListener('change', validateAndReload);
    destDirInput.addEventListener('change', () => {
        destDir = destDirInput.value.trim();
        localStorage.setItem('dest_dir', destDir);
        loadPatchList();
    });
    exportSrcInput.addEventListener('change', () => {
        exportSrc = exportSrcInput.value.trim();
        localStorage.setItem('export_src', exportSrc);
    });
    exportDestInput.addEventListener('change', () => {
        exportDest = exportDestInput.value.trim();
        localStorage.setItem('export_dest', exportDest);
    });

    function populateCollections(folders) {
        const previousSelectVal = folderSelect.value;
        folderSelect.innerHTML = '<option value="">-- All Collections --</option>';
        
        let totalImages = 0;
        foldersTableBody.innerHTML = '';
        
        folders.forEach(folder => {
            totalImages += folder.image_count;
            
            const opt = document.createElement('option');
            opt.value = folder.name;
            opt.textContent = `${folder.name} (${folder.image_count} images)`;
            folderSelect.appendChild(opt);
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${folder.name}</strong></td>
                <td>${folder.image_count} images</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="triggerDirectAction('${folder.name}', 'audit')">Audit</button>
                    <button class="btn btn-primary btn-sm" onclick="triggerDirectAction('${folder.name}', 'resize')">Resize</button>
                </td>
            `;
            foldersTableBody.appendChild(tr);
        });
        
        if (previousSelectVal && folders.some(f => f.name === previousSelectVal)) {
            folderSelect.value = previousSelectVal;
        }
        
        statsFoldersCount.textContent = folders.length;
        statsImagesCount.textContent = totalImages;
    }
    
    function clearFoldersTable(errorMessage) {
        folderSelect.innerHTML = '<option value="">-- No Collections --</option>';
        foldersTableBody.innerHTML = `
            <tr>
                <td colspan="3" style="text-align: center; color: var(--danger); padding: 2rem;">
                    ⚠️ ${errorMessage || 'Invalid directory location'}
                </td>
            </tr>
        `;
        statsFoldersCount.textContent = '0';
        statsImagesCount.textContent = '0';
    }

    async function loadFolders() {
        await validateAndReload();
    }

    async function loadPatchList() {
        try {
            const rootParam = encodeURIComponent(rootDirInput.value.trim());
            const destParam = encodeURIComponent(isDefaultOutput ? '' : destDirInput.value.trim());
            
            const res = await fetch(`/api/patch-list?root_dir=${rootParam}&dest_dir=${destParam}`);
            const data = await res.json();
            
            if (data.error) throw new Error(data.error);
            
            padBadge.textContent = data.items.length;
            statsPaddedCount.textContent = data.items.length;
            galleryCount.textContent = `Total: ${data.items.length} images requiring manual patching`;
            
            galleryGrid.innerHTML = '';
            
            if (data.items.length === 0) {
                galleryGrid.innerHTML = '<div class="card" style="grid-column: 1/-1; text-align: center; color: var(--text-muted);">No padded images recorded yet. All processed images fit the crop window!</div>';
                return;
            }
            
            data.items.forEach(item => {
                const parts = item.relative_path.split('\\');
                const filename = parts[parts.length - 1];
                const folderName = parts.length > 2 ? parts[parts.length - 2] : '';
                
                const card = document.createElement('div');
                card.className = 'gallery-item';
                card.innerHTML = `
                    <div class="gallery-preview">
                        <img src="${item.resized_url}" alt="${filename}">
                        <span class="gallery-tag">Padded Preview</span>
                    </div>
                    <div class="gallery-info">
                        <h4>${filename}</h4>
                        <p>${folderName}</p>
                    </div>
                `;
                
                card.querySelector('.gallery-preview').addEventListener('click', () => {
                    openComparisonModal(filename, item.src_url, item.resized_url);
                });
                
                galleryGrid.appendChild(card);
            });
            
        } catch (err) {
            console.error("Error loading patch list:", err);
            appendLog(`[System Error] Failed to load padded patch list: ${err.message}`, 'error');
        }
    }

    // ----------------------------------------------------
    // Directory Browser Logic
    // ----------------------------------------------------
    async function handleBrowseNative(target) {
        let currentVal = '';
        if (target === 'root') currentVal = rootDirInput.value.trim();
        else if (target === 'dest') currentVal = destDirInput.value.trim();
        else if (target === 'export_src') currentVal = exportSrcInput.value.trim();
        else if (target === 'export_dest') currentVal = exportDestInput.value.trim();
        
        try {
            const queryParam = encodeURIComponent(currentVal);
            const res = await fetch(`/api/select-folder?initial_dir=${queryParam}`);
            const data = await res.json();
            
            if (data.error) throw new Error(data.error);
            
            if (data.selected_path) {
                if (target === 'root') {
                    rootDirInput.value = data.selected_path;
                    validateAndReload();
                } else if (target === 'dest') {
                    destDirInput.value = data.selected_path;
                    destDir = data.selected_path;
                    localStorage.setItem('dest_dir', destDir);
                    loadPatchList();
                } else if (target === 'export_src') {
                    exportSrcInput.value = data.selected_path;
                    exportSrc = data.selected_path;
                    localStorage.setItem('export_src', exportSrc);
                } else if (target === 'export_dest') {
                    exportDestInput.value = data.selected_path;
                    exportDest = data.selected_path;
                    localStorage.setItem('export_dest', exportDest);
                }
            }
        } catch (err) {
            console.error("Native browse error:", err);
            // Fallback to custom browser modal if native dialog fails
            openDirectoryBrowser(target);
        }
    }

    async function openDirectoryBrowser(target) {
        activeBrowserTarget = target;
        let currentVal = '';
        if (target === 'root') currentVal = rootDirInput.value.trim();
        else if (target === 'dest') currentVal = destDirInput.value.trim();
        else if (target === 'export_src') currentVal = exportSrcInput.value.trim();
        else if (target === 'export_dest') currentVal = exportDestInput.value.trim();
        
        browserModal.classList.add('active');
        await browseToPath(currentVal);
    }
    
    async function browseToPath(path) {
        currentBrowsePath = path;
        browserCurrentPath.textContent = path || 'Loading...';
        browserDirList.innerHTML = '<li style="color: var(--text-muted); padding-left: 1.25rem;">Loading directories...</li>';
        
        try {
            const queryParam = encodeURIComponent(path);
            const res = await fetch(`/api/browse?path=${queryParam}`);
            
            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.error || 'Path error');
            }
            
            const data = await res.json();
            
            currentBrowsePath = data.current_path;
            browserCurrentPath.textContent = data.current_path;
            
            if (data.parent_path) {
                btnBrowserUp.disabled = false;
                btnBrowserUp.dataset.parent = data.parent_path;
            } else {
                btnBrowserUp.disabled = true;
                btnBrowserUp.removeAttribute('data-parent');
            }
            
            browserDirList.innerHTML = '';
            
            if (data.dirs.length === 0) {
                browserDirList.innerHTML = '<li style="color: var(--text-muted); font-style: italic; padding: 0.65rem 1.25rem;">No subdirectories found.</li>';
                return;
            }
            
            data.dirs.forEach(dirName => {
                const li = document.createElement('li');
                li.innerHTML = `<span class="folder-icon">📁</span> ${dirName}`;
                li.addEventListener('click', () => {
                    const separator = currentBrowsePath.includes('/') ? '/' : '\\';
                    const endsWithSep = currentBrowsePath.endsWith('/') || currentBrowsePath.endsWith('\\');
                    const nextPath = endsWithSep ? `${currentBrowsePath}${dirName}` : `${currentBrowsePath}${separator}${dirName}`;
                    browseToPath(nextPath);
                });
                browserDirList.appendChild(li);
            });
        } catch (err) {
            console.error("Browse error:", err);
            browserDirList.innerHTML = `<li style="color: var(--danger); padding: 0.65rem 1.25rem;">⚠️ Error: ${err.message}</li>`;
            btnBrowserUp.disabled = false;
            btnBrowserUp.dataset.parent = '';
        }
    }
    
    btnBrowseRoot.addEventListener('click', () => handleBrowseNative('root'));
    btnBrowseDest.addEventListener('click', () => handleBrowseNative('dest'));
    btnBrowseExportSrc.addEventListener('click', () => handleBrowseNative('export_src'));
    btnBrowseExportDest.addEventListener('click', () => handleBrowseNative('export_dest'));
    
    btnBrowserUp.addEventListener('click', () => {
        const parentPath = btnBrowserUp.dataset.parent;
        browseToPath(parentPath || '');
    });
    
    btnBrowserConfirm.addEventListener('click', () => {
        if (activeBrowserTarget === 'root') {
            rootDirInput.value = currentBrowsePath;
            validateAndReload();
        } else if (activeBrowserTarget === 'dest') {
            destDirInput.value = currentBrowsePath;
            destDir = currentBrowsePath;
            localStorage.setItem('dest_dir', destDir);
            loadPatchList();
        } else if (activeBrowserTarget === 'export_src') {
            exportSrcInput.value = currentBrowsePath;
            exportSrc = currentBrowsePath;
            localStorage.setItem('export_src', exportSrc);
        } else if (activeBrowserTarget === 'export_dest') {
            exportDestInput.value = currentBrowsePath;
            exportDest = currentBrowsePath;
            localStorage.setItem('export_dest', exportDest);
        }
        closeBrowserModal();
    });
    
    function closeBrowserModal() {
        browserModal.classList.remove('active');
    }
    
    browserModalClose.addEventListener('click', closeBrowserModal);
    btnBrowserCancel.addEventListener('click', closeBrowserModal);
    browserModal.addEventListener('click', (e) => {
        if (e.target === browserModal) closeBrowserModal();
    });

    // ----------------------------------------------------
    // Operations & Task Submission
    // ----------------------------------------------------
    async function startTask(endpoint, payload = {}) {
        try {
            // Append folder paths dynamically to payload
            payload.root_dir = rootDirInput.value.trim();
            payload.dest_dir = isDefaultOutput ? '' : destDirInput.value.trim();
            
            const res = await fetch(`/api/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            
            appendLog(`[System] ${data.message}`);
            showSection(secPipe);
        } catch (err) {
            alert(`Failed to start task: ${err.message}`);
            appendLog(`[System Error] Failed to start operation: ${err.message}`, 'error');
        }
    }

    btnAudit.addEventListener('click', () => {
        const folder = folderSelect.value;
        startTask('analyze', { folder });
    });

    btnResize.addEventListener('click', () => {
        const folder = folderSelect.value;
        startTask('resize', { folder });
    });

    btnExport.addEventListener('click', () => {
        if (confirm("This will copy and rename the files from 'Untitled Export' to the Shopify output folder. Continue?")) {
            const export_src = exportSrcInput.value.trim();
            const export_dest = exportDestInput.value.trim();
            startTask('export', { export_src, export_dest });
        }
    });

    btnCancel.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/cancel', { method: 'POST' });
            const data = await res.json();
            appendLog(`[System] ${data.message}`);
        } catch (err) {
            console.error(err);
        }
    });

    window.triggerDirectAction = function(folder, action) {
        folderSelect.value = folder;
        if (action === 'audit') {
            startTask('analyze', { folder });
        } else if (action === 'resize') {
            startTask('resize', { folder });
        }
    };

    // ----------------------------------------------------
    // Terminal Log Utilities
    // ----------------------------------------------------
    function appendLog(message, type = '') {
        const div = document.createElement('div');
        div.className = `log-line ${type}`;
        div.textContent = message;
        logTerminal.appendChild(div);
        logTerminal.scrollTop = logTerminal.scrollHeight;
    }

    btnClearLogs.addEventListener('click', () => {
        logTerminal.innerHTML = '<div class="log-line system">[System] Terminal view cleared. Logs still record in backend.</div>';
    });

    // ----------------------------------------------------
    // Modal Comparison Setup
    // ----------------------------------------------------
    function openComparisonModal(title, origUrl, resizedUrl) {
        modalTitle.textContent = `Comparison: ${title}`;
        modalImgOrig.src = origUrl;
        modalImgResized.src = resizedUrl;
        imageModal.classList.add('active');
    }

    function closeModal() {
        imageModal.classList.remove('active');
        modalImgOrig.src = '';
        modalImgResized.src = '';
    }

    modalClose.addEventListener('click', closeModal);
    imageModal.addEventListener('click', (e) => {
        if (e.target === imageModal) closeModal();
    });

    // ----------------------------------------------------
    // Task Status Polling Loop
    // ----------------------------------------------------
    async function pollStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            
            // Check status change transitions to reload data
            if (currentStatus === 'running' && data.status !== 'running') {
                // Task has ended
                validateAndReload();
                loadPatchList();
            }
            currentStatus = data.status;

            if (data.status === 'running') {
                systemDot.className = 'dot running';
                let taskLabel = data.task_type.toUpperCase();
                systemStatusText.textContent = `Running ${taskLabel}...`;
                activeTaskCard.classList.remove('hidden');
                
                taskTitle.textContent = `Running ${data.task_type === 'audit' ? 'Padding Audit' : data.task_type === 'resize' ? 'Subject-Aware Resizing' : 'Shopify Exporter'}...`;
                taskFilename.textContent = data.current_file ? `File: ${data.current_file}` : 'Starting task...';
                
                taskProgressBar.style.width = `${data.progress}%`;
                taskProgressText.textContent = `${data.progress}% Completed`;
                taskCountText.textContent = `${data.current} / ${data.total} processed`;
                
                btnCancel.disabled = false;
            } else {
                systemDot.className = 'dot idle';
                systemStatusText.textContent = 'System Idle';
                activeTaskCard.classList.add('hidden');
            }

            // Sync logs
            if (data.logs.length > 0) {
                if (data.logs.length < loadedLogsCount) {
                    loadedLogsCount = 0;
                }
                
                for (let i = loadedLogsCount; i < data.logs.length; i++) {
                    const line = data.logs[i];
                    let logType = '';
                    if (line.includes('ERROR') || line.includes('Failed')) logType = 'error';
                    else if (line.includes('Complete') || line.includes('Success')) logType = 'system';
                    
                    appendLog(line, logType);
                }
                loadedLogsCount = data.logs.length;
            } else {
                loadedLogsCount = 0;
            }

        } catch (err) {
            console.error("Status polling error:", err);
        }
    }

    // Fetch last active directories from backend to sync
    async function syncActiveDirectories() {
        try {
            const res = await fetch('/api/active-directory');
            const data = await res.json();
            if (data.root_dir) {
                rootDir = data.root_dir;
                localStorage.setItem('root_dir', rootDir);
                rootDirInput.value = rootDir;
            }
            if (data.dest_dir) {
                destDir = data.dest_dir;
                localStorage.setItem('dest_dir', destDir);
                destDirInput.value = destDir;
                
                // Determine if this destination matches the default destination pattern
                let rootLower = rootDir.toLowerCase();
                let isDefault = false;
                if (rootDir) {
                    if (rootLower.endsWith('\\resizing') || rootLower.endsWith('/resizing')) {
                        const expectedDefault = rootDir.substring(0, rootDir.length - 8) + 'Re-sized';
                        isDefault = (destDir.toLowerCase() === expectedDefault.toLowerCase());
                    } else {
                        const expectedDefault = rootDir + '_resized';
                        isDefault = (destDir.toLowerCase() === expectedDefault.toLowerCase());
                    }
                }
                isDefaultOutput = isDefault;
                localStorage.setItem('use_default_output', isDefault);
                useDefaultOutput.checked = isDefault;
                if (isDefault) {
                    destDirGroup.classList.add('hidden');
                } else {
                    destDirGroup.classList.remove('hidden');
                }
            }
            await validateAndReload();
            await loadPatchList();
        } catch (err) {
            console.error("Failed to sync active directories:", err);
            await validateAndReload();
            await loadPatchList();
        }
    }

    // Init & Loop
    updateRecentFoldersDropdown();
    syncActiveDirectories();
    setInterval(pollStatus, 1000);
});

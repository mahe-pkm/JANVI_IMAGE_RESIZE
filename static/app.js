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
    let loadedLogCursor = 0;
    
    // Directory Settings State
    let rootDir = localStorage.getItem('root_dir') || '';
    let destDir = localStorage.getItem('dest_dir') || '';
    let isDefaultOutput = localStorage.getItem('use_default_output') !== 'false';
    let recentFolders = JSON.parse(localStorage.getItem('recent_folders') || '[]');
    
    // Shopify Export State
    let exportSrc = localStorage.getItem('export_src') || '';
    let exportDest = localStorage.getItem('export_dest') || '';
    
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
        { nav: document.getElementById('nav-logo'), sec: document.getElementById('sec-logo') },
        { nav: navPad, sec: secPad }
    ];

    function showSection(targetSec) {
        document.body.classList.toggle('logo-mode', targetSec.id === 'sec-logo');
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
    document.getElementById('nav-logo').addEventListener('click', (e) => { e.preventDefault(); showSection(document.getElementById('sec-logo')); });
    navPad.addEventListener('click', (e) => { e.preventDefault(); showSection(secPad); });

    // Handle hash routing on load
    if (window.location.hash === '#logo') showSection(document.getElementById('sec-logo'));
    else if (window.location.hash === '#pipeline') showSection(secPipe);
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
        document.dispatchEvent(new Event('janvi-root-changed'));
        
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
            const nameCell = document.createElement('td');
            nameCell.textContent = folder.name;
            const countCell = document.createElement('td');
            countCell.textContent = `${folder.image_count} images`;
            const actionCell = document.createElement('td');
            for (const [label, action] of [['Audit', 'audit'], ['Resize', 'resize']]) {
                const button = document.createElement('button');
                button.className = 'btn btn-secondary btn-sm';
                button.textContent = label;
                button.addEventListener('click', () => window.triggerDirectAction(folder.name, action));
                actionCell.appendChild(button);
            }
            tr.append(nameCell, countCell, actionCell);
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

    let comparisonItems = [], comparisonIndex = 0;
    function renderReview() {
        const item = comparisonItems[comparisonIndex], image = document.getElementById('review-image');
        image.hidden = !item;
        document.getElementById('review-empty').hidden = !!item;
        document.getElementById('review-position').textContent = item ? `${comparisonIndex + 1} / ${comparisonItems.length}` : '0 / 0';
        ['review-prev','review-next','review-full'].forEach(id => { document.getElementById(id).disabled = !item; });
        document.getElementById('review-filename').textContent = item ? item.relative_path : 'Select a processed folder to begin';
        if (item) { image.src = document.getElementById('review-before').checked ? item.src_url : item.resized_url; image.alt = item.relative_path; }
        const zoom = document.getElementById('review-zoom').value;
        image.style.maxHeight = zoom === 'fit' ? '100%' : 'none';
        image.style.maxWidth = zoom === 'fit' ? '100%' : 'none';
        image.style.width = zoom === 'fit' ? '' : `${image.naturalWidth * Number(zoom) / 100}px`;
        document.querySelectorAll('#padded-gallery .gallery-item').forEach((card,index) => { card.classList.toggle('selected',index === comparisonIndex); card.setAttribute('aria-pressed',String(index === comparisonIndex)); });
    }
    function navigateReview(delta) { if (!comparisonItems.length) return; comparisonIndex = (comparisonIndex + delta + comparisonItems.length) % comparisonItems.length; renderReview(); }
    document.getElementById('review-prev').addEventListener('click',()=>navigateReview(-1));
    document.getElementById('review-next').addEventListener('click',()=>navigateReview(1));
    document.getElementById('review-before').addEventListener('change',renderReview);
    document.getElementById('review-zoom').addEventListener('change',renderReview);
    document.getElementById('review-full').addEventListener('click',()=>{const item=comparisonItems[comparisonIndex];if(item)openComparisonModal(item.relative_path,item.src_url,item.resized_url);});
    async function loadPatchList() {
        try {
            const rootParam = encodeURIComponent(rootDirInput.value.trim());
            const destParam = encodeURIComponent(isDefaultOutput ? '' : destDirInput.value.trim());
            
            const res = await fetch(`/api/patch-list?root_dir=${rootParam}&dest_dir=${destParam}&all=${document.getElementById('gallery-all').checked ? '1' : '0'}`);
            const data = await res.json();
            
            if (data.error) throw new Error(data.error);
            
            comparisonItems = data.items;
            comparisonIndex = Math.min(comparisonIndex, Math.max(0, data.items.length - 1));
            padBadge.textContent = data.padded_count;
            statsPaddedCount.textContent = data.padded_count;
            galleryCount.textContent = `${data.items.length} images shown · ${data.padded_count} padded`;
            
            galleryGrid.innerHTML = '';
            
            if (data.items.length === 0) {
                galleryGrid.innerHTML = '<p class="monitor-note">No matching processed images. Try All images or check your output folder.</p>';
                renderReview();
                return;
            }
            
            data.items.forEach((item, index) => {
                const parts = item.relative_path.split(/[\\/]/);
                const filename = parts[parts.length - 1];
                const folderName = parts.length > 2 ? parts[parts.length - 2] : '';
                
                const card = document.createElement('button');
                card.type = 'button';
                card.title = filename;
                card.className = 'gallery-item';
                card.innerHTML = '<div class="gallery-preview"><img><span class="gallery-tag"></span></div><div class="gallery-info"><h4></h4><p></p></div>';
                card.querySelector('img').src = item.resized_url;
                card.querySelector('img').alt = filename;
                card.querySelector('.gallery-tag').textContent = item.padded ? 'Padded' : 'Resized';
                card.querySelector('h4').textContent = filename;
                card.querySelector('p').textContent = folderName;
                
                card.addEventListener('click', () => {
                    comparisonIndex = index;
                    renderReview();
                });
                
                galleryGrid.appendChild(card);
            });
            renderReview();
            
        } catch (err) {
            console.error("Error loading patch list:", err);
            appendLog(`[System Error] Failed to load padded patch list: ${err.message}`, 'error');
        }
    }
    document.getElementById('gallery-all').addEventListener('change', loadPatchList);
    document.addEventListener('keydown', event => {
        if (!secPad.classList.contains('active') || imageModal.classList.contains('active') || /INPUT|SELECT|TEXTAREA/.test(event.target.tagName)) return;
        if (event.key === 'ArrowLeft') { event.preventDefault(); navigateReview(-1); }
        if (event.key === 'ArrowRight') { event.preventDefault(); navigateReview(1); }
    });

    // ----------------------------------------------------
    // Directory Browser Logic
    // ----------------------------------------------------
    async function handleBrowseNative(target) {
        let currentVal = '';
        if (target === 'logo_source') currentVal = document.getElementById('logo-source').value.trim();
        else if (target === 'logo_destination') currentVal = document.getElementById('logo-destination').value.trim();
        else if (target === 'root') currentVal = rootDirInput.value.trim();
        else if (target === 'dest') currentVal = destDirInput.value.trim();
        else if (target === 'export_src') currentVal = exportSrcInput.value.trim();
        else if (target === 'export_dest') currentVal = exportDestInput.value.trim();
        
        try {
            let data;
            if (window.JanviDesktop) {
                data = await window.JanviDesktop.selectFolder(currentVal);
            } else {
                const res = await fetch('/api/select-folder', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({initial_dir: currentVal})});
                data = await res.json();
            }
            
            if (data.error) throw new Error(data.error);
            
            if (data.selected_path) {
                if (target === 'logo_source' || target === 'logo_destination') {
                    const input = document.getElementById(target === 'logo_source' ? 'logo-source' : 'logo-destination');
                    input.value = data.selected_path;
                    input.dispatchEvent(new Event('change', {bubbles: true}));
                } else if (target === 'root') {
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
                    exportSrcInput.dispatchEvent(new Event('change', {bubbles: true}));
                } else if (target === 'export_dest') {
                    exportDestInput.value = data.selected_path;
                    exportDest = data.selected_path;
                    localStorage.setItem('export_dest', exportDest);
                    exportDestInput.dispatchEvent(new Event('change', {bubbles: true}));
                }
            }
        } catch (err) {
            console.error("Native browse error:", err);
            alert(err.message || 'Could not open the system folder picker. Enter the folder path manually.');
        }
    }

    async function openDirectoryBrowser(target) {
        activeBrowserTarget = target;
        let currentVal = '';
        if (target === 'logo_source') currentVal = document.getElementById('logo-source').value.trim();
        else if (target === 'logo_destination') currentVal = document.getElementById('logo-destination').value.trim();
        else if (target === 'root') currentVal = rootDirInput.value.trim();
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
    window.JanviBrowse = handleBrowseNative;
    if (window.JanviDesktop) {
        ['root-dir-input', 'dest-dir-input', 'export-src-input', 'export-dest-input', 'logo-source', 'logo-destination'].forEach(id => {
            const field = document.getElementById(id), zone = field?.closest('.input-with-button');
            if (!zone) return;
            zone.classList.add('folder-drop-zone');
            zone.title = 'Drop a folder here or use Browse';
            const hint = document.createElement('small');
            hint.className = 'folder-drop-hint'; hint.textContent = 'Or drag a folder here from File Explorer.';
            zone.insertAdjacentElement('afterend', hint);
            zone.addEventListener('dragover', event => { event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; zone.classList.add('drag-active'); });
            zone.addEventListener('dragleave', () => zone.classList.remove('drag-active'));
            zone.addEventListener('drop', async event => {
                event.preventDefault(); zone.classList.remove('drag-active');
                if (field.disabled) return;
                if (event.dataTransfer.files.length !== 1) { alert('Drop one folder.'); return; }
                try {
                    field.value = await window.JanviDesktop.validateDroppedFolder(event.dataTransfer.files[0]);
                    field.dispatchEvent(new Event('input', {bubbles: true}));
                    field.dispatchEvent(new Event('change', {bubbles: true}));
                } catch (error) { alert(error.message || 'Drop one existing folder.'); }
            });
        });
    }
    
    btnBrowserUp.addEventListener('click', () => {
        const parentPath = btnBrowserUp.dataset.parent;
        browseToPath(parentPath || '');
    });
    
    btnBrowserConfirm.addEventListener('click', () => {
        if (activeBrowserTarget === 'logo_source' || activeBrowserTarget === 'logo_destination') {
            const input = document.getElementById(activeBrowserTarget === 'logo_source' ? 'logo-source' : 'logo-destination');
            input.value = currentBrowsePath;
            input.dispatchEvent(new Event('change', {bubbles: true}));
        } else if (activeBrowserTarget === 'root') {
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
            payload.device_id = window.JanviMonitor.selectedDevice();
            if (endpoint === 'resize' || endpoint === 'analyze') {
                payload.target_width = Number(document.getElementById('target-width').value);
                payload.target_height = Number(document.getElementById('target-height').value);
            }
            
            const res = await fetch(`/api/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            
            appendLog(`[System] ${data.message}`);
            showSection(secPipe);
            await pollStatus();
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

    const exportMode = document.getElementById('export-mode');
    const exportSummary = document.getElementById('export-preview-summary');
    const exportDetails = document.getElementById('export-preview-details');
    const exportList = document.getElementById('export-preview-list');
    let reviewedExport = '', exportSignature = '', previewSerial = 0;
    const exportPayload = () => ({export_src: exportSrcInput.value.trim(), export_dest: exportDestInput.value.trim(), mode: exportMode.value});
    function invalidateExportPreview() {
        previewSerial++; reviewedExport = ''; exportSignature = ''; exportDetails.hidden = true;
        exportSummary.textContent = 'Choose folders and preview before exporting.';
    }
    [exportSrcInput, exportDestInput].forEach(field => {
        field.addEventListener('input', invalidateExportPreview);
        field.addEventListener('change', invalidateExportPreview);
    });
    exportMode.addEventListener('change', () => {
        invalidateExportPreview();
        document.getElementById('export-mode-help').textContent = exportMode.value === 'lightroom'
            ? 'Only images directly inside Untitled Export folders are included; they go into their parent product folder.'
            : 'All supported images in the selected logo output are included. Untitled Export images go into their parent folder.';
    });
    document.getElementById('export-preview-button').addEventListener('click', async () => {
        const payload = exportPayload(), snapshot = JSON.stringify(payload), serial = ++previewSerial;
        reviewedExport = ''; exportDetails.hidden = true; exportSummary.textContent = 'Scanning images…';
        try {
            const response = await fetch('/api/export/preview', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: snapshot});
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Could not preview export.');
            if (serial !== previewSerial || snapshot !== JSON.stringify(exportPayload())) return;
            exportSummary.textContent = `${data.total} images · ${data.copy} to copy · ${data.already_present} already present · ${data.conflicts} conflicts`;
            exportList.replaceChildren();
            data.entries.forEach(entry => {
                const row = document.createElement('div');
                row.textContent = `${entry.source} → ${entry.output} (${entry.status.replaceAll('_', ' ')})`;
                exportList.append(row);
            });
            if (data.total > data.entries.length) {
                const note = document.createElement('div'); note.textContent = `Showing first ${data.entries.length} of ${data.total} images.`; exportList.append(note);
            }
            exportDetails.hidden = !data.total;
            if (data.total) { reviewedExport = snapshot; exportSignature = data.signature; }
            else exportSummary.textContent += ' · No eligible images found.';
        } catch (error) {
            if (serial === previewSerial) exportSummary.textContent = error.message;
        }
    });
    btnExport.addEventListener('click', () => {
        const payload = exportPayload();
        if (!reviewedExport || reviewedExport !== JSON.stringify(payload)) {
            exportSummary.textContent = 'Preview the selected folders before exporting.';
            return;
        }
        reviewedExport = '';
        startTask('export', {...payload, signature: exportSignature});
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
        document.getElementById('modal-count').textContent = `${comparisonIndex + 1} / ${comparisonItems.length}`;
    }

    function moveComparison(delta) {
        if (!comparisonItems.length) return;
        comparisonIndex = (comparisonIndex + delta + comparisonItems.length) % comparisonItems.length;
        const item = comparisonItems[comparisonIndex];
        openComparisonModal(item.relative_path.split(/[\\/]/).pop(), item.src_url, item.resized_url);
    }
    document.getElementById('modal-prev').addEventListener('click', () => moveComparison(-1));
    document.getElementById('modal-next').addEventListener('click', () => moveComparison(1));
    document.addEventListener('keydown', event => { if (!imageModal.classList.contains('active')) return; if (event.key === 'ArrowLeft') moveComparison(-1); if (event.key === 'ArrowRight') moveComparison(1); if (event.key === 'Escape') closeModal(); });

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
    let statusPolling = false;
    async function pollStatus() {
        if (statusPolling) return;
        statusPolling = true;
        try {
            const res = await fetch(`/api/status?after=${loadedLogCursor}`, {cache: 'no-store'});
            if (!res.ok) throw new Error('Status unavailable');
            const data = await res.json();
            if (['running', 'cancelling'].includes(currentStatus) && !data.active) {
                validateAndReload();
                loadPatchList();
            }
            currentStatus = data.status;
            window.JanviMonitor.renderJob(data);
            document.dispatchEvent(new CustomEvent('janvi-job-status', {detail: data}));
            systemDot.className = data.active ? 'dot running' : 'dot idle';
            systemStatusText.textContent = data.active ? data.phase : data.status.replaceAll('_', ' ');
            for (const event of data.events || []) {
                appendLog(event.message, event.message.includes('ERROR') ? 'error' : '');
            }
            loadedLogCursor = data.log_cursor;
        } catch (err) {
            systemStatusText.textContent = 'Connection interrupted · reconnecting';
        } finally {
            statusPolling = false;
        }
    }

    // Fetch last active directories from backend to sync
    async function syncActiveDirectories() {
        try {
            const res = await fetch('/api/active-directory');
            const data = await res.json();
            // A connected workflow owns its paths; older server job directories
            // must not replace the user's saved setup on a refresh.
            let workflow;
            try { workflow = JSON.parse(localStorage.getItem('janvi_workflow') || '{}'); } catch (_) { workflow = {}; }
            if (workflow.linked && workflow.source) {
                data.root_dir = workflow.source;
            }
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
            exportSrcInput.value = exportSrc || data.export_src || '';
            exportDestInput.value = exportDest || data.export_dest || '';
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
    syncActiveDirectories().finally(() => document.dispatchEvent(new Event('janvi-directories-ready')));
    pollStatus();
    setInterval(pollStatus, 1000);
});

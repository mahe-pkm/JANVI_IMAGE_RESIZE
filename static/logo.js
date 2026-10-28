document.addEventListener('DOMContentLoaded', () => {
    const $ = id => document.getElementById(id);
    const source = $('logo-source'), destination = $('logo-destination'), asset = $('logo-asset');
    const image = $('logo-image'), before = $('logo-before'), after = $('logo-after');
    const message = $('logo-message'), apply = $('logo-apply'), useExport = $('logo-use-export');
    const controls = ['logo-position', 'logo-width', 'logo-opacity', 'logo-offset-x', 'logo-offset-y', 'logo-rotation'];
    let presets = [], previewOK = false, busy = false, completedOutput = '', availableOutput = '', autoDestination = '', previewURL = null;
    let previewSequence = 0, previewTimer = null, imageSequence = 0, outputSequence = 0;
    let shownJob = null;

    const settings = () => ({position: $('logo-position').value, width_pct: $('logo-width').value,
        opacity_pct: $('logo-opacity').value, offset_x_pct: $('logo-offset-x').value, offset_y_pct: $('logo-offset-y').value,
        rotation: $('logo-rotation').value,
        size_mode: document.querySelector('input[name="logo-size-mode"]:checked')?.value || 'proportional'});
    const showMessage = (text, error = false) => { message.textContent = text; message.classList.toggle('error', error); };
    const samePath = (left, right) => !!left && !!right &&
        left.trim().replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase() ===
        right.trim().replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase();
    function buttonState() {
        apply.disabled = busy || !previewOK || !source.value.trim() || !destination.value.trim();
        useExport.disabled = busy || !(completedOutput || availableOutput);
    }
    function syncInspector() {
        document.querySelectorAll('[data-anchor]').forEach(button =>
            button.setAttribute('aria-pressed', String(button.dataset.anchor === $('logo-position').value)));
        for (const id of ['logo-width', 'logo-opacity', 'logo-offset-x', 'logo-offset-y']) {
            $(id + '-slider').value = $(id).value;
        }
        $('logo-rotation-label').textContent = `${$('logo-rotation').value}°`;
        updateSizeMode();
    }
    function updateSizeMode() {
        const locked = busy || settings().size_mode !== 'proportional';
        $('logo-width').disabled = locked;
        $('logo-width-slider').disabled = locked;
    }
    function updatePreviewView() {
        const showingBefore = $('logo-show-before').checked;
        before.hidden = !showingBefore;
        after.hidden = showingBefore;
        $('logo-empty-preview').hidden = showingBefore ? before.hasAttribute('src') : after.hasAttribute('src');
    }
    function updateFolderSummary() {
        const name = value => value.trim().replace(/[\\/]+$/, '').split(/[\\/]/).pop() || 'not chosen';
        $('logo-folder-summary').textContent = `${name(source.value)} → ${name(destination.value)}`;
    }
    async function jsonFetch(url, options = {}) {
        const response = await fetch(url, options);
        let data;
        try { data = await response.json(); } catch (_) { throw new Error(response.status === 413 ? 'Logo file is too large.' : 'The request failed.'); }
        if (!response.ok) throw new Error(data.error || 'The request failed.');
        return data;
    }
    function jsonOptions(data) { return {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)}; }
    function updateInputs(jobBusy) {
        busy = jobBusy;
        document.querySelectorAll('#sec-logo input, #sec-logo select, #sec-logo button').forEach(control => {
            if (control.id !== 'logo-hardware-toggle') control.disabled = jobBusy;
        });
        updateSizeMode();
        buttonState();
    }
    async function loadAssets(selected = 'default') {
        const data = await jsonFetch('/api/logo/assets');
        asset.replaceChildren();
        for (const item of data.assets) asset.add(new Option(item.name, item.id));
        if ([...asset.options].some(option => option.value === selected)) asset.value = selected;
        if (!asset.value) showMessage('Choose or upload a logo.', true);
    }
    async function loadPresets(selected = '') {
        presets = (await jsonFetch('/api/logo/presets')).presets;
        const list = $('logo-presets');
        list.replaceChildren(new Option('Choose a saved preset', ''));
        presets.forEach((preset, index) => list.add(new Option(preset.name, String(index))));
        list.value = selected;
    }
    function clearPreview() {
        previewSequence++;
        previewOK = false;
        before.removeAttribute('src'); after.removeAttribute('src');
        if (previewURL) URL.revokeObjectURL(previewURL);
        previewURL = null;
        updatePreviewView();
        buttonState();
    }
    function previewSoon() {
        previewSequence++;
        previewOK = false;
        buttonState();
        clearTimeout(previewTimer);
        previewTimer = setTimeout(renderPreview, 250);
    }
    async function renderPreview() {
        const serial = ++previewSequence;
        if (!source.value.trim() || !image.value || !asset.value) {
            clearPreview();
            showMessage('Choose a folder, logo, and preview image.');
            return;
        }
        showMessage('Rendering preview…');
        try {
            const response = await fetch('/api/logo/preview', jsonOptions({source: source.value.trim(), image: image.value,
                asset_id: asset.value, settings: settings()}));
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Preview failed.');
            }
            const blob = await response.blob();
            if (serial !== previewSequence) return;
            if (previewURL) URL.revokeObjectURL(previewURL);
            previewURL = URL.createObjectURL(blob);
            before.src = `/api/image?root=${encodeURIComponent(source.value.trim())}&file=${encodeURIComponent(image.value)}`;
            after.src = previewURL;
            updatePreviewView();
            previewOK = true;
            showMessage('Preview ready. Check placement before applying it to the folder.');
            buttonState();
        } catch (error) {
            if (serial !== previewSequence) return;
            previewOK = false; after.removeAttribute('src');
            updatePreviewView();
            showMessage(error.message, true); buttonState();
        }
    }
    async function loadImages() {
        const serial = ++imageSequence;
        clearPreview();
        const previous = image.value;
        image.replaceChildren(new Option('Loading images…', ''));
        if (!source.value.trim()) {
            image.replaceChildren(new Option('Choose a source folder first', ''));
            return;
        }
        try {
            const data = await jsonFetch(`/api/logo/images?root=${encodeURIComponent(source.value.trim())}`);
            if (serial !== imageSequence) return;
            image.replaceChildren();
            data.images.forEach(path => image.add(new Option(path, path)));
            if (!data.images.length) image.add(new Option('No supported images found', ''));
            if (data.images.includes(previous)) image.value = previous;
            $('logo-image-count').textContent = `${data.total} images found${data.total > data.images.length ? ` · first ${data.images.length} available for preview` : ''}`;
            previewSoon();
        } catch (error) {
            if (serial !== imageSequence) return;
            image.replaceChildren(new Option('No preview image available', ''));
            $('logo-image-count').textContent = '';
            showMessage(error.message, true);
        }
    }
    async function checkOutput() {
        const serial = ++outputSequence;
        const path = destination.value.trim();
        availableOutput = '';
        buttonState();
        if (!path || samePath(path, source.value)) return;
        try {
            const result = await jsonFetch(`/api/logo/images?root=${encodeURIComponent(path)}`);
            if (serial !== outputSequence || path !== destination.value.trim()) return;
            if (result.total > 0) {
                availableOutput = path;
                if (!completedOutput) $('logo-output-note').textContent = `Existing output contains ${result.total} images. You can use this folder for Shopify export.`;
            }
        } catch (_) {
            if (serial !== outputSequence) return;
        }
        buttonState();
    }
    source.addEventListener('change', () => {
        const value = source.value.trim();
        localStorage.setItem('logo_source', value);
        if (!destination.value.trim() || destination.value.trim() === autoDestination) {
            autoDestination = value ? value.replace(/[\\/]+$/, '') + '_with_logo' : '';
            destination.value = autoDestination;
            localStorage.setItem('logo_destination', autoDestination);
        }
        updateFolderSummary(); completedOutput = ''; availableOutput = ''; buttonState(); loadImages(); checkOutput();
    });
    destination.addEventListener('change', () => {
        localStorage.setItem('logo_destination', destination.value.trim());
        updateFolderSummary(); completedOutput = ''; availableOutput = ''; buttonState(); checkOutput();
    });
    $('logo-browse-source').addEventListener('click', () => window.JanviBrowse('logo_source'));
    $('logo-browse-destination').addEventListener('click', () => window.JanviBrowse('logo_destination'));
    [asset, image, ...controls.map($)].forEach(control => control.addEventListener('input', previewSoon));
    for (const id of ['logo-width', 'logo-opacity', 'logo-offset-x', 'logo-offset-y']) {
        $(id + '-slider').addEventListener('input', event => {
            $(id).value = event.target.value;
            $(id).dispatchEvent(new Event('input', {bubbles: true}));
        });
        $(id).addEventListener('input', () => { $(id + '-slider').value = $(id).value; });
    }
    document.querySelectorAll('[data-anchor]').forEach(button => button.addEventListener('click', () => {
        $('logo-position').value = button.dataset.anchor;
        syncInspector(); previewSoon();
    }));
    document.querySelectorAll('input[name="logo-size-mode"]').forEach(option => option.addEventListener('change', () => {
        updateSizeMode(); previewSoon();
    }));
    function rotate(delta) {
        $('logo-rotation').value = (Number($('logo-rotation').value) + delta + 360) % 360;
        syncInspector(); previewSoon();
    }
    $('logo-rotate-left').addEventListener('click', () => rotate(-90));
    $('logo-rotate-right').addEventListener('click', () => rotate(90));
    $('logo-show-before').addEventListener('change', updatePreviewView);
    $('logo-hardware-toggle').addEventListener('click', event => {
        const expanded = document.body.classList.toggle('logo-hardware-expanded');
        event.currentTarget.setAttribute('aria-expanded', String(expanded));
        event.currentTarget.textContent = expanded ? 'Hide hardware' : 'Show hardware';
    });
    $('logo-upload').addEventListener('change', async event => {
        const file = event.target.files[0];
        if (!file) return;
        try {
            showMessage('Saving logo…');
            const form = new FormData(); form.append('file', file);
            const saved = await jsonFetch('/api/logo/assets', {method: 'POST', body: form});
            await loadAssets(saved.id); previewSoon();
        } catch (error) { showMessage(error.message, true); }
        finally { event.target.value = ''; }
    });
    $('logo-save-preset').addEventListener('click', async () => {
        try {
            const saved = await jsonFetch('/api/logo/presets', jsonOptions({name: $('logo-preset-name').value,
                asset_id: asset.value, settings: settings()}));
            await loadPresets();
            $('logo-preset-name').value = '';
            showMessage(`Saved preset: ${saved.name}`);
        } catch (error) { showMessage(error.message, true); }
    });
    $('logo-presets').addEventListener('change', async event => {
        if (event.target.value === '') return;
        const preset = presets[Number(event.target.value)];
        if (!preset) return;
        try {
            await loadAssets(preset.asset_id);
            if (asset.value !== preset.asset_id) throw new Error('The logo for this preset is unavailable. Upload it again.');
            const values = preset.settings;
            $('logo-position').value = values.position;
            $('logo-width').value = values.width_pct;
            $('logo-opacity').value = values.opacity_pct;
            $('logo-offset-x').value = values.offset_x_pct;
            $('logo-offset-y').value = values.offset_y_pct;
            $('logo-rotation').value = values.rotation ?? 0;
            const mode = ['proportional', 'fit', 'fill'].includes(values.size_mode) ? values.size_mode : 'proportional';
            document.querySelector(`input[name="logo-size-mode"][value="${mode}"]`).checked = true;
            syncInspector();
            previewSoon();
        } catch (error) { showMessage(error.message, true); }
    });
    apply.addEventListener('click', async () => {
        try {
            apply.disabled = true;
            const data = await jsonFetch('/api/logo/apply', jsonOptions({source: source.value.trim(),
                destination: destination.value.trim(), asset_id: asset.value, settings: settings(),
                target_width: Number($('target-width').value), target_height: Number($('target-height').value)}));
            completedOutput = '';
            $('logo-output-note').textContent = data.message + ' Progress appears above.';
            updateInputs(true);
        } catch (error) { showMessage(error.message, true); buttonState(); }
    });
    useExport.addEventListener('click', () => {
        const field = $('export-src-input');
        field.value = completedOutput || availableOutput;
        field.dispatchEvent(new Event('change', {bubbles: true}));
        const mode = $('export-mode');
        mode.value = 'native';
        mode.dispatchEvent(new Event('change', {bubbles: true}));
        $('nav-pipe').click();
    });
    document.addEventListener('janvi-job-status', event => {
        const job = event.detail;
        updateInputs(job.active);
        if (job.task_type === 'logo' && job.job_id) {
            const log = $('logo-job-log');
            if (shownJob !== job.job_id) { shownJob = job.job_id; log.replaceChildren(); }
            for (const item of job.events || []) {
                const line = document.createElement('div'); line.textContent = item.message; log.append(line);
            }
            while (log.childElementCount > 500) log.firstElementChild.remove();
            if (job.events?.length) log.scrollTop = log.scrollHeight;
            $('logo-report-path').textContent = job.report_error || (job.report_path ? `Job report: ${job.report_path}` : '');
        }
        if (job.task_type === 'logo' && !job.active && job.results?.output_dir &&
                samePath(source.value, job.results.source_dir) && samePath(destination.value, job.results.output_dir)) {
            completedOutput = job.results.output_dir;
            $('logo-output-note').textContent = `Finished: ${job.succeeded} added · ${job.skipped || 0} skipped · ${job.failed} failed. Output: ${completedOutput}`;
        } else if (job.task_type === 'logo' && !job.active && job.results?.output_dir) {
            completedOutput = '';
            $('logo-output-note').textContent = availableOutput ? 'The selected output already contains images and can be used for Shopify export.' :
                'The last logo job used different folders. Run a new batch to use this output for Shopify export.';
        } else if (job.task_type === 'logo' && job.status === 'failed') {
            $('logo-output-note').textContent = `Logo job failed: ${job.error || 'See logs.'}`;
        } else if (job.task_type === 'logo' && job.status === 'cancelled') {
            $('logo-output-note').textContent = 'Cancelled. Completed output images remain in the selected output folder.';
        }
        buttonState();
    });
    (async () => {
        try {
            await Promise.all([loadAssets(), loadPresets()]);
            const dirs = await jsonFetch('/api/active-directory');
            source.value = localStorage.getItem('logo_source') || dirs.dest_dir || '';
            autoDestination = source.value ? source.value.replace(/[\\/]+$/, '') + '_with_logo' : '';
            destination.value = localStorage.getItem('logo_destination') || autoDestination;
            updateFolderSummary(); syncInspector(); updatePreviewView(); checkOutput();
            await loadImages();
            document.dispatchEvent(new Event('janvi-logo-ready'));
        } catch (error) { showMessage(error.message, true); }
    })();
});

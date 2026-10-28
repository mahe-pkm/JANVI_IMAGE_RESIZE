// Connected folders are opt-in so existing custom/Lightroom workflows remain usable.
document.addEventListener('DOMContentLoaded', () => {
    const $ = id => document.getElementById(id);
    const preset=$('size-preset'), width=$('target-width'), height=$('target-height'), ratio=$('size-ratio');
    function showRatio() { let a=Number(width.value),b=Number(height.value),x=a,y=b; while(y){const n=x%y;x=y;y=n;} ratio.textContent=(a>0&&b>0&&x) ? `Ratio ${a/x}:${b/x}` : 'Enter dimensions'; }
    preset.addEventListener('change',()=>{if(preset.value!=='custom'){[width.value,height.value]=preset.value.split('x');}showRatio();});
    [width,height].forEach(input=>input.addEventListener('input',()=>{preset.value='custom';showRatio();})); showRatio();
    const linked = $('workflow-linked'), output = $('workflow-output');
    let saved;
    try { saved = JSON.parse(localStorage.getItem('janvi_workflow') || '{}'); } catch (_) { saved = {}; }
    linked.checked = saved.linked !== false;
    output.value = saved.output || '';
    const resize = $('workflow-do-resize'), logoStage = $('workflow-do-logo'), exportStage = $('workflow-do-export');
    resize.checked = saved.resize !== false;
    logoStage.checked = saved.logo !== false;
    exportStage.checked = saved.export !== false;
    let ready = false, applying = false, busy = false, last = '', step = 'setup', routing = false;
    $('workflow-settings').parentElement.append($('workflow-settings'));
    const steps = () => ['setup', ...(resize.checked ? ['resize', 'review'] : []), ...(logoStage.checked ? ['logo'] : []), ...(exportStage.checked ? ['export'] : [])];
    function footer() {
        const next = steps()[steps().indexOf(step) + 1];
        $('workflow-next').hidden = !next;
        $('workflow-next').disabled = busy;
        $('workflow-next').textContent = next ? `Continue to ${next === 'review' ? 'image review' : next}` : 'Finished';
        const id = {resize: 'dest-dir-input', review: 'dest-dir-input', logo: 'logo-source', export: 'export-src-input'}[step];
        $('workflow-context').textContent = id ? `Using: ${$(id).value}` : 'Folders are shared by every enabled step. Originals are preserved.';
    }
    function navigate(next) {
        step = next;
        $('workflow-footer').hidden = !linked.checked;
        document.body.dataset.workflowStep = next;
        document.querySelectorAll('#workflow-steps button').forEach(button => {
            button.setAttribute('aria-current', button.dataset.step === next ? 'step' : 'false');
        });
        if (next === 'logo') {
            $('logo-source').dispatchEvent(new Event('change', {bubbles: true}));
            $('nav-logo').click();
        }
        else if (next === 'review') $('nav-pad').click();
        else {
            routing = true;
            try { $('nav-pipe').click(); } finally { routing = false; }
        }
        const title = $('sec-pipeline').querySelector('h1');
        title.textContent = ({setup: 'Choose folders and steps', resize: 'Resize images', export: 'Review and export'})[next] || 'Image workflow';
        footer();
    }
    const clean = path => path.trim().replace(/[\\/]+$/, '');
    function field(id, value) {
        const element = $(id);
        if (element.value === value) return;
        element.value = value;
        element.dispatchEvent(new Event('change', {bubbles: true}));
    }
    function connect() {
        if (!ready || applying || busy) return;
        applying = true;
        try {
            $('workflow-settings').hidden = !linked.checked;
            document.body.classList.toggle('workflow-linked', linked.checked);
            $('workflow-steps').hidden = !linked.checked;
            $('workflow-footer').hidden = !linked.checked;
            const source = clean($('root-dir-input').value);
            const base = clean(output.value) || (source ? source + '_output' : '');
            localStorage.setItem('janvi_workflow', JSON.stringify({linked: linked.checked, output: output.value.trim(), source, resize: resize.checked, logo: logoStage.checked, export: exportStage.checked}));
            if (!linked.checked || !source || !base) return;
            const separator = base.includes('\\') ? '\\' : '/';
            const resized = base + separator + 'Resized', logo = base + separator + 'With Logo';
            const fingerprint = JSON.stringify([source, base, resize.checked, logoStage.checked, exportStage.checked]);
            if (last === fingerprint) return;
            last = fingerprint;
            $('use-default-output').checked = false;
            $('use-default-output').dispatchEvent(new Event('change'));
            field('dest-dir-input', resized);
            field('logo-source', resize.checked ? resized : source);
            field('logo-destination', logo);
            field('export-src-input', logoStage.checked ? logo : (resize.checked ? resized : source));
            field('export-dest-input', base + separator + 'Final For Shopify');
            field('export-mode', 'native');
            $('workflow-paths').textContent = [resize.checked ? `Resize → ${resized}` : '', logoStage.checked ? `Logo → ${logo}` : '', exportStage.checked ? `Shopify → ${base + separator + 'Final For Shopify'}` : ''].filter(Boolean).join('\n');
            document.querySelector('[data-step="resize"]').disabled = !resize.checked;
            document.querySelector('[data-step="review"]').disabled = !resize.checked;
            document.querySelector('[data-step="logo"]').disabled = !logoStage.checked;
            document.querySelector('[data-step="export"]').disabled = !exportStage.checked;
            footer();
        } finally { applying = false; }
    }
    linked.addEventListener('change', () => { last = ''; connect(); navigate('setup'); });
    [resize, logoStage, exportStage].forEach(element => element.addEventListener('change', connect));
    output.addEventListener('change', connect);
    document.addEventListener('janvi-root-changed', connect);
    document.addEventListener('janvi-directories-ready', () => { ready = true; connect(); if (linked.checked) navigate('setup'); });
    document.addEventListener('janvi-logo-ready', () => { last = ''; connect(); });
    document.addEventListener('janvi-job-status', event => {
        const wasBusy = busy;
        busy = !!event.detail.active;
        [linked, output, resize, logoStage, exportStage, $('workflow-browse')].forEach(element => { element.disabled = busy; });
        if (wasBusy && !busy) connect();
        footer();
    });
    $('workflow-browse').addEventListener('click', async () => {
        try {
            let result;
            if (window.JanviDesktop) result = await window.JanviDesktop.selectFolder(output.value);
            else {
                const response = await fetch('/api/select-folder', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({initial_dir: output.value})});
                result = await response.json();
            }
            if (result.error) throw new Error(result.error);
            if (result.selected_path) { output.value = result.selected_path; connect(); }
        } catch (error) { $('workflow-paths').textContent = error.message; }
    });
    $('workflow-next').addEventListener('click', () => {
        const next = steps()[steps().indexOf(step) + 1];
        if (next && !busy) navigate(next);
    });
    $('shopify-export-settings').append($('btn-export'));
    document.querySelectorAll('#workflow-steps button').forEach(button => button.addEventListener('click', () => navigate(button.dataset.step)));
    $('nav-pipe').addEventListener('click', () => {
        if (!linked.checked) return;
        if (!routing) { navigate('setup'); return; }
        document.body.dataset.workflowStep = step;
    });
    // Keep the stage bar accurate when the existing sidebar is used.
    function sidebarStep(value) {
        if (!linked.checked) return;
        step = value; document.body.dataset.workflowStep = value;
        document.querySelectorAll('#workflow-steps button').forEach(button => button.setAttribute('aria-current', button.dataset.step === value ? 'step' : 'false'));
        $('workflow-footer').hidden = false; footer();
    }
    $('nav-logo').addEventListener('click', () => sidebarStep('logo'));
    $('nav-pad').addEventListener('click', () => sidebarStep('review'));
    $('nav-dash').addEventListener('click', () => { $('workflow-footer').hidden = true; });
    const hardware = document.querySelector('.device-card');
    const toggle = document.createElement('button');
    hardware.id = 'hardware-settings';
    toggle.setAttribute('aria-controls', hardware.id);
    $('usage-gpu-settings').setAttribute('aria-controls', hardware.id);
    toggle.type = 'button'; toggle.className = 'btn btn-secondary btn-sm workflow-hardware';
    toggle.textContent = 'Hardware and processing method'; toggle.setAttribute('aria-expanded', 'false');
    hardware.before(toggle); hardware.classList.add('workflow-hardware-closed');
    function showHardware(open) {
        const closed = !open;
        hardware.classList.toggle('workflow-hardware-closed', closed);
        document.body.classList.toggle('logo-hardware-expanded', !closed);
        toggle.setAttribute('aria-expanded', String(!closed));
        $('usage-gpu-settings').setAttribute('aria-expanded', String(!closed));
    }
    toggle.addEventListener('click', () => {
        showHardware(hardware.classList.contains('workflow-hardware-closed'));
    });
    $('usage-gpu-settings').addEventListener('click', () => {
        showHardware(true);
        hardware.scrollIntoView({behavior: 'smooth', block: 'start'});
        hardware.tabIndex = -1;
        hardware.focus({preventScroll: true});
    });
    $('logo-hardware-toggle').hidden = true;
    let repairTimer = null;
    async function refreshPhotoshop() {
        const source=$('root-dir-input').value.trim().replace(/[\\/]+$/, '');
        const defaultDestination=/[\\/]resizing$/i.test(source) ? source.replace(/resizing$/i,'Re-sized') : source+'_resized';
        const destination = $('use-default-output').checked ? defaultDestination : $('dest-dir-input').value.trim();
        const query = new URLSearchParams({dest_dir:destination});
        const download = $('photoshop-script-download');
        $('photoshop-errors').replaceChildren();
        try {
            const response = await fetch('/api/photoshop/status?' + query, {cache:'no-store'});
            const data = await response.json();
            if(!response.ok)throw Error(data.error || 'Cannot read Photoshop status');
            download.hidden=!data.available || !data.total;
            download.href='/api/photoshop/script?' + query;
            $('photoshop-repair-path').textContent=data.script || '';
            const report=data.report || {};
            if (repairTimer && ['completed', 'needs_attention', 'cancelled'].includes(report.status)) { clearInterval(repairTimer); repairTimer=null; }
            const done=(report.items || []).filter(item=>item.status==='done').length;
            $('photoshop-repair-status').textContent=data.available ? `${done} / ${data.total} repaired · ${report.status || 'Ready to run'}${data.missing_geometry ? ' · '+data.missing_geometry+' older files need a new resize to record bounds' : ''}` : data.message;
            for(const item of report.items || [])if(item.error){const row=document.createElement('li');row.textContent=item.file+': '+item.error;$('photoshop-errors').append(row);}
        } catch(error){download.hidden=true;$('photoshop-repair-status').textContent=error.message;}
    }
    $('photoshop-refresh').addEventListener('click', refreshPhotoshop);
    $('dest-dir-input').addEventListener('change', refreshPhotoshop);
    if (window.JanviDesktop) {
        const start=$('photoshop-start'); start.hidden=false;
        start.addEventListener('click', async()=>{
            const source=$('root-dir-input').value.trim().replace(/[\\/]+$/, '');
            const destination=$('use-default-output').checked ? (/[\\/]resizing$/i.test(source) ? source.replace(/resizing$/i,'Re-sized') : source+'_resized') : $('dest-dir-input').value.trim();
            try { start.disabled=true; await window.JanviDesktop.startPhotoshopRepair(destination); $('photoshop-repair-status').textContent='Opening regular Photoshop. If asked whether to run Repair_Padding.jsx, choose Yes. Repair starts after confirmation.'; if(repairTimer)clearInterval(repairTimer); repairTimer=setInterval(refreshPhotoshop,3000); }
            catch(error){$('photoshop-repair-status').textContent=error.message;} finally { start.disabled=false; }
        });
        window.JanviDesktop.onPhotoshopError(error=>{if(repairTimer)clearInterval(repairTimer);repairTimer=null;$('photoshop-repair-status').textContent=error;});
        const openFolder=folder=>{if(!folder || busy)return; const input=$('root-dir-input');input.value=folder;input.dispatchEvent(new Event('change',{bubbles:true}));input.dispatchEvent(new Event('input',{bubbles:true}));};
        window.JanviDesktop.onOpenFolder(openFolder);
        window.addEventListener('focus',async()=>{try{openFolder(await window.JanviDesktop.initialFolder());}catch(_){}});
        document.addEventListener('janvi-directories-ready',async()=>{try{openFolder(await window.JanviDesktop.initialFolder());}catch(_){}});
    }
    $('nav-pad').addEventListener('click', refreshPhotoshop);
    document.addEventListener('janvi-directories-ready',refreshPhotoshop);
    if (window.JanviDesktop) {
        const zone = output.parentElement;
        zone.addEventListener('dragover', event => { event.preventDefault(); });
        zone.addEventListener('drop', async event => {
            event.preventDefault();
            if (busy) return;
            try {
                if (event.dataTransfer.files.length !== 1) throw new Error('Drop one folder at a time.');
                const result = await window.JanviDesktop.validateDroppedFolder(event.dataTransfer.files[0]);
                if (result) { output.value = result; connect(); }
            } catch (error) { $('workflow-paths').textContent = error.message; }
        });
    }
});

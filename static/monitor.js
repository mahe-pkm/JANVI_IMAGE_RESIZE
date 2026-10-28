window.JanviMonitor = (() => {
    let devices = [], method = 'cpu', busy = false, sampling = false, adoptedJob = null;
    const byId = id => document.getElementById(id);
    const text = (id, value) => { byId(id).textContent = value; };
    const valid = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
    const bytes = value => !valid(value) ? 'Unavailable' : `${(value / 1073741824).toFixed(2)} GB`;
    function usage(id, value) {
        const meter = byId(id);
        meter.hidden = !valid(value);
        meter.value = valid(value) ? Math.min(100, value) : 0;
    }
    function unavailable() {
        ['metric-cpu', 'metric-ram', 'metric-app-cpu', 'metric-app-ram', 'metric-vram'].forEach(id => text(id, 'Unavailable'));
        usage('usage-cpu', null); usage('usage-ram', null); usage('usage-gpu', null);
        const device = devices.find(d => d.id === selectedDevice());
        text('metric-gpu', device?.kind === 'cpu' ? 'CPU selected' : 'Unavailable');
        text('metric-gpu-name', device?.name || 'No GPU selected');
        byId('metric-gpu-name').title = device?.name || 'No GPU selected';
        text('metric-shared', 'Shared unavailable');
        if (device?.kind === 'cpu') { text('metric-vram', '—'); text('metric-shared', 'Shared —'); }
    }
    const duration = value => value == null ? '—' : `${Math.floor(value / 60)}m ${Math.floor(value % 60)}s`;
    const selectedDevice = () => byId('device-select').value;
    const backendLabel = provider => ({CPUExecutionProvider: 'CPU processing', DmlExecutionProvider: 'Windows GPU processing', filesystem: 'File copy'})[provider] || provider;
    function populate() {
        const select = byId('device-select'), previous = select.value;
        select.replaceChildren();
        const matches = devices.filter(d => d.kind === method);
        for (const device of matches) {
            const option = new Option(`${device.name}${device.available ? '' : ' · Unavailable'}`, device.id);
            option.disabled = !device.available;
            select.append(option);
        }
        if (!matches.length) {
            select.add(new Option('No compatible device detected', ''));
        }
        if (matches.some(d => d.id === previous && d.available)) select.value = previous;
        else select.value = matches.find(d => d.available)?.id || '';
        document.querySelectorAll('[data-method]').forEach(button => {
            const active = button.dataset.method === method;
            button.classList.toggle('active', active);
            button.setAttribute('aria-pressed', String(active));
        });
        detail();
    }
    function detail() {
        const device = devices.find(d => d.id === selectedDevice());
        text('device-detail', device ? `${device.reason} · ${backendLabel(device.provider)}` : 'This processing method is unavailable on this PC. Choose CPU or another available device.');
        ['btn-audit', 'btn-resize'].forEach(id => { byId(id).disabled = busy || !device?.available; });
    }
    async function refresh() {
        try {
            const response = await fetch('/api/devices', {cache: 'no-store'});
            if (!response.ok) throw new Error('Hardware detection failed');
            devices = (await response.json()).devices;
            populate();
        } catch (error) { text('device-detail', error.message); }
    }
    async function metrics() {
        if (sampling) return;
        sampling = true;
        try {
            const response = await fetch('/api/telemetry', {cache: 'no-store'});
            if (!response.ok) throw new Error('Telemetry unavailable');
            const data = await response.json();
            if (valid(data.sampled_at) && Date.now() / 1000 - data.sampled_at > 10) throw new Error('Telemetry is stale');
            text('metric-cpu', !valid(data.cpu_percent) ? 'Unavailable' : `${data.cpu_percent.toFixed(1)}%`);
            text('metric-app-cpu', `App ${!valid(data.app_cpu_percent) ? 'Unavailable' : data.app_cpu_percent + '%'}`);
            text('metric-ram', data.ram_total_bytes > 0 && valid(data.ram_used_bytes) ? `${bytes(data.ram_used_bytes)} / ${bytes(data.ram_total_bytes)}` : 'Unavailable');
            text('metric-app-ram', `App ${bytes(data.app_ram_bytes)}`);
            usage('usage-cpu', data.cpu_percent);
            usage('usage-ram', data.ram_total_bytes > 0 && valid(data.ram_used_bytes) ? data.ram_used_bytes / data.ram_total_bytes * 100 : null);
            const device = devices.find(d => d.id === selectedDevice());
            const gpu = data.gpus?.[device?.luid] || {};
            text('metric-gpu', device?.kind === 'cpu' ? 'CPU selected' : !valid(gpu.utilization_percent) ? 'Unavailable' : `${gpu.utilization_percent.toFixed(1)}%`);
            text('metric-gpu-name', device?.kind === 'cpu' ? 'CPU processing' : device?.name || 'No GPU selected');
            byId('metric-gpu-name').title = device?.name || 'No GPU selected';
            usage('usage-gpu', device?.kind === 'cpu' ? null : gpu.utilization_percent);
            text('metric-vram', device?.kind === 'cpu' ? '—' : bytes(gpu.dedicated_bytes));
            text('metric-shared', `Shared ${device?.kind === 'cpu' ? '—' : bytes(gpu.shared_bytes)}`);
        } catch (_) {
            unavailable();
        } finally { sampling = false; }
    }
    function renderJob(job) {
        busy = job.active;
        const actualId = job.device?.id || job.requested_device_id;
        const runningDevice = devices.find(d => d.id === actualId);
        if (job.job_id && runningDevice && job.task_type !== 'export' && (busy || adoptedJob !== job.job_id)) {
            method = runningDevice.kind;
            populate();
            byId('device-select').value = runningDevice.id;
            adoptedJob = job.job_id;
        }
        if (job.device?.validated) {
            const device = devices.find(d => d.id === job.device.id);
            if (device) device.reason = 'Validated on last run';
        }
        document.querySelectorAll('[data-method]').forEach(button => { button.disabled = busy; });
        byId('device-select').disabled = busy;
        byId('refresh-devices').disabled = busy;
        byId('btn-export').disabled = busy;
        byId('btn-cancel').disabled = !busy || job.status === 'cancelling';
        text('task-title', job.status === 'idle' ? 'Ready to process' : `${job.task_type} · ${job.phase}`);
        text('task-filename', job.current_file || 'Choose a source folder and processing method');
        const bar = byId('task-progress-bar');
        bar.style.width = `${job.progress}%`;
        bar.setAttribute('aria-valuenow', job.progress);
        text('task-progress-text', `${job.progress}% · ${job.status.replaceAll('_', ' ')}`);
        text('task-count-text', `${job.current} / ${job.total} finished · ${job.succeeded} succeeded · ${job.failed} failed${job.skipped ? ` · ${job.skipped} skipped` : ''}`);
        text('task-timing', `Elapsed ${duration(job.elapsed_seconds)} · Speed ${job.images_per_minute ?? '—'} images/min · Remaining ${duration(job.eta_seconds)}`);
        text('task-result', job.error || (job.device ? `Actual processing device: ${job.device.name} · ${backendLabel(job.device.provider)}` : ''));
        byId('active-task-card').dataset.state = job.status;
        detail();
    }
    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('[data-method]').forEach(button => button.addEventListener('click', () => {
            method = button.dataset.method; populate(); metrics();
        }));
        byId('device-select').addEventListener('change', () => { detail(); metrics(); });
        byId('refresh-devices').addEventListener('click', refresh);
        refresh(); metrics(); setInterval(metrics, 1500);
    });
    return {selectedDevice, renderJob};
})();

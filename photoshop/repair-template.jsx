#target photoshop
// Janvi sequential padding repair. No action installation or GPT service needed.
(function () {
    var queue = /*__JANVI_QUEUE__*/null;
    if (!queue) throw Error('Generate this script from a Janvi resize job first.');
    var workspace = File($.fileName).parent;
    var root = Folder(queue.original_root);
    var reportFile = File(workspace.fsName + '/' + queue.report);
    var backupRoot = Folder(root.parent.fsName + '/.janvi-photoshop-backups/' + queue.fingerprint);
    var report = {schema_version:1, fingerprint:queue.fingerprint, status:'ready', items:[]};
    var owned = null, stop = false, lockAcquired = false, lock = Folder(workspace.fsName + '/.janvi-photoshop-running');
    var originalDialogs = app.displayDialogs, originalUnits = app.preferences.rulerUnits;

    function quote(s) {
        return '"' + String(s).replace(/["\\\x00-\x1f]/g, function(c) {
            if (c === '"' || c === '\\') return '\\' + c;
            return '\\u' + ('0000'+c.charCodeAt(0).toString(16)).slice(-4);
        }) + '"';
    }
    function json(v) {
        if (v === null) return 'null';
        if (typeof v === 'string') return quote(v);
        if (typeof v === 'number' || typeof v === 'boolean') return String(v);
        var a=[], k;
        if (v instanceof Array) { for(k=0;k<v.length;k++) a.push(json(v[k])); return '['+a.join(',')+']'; }
        for(k in v) if(v.hasOwnProperty(k)) a.push(quote(k)+':'+json(v[k]));
        return '{'+a.join(',')+'}';
    }
    // Strict JSON parser: checkpoint data is never evaluated as JavaScript.
    function parse(s) {
        var i=0;
        function ws(){while(/\s/.test(s.charAt(i)) && i<s.length)i++;}
        function str(){
            var out='', c, h; if(s.charAt(i++)!=='"')throw Error('Invalid checkpoint string');
            while(i<s.length){c=s.charAt(i++); if(c==='"')return out;
                if(c==='\\'){c=s.charAt(i++); if(c==='u'){h=s.substr(i,4);if(!/^[0-9a-f]{4}$/i.test(h))throw Error('Invalid escape');out+=String.fromCharCode(parseInt(h,16));i+=4;}
                    else if(c==='"'||c==='\\'||c==='/')out+=c;
                    else if(c==='n')out+='\n';else if(c==='r')out+='\r';else if(c==='t')out+='\t';else if(c==='b')out+='\b';else if(c==='f')out+='\f';else throw Error('Invalid escape');}
                else {if(c.charCodeAt(0)<32)throw Error('Invalid string');out+=c;}}
            throw Error('Unclosed string');
        }
        function val(depth){
            if(depth>30)throw Error('Checkpoint too deep');ws();var c=s.charAt(i),o,k,m;
            if(c==='"')return str();
            if(c==='{'||c==='['){var array=c==='[';i++;o=array?[]:{};ws();if(s.charAt(i)===(array?']':'}')){i++;return o;}
                while(true){ws();if(array)o.push(val(depth+1));else{k=str();if(k==='__proto__'||k==='constructor'||k==='prototype')throw Error('Invalid key');ws();if(s.charAt(i++)!==':')throw Error('Invalid object');o[k]=val(depth+1);}
                    ws();c=s.charAt(i++);if(c===(array?']':'}'))return o;if(c!==',')throw Error('Invalid checkpoint');}}
            m=/^(true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(s.substr(i));
            if(!m)throw Error('Invalid checkpoint value');i+=m[0].length;
            return m[0]==='true'?true:m[0]==='false'?false:m[0]==='null'?null:Number(m[0]);
        }
        var result=val(0);ws();if(i!==s.length)throw Error('Trailing checkpoint data');return result;
    }
    function read(file){file.encoding='UTF8';if(!file.open('r'))throw Error('Cannot read '+file.fsName);var s=file.read();file.close();return s;}
    function writeReport(){
        report.updated_at=new Date().toUTCString();
        var temp=File(reportFile.fsName+'.tmp'), previous=File(reportFile.fsName+'.previous');
        temp.encoding='UTF8';if(!temp.open('w'))throw Error('Cannot write checkpoint');
        var ok=temp.write(json(report));temp.close();if(!ok)throw Error('Checkpoint write failed');
        if(previous.exists && !previous.remove())throw Error('Cannot rotate checkpoint');
        if(reportFile.exists && !reportFile.rename(previous.name))throw Error('Cannot preserve checkpoint');
        if(!temp.rename(queue.report)){if(previous.exists)previous.rename(queue.report);throw Error('Cannot commit checkpoint');}
        reportFile=File(workspace.fsName+'/'+queue.report);
    }
    function mkdir(folder){if(folder.exists)return;if(folder.parent.fsName!==folder.fsName)mkdir(folder.parent);if(!folder.create())throw Error('Cannot create '+folder.fsName);}
    function safeFile(relative){
        if(!relative || /(^|[\\\/])\.\.([\\\/]|$)|^[\\\/]|:/.test(relative))throw Error('Unsafe relative path');
        var file=File(root.fsName+'/'+relative);
        if(file.alias)throw Error('Linked files are not supported');
        var parent=file.parent;
        while(parent.fsName!==root.fsName){if(parent.alias || parent.parent.fsName===parent.fsName)throw Error('File is outside the output folder');parent=parent.parent;}
        return file;
    }
    // CRC32 + byte count detects accidental changes without slow ES3 SHA rounds.
    // SHA-256 remains in the app-generated manifest as an audit fingerprint.
    function fileChecksum(file){
        var table=[],crc=-1,total=0,i,j,c;
        for(i=0;i<256;i++){c=i;for(j=0;j<8;j++)c=(c&1)?(0xedb88320^(c>>>1)):(c>>>1);table[i]=c;}
        file.encoding='BINARY';if(!file.open('r'))throw Error('Cannot verify '+file.fsName);
        try{while(!file.eof){var chunk=file.read(65536);if(!chunk.length)break;total+=chunk.length;
            for(i=0;i<chunk.length;i++)crc=(crc>>>8)^table[(crc^(chunk.charCodeAt(i)&255))&255];}}
        finally{file.close();}
        return ('00000000'+((crc^-1)>>>0).toString(16)).slice(-8)+':'+total;
    }
    function selection(doc,geometry){
        var rects=geometry.rectangles;
        if(!rects.length)throw Error('No padding rectangles');
        for(var i=0;i<rects.length;i++){
            var r=rects[i];
            if(r.width<=0||r.height<=0||r.x<0||r.y<0||r.x+r.width>geometry.canvas_width||r.y+r.height>geometry.canvas_height)throw Error('Invalid padding rectangle');
            doc.selection.select([[r.x,r.y],[r.x+r.width,r.y],[r.x+r.width,r.y+r.height],[r.x,r.y+r.height]],i===0?SelectionType.REPLACE:SelectionType.EXTEND,0,false);
        }
    }
    function saveCopy(doc,file,ext){
        var options;
        if(ext==='jpg'||ext==='jpeg'){options=new JPEGSaveOptions();options.quality=12;options.embedColorProfile=true;options.formatOptions=FormatOptions.STANDARDBASELINE;}
        else if(ext==='png'){options=new PNGSaveOptions();options.interlaced=false;options.compression=9;}
        else if(ext==='tif'||ext==='tiff'){options=new TiffSaveOptions();options.imageCompression=TIFFEncoding.TIFFLZW;options.layers=false;options.embedColorProfile=true;}
        else throw Error('Automated save currently supports JPG, PNG and TIFF. Other formats need manual review.');
        doc.saveAs(file,options,true,Extension.LOWERCASE);
    }
    function itemFor(file){for(var i=0;i<report.items.length;i++)if(report.items[i].file===file)return report.items[i];var item={file:file,status:'pending'};report.items.push(item);return item;}
    var palette;
    try {
        var manifestFile=File(workspace.fsName+'/padding_manifest.json');
        if(!manifestFile.exists || parse(read(manifestFile)).fingerprint!==queue.fingerprint)throw Error('Cannot locate the matching Janvi repair workspace. Keep this script inside .janvi beside the resized images.');
        if(lock.exists)throw Error('A repair run may already be active. Close/cancel it before removing the .janvi-photoshop-running lock folder and restarting.');
        if(app.documents.length)throw Error('Close your open Photoshop documents before starting this batch.');
        if(!queue.entries.length)throw Error('No padded images with known geometry are queued.');
        if(reportFile.exists)report=parse(read(reportFile));
        else if(File(reportFile.fsName+'.previous').exists)report=parse(read(File(reportFile.fsName+'.previous')));
        if(report.fingerprint!==queue.fingerprint || !(report.items instanceof Array))throw Error('Checkpoint does not match this queue');
        if(!lock.create())throw Error('Cannot acquire repair lock');
        lockAcquired=true;
        app.displayDialogs=DialogModes.NO;app.preferences.rulerUnits=Units.PIXELS;
        palette=new Window('palette','Janvi padding repair');
        var label=palette.add('statictext',undefined,'Starting...');label.preferredSize.width=420;
        var cancel=palette.add('button',undefined,'Stop after current image');cancel.onClick=function(){stop=true;};palette.show();
        report.status='running';writeReport();
        for(var index=0;index<queue.entries.length;index++){
            palette.update();if(stop){report.status='paused';break;}
            var entry=queue.entries[index],item=itemFor(entry.file),file=safeFile(entry.file),nativePath=file.fsName;
            var name=nativePath.substring(Math.max(nativePath.lastIndexOf('/'),nativePath.lastIndexOf('\\'))+1),temporary=null,committed=false;
            try{
                if(item.status==='committing' && item.hold){var held=safeFile(item.hold);if(!file.exists&&held.exists&&!held.rename(name))throw Error('Cannot recover interrupted commit');}
                if(!file.exists)throw Error('Image missing');
                var currentHash=fileChecksum(file);
                if((item.status==='done'||item.status==='committing')&&item.output_checksum===currentHash){item.status='done';writeReport();continue;}
                if(currentHash!==entry.file_checksum)throw Error('File changed since resizing; it was not overwritten');
                label.text=(index+1)+' / '+queue.entries.length+' - '+entry.file;palette.update();
                var ext=entry.file.split('.').pop().toLowerCase();
                if(!/^(jpg|jpeg|png|tif|tiff)$/.test(ext))throw Error('Unsupported save format; manual review required');
                item.status='processing';item.error='';writeReport();
                var free=app.freeMemory;
                if(typeof free==='number' && free<536870912)throw Error('Photoshop has less than 512 MiB free memory. Free memory and rerun to resume.');
                if(typeof free==='number')item.available_memory_bytes=free;
                var backup=File(backupRoot.fsName+'/'+entry.file);mkdir(backup.parent);
                if(!backup.exists&&!file.copy(backup.fsName))throw Error('Cannot create recovery copy');
                if(fileChecksum(backup)!==entry.file_checksum)throw Error('Recovery copy does not match input');
                owned=app.open(file);
                if(owned.width.as('px')!==entry.geometry.canvas_width||owned.height.as('px')!==entry.geometry.canvas_height)throw Error('Image dimensions changed');
                selection(owned,entry.geometry);
                var before=owned.activeHistoryState,layerCount=owned.layers.length;
                executeAction(stringIDToTypeID('removeButton'),undefined,DialogModes.NO);
                if(owned.activeHistoryState===before || owned.layers.length<=layerCount)throw Error('Remove did not produce a confirmed edit layer');
                // Keep edits exactly inside padding; Remove can feather across its boundary.
                selection(owned,entry.geometry);owned.selection.invert();owned.selection.clear();owned.selection.deselect();
                owned.flatten();
                var nonce=new Date().getTime()+'-'+index;
                var transactionRoot=Folder(backupRoot.fsName+'/transactions');mkdir(transactionRoot);
                temporary=File(transactionRoot.fsName+'/rendered-'+nonce+'.'+ext);
                saveCopy(owned,temporary,ext);owned.close(SaveOptions.DONOTSAVECHANGES);owned=null;
                owned=app.open(temporary);
                if(owned.width.as('px')!==entry.geometry.canvas_width||owned.height.as('px')!==entry.geometry.canvas_height)throw Error('Saved image validation failed');
                owned.close(SaveOptions.DONOTSAVECHANGES);owned=null;
                item.output_checksum=fileChecksum(temporary);
                var rendered=temporary;
                temporary=File(file.parent.fsName+'/.__janvi_repair_'+nonce+'.pending');
                if(!rendered.copy(temporary.fsName)||fileChecksum(temporary)!==item.output_checksum)throw Error('Cannot stage validated output');
                if(fileChecksum(file)!==entry.file_checksum)throw Error('Input changed during processing');
                var holdName='.__janvi_previous_'+nonce+'.hold';
                item.hold=entry.file.substring(0,entry.file.lastIndexOf('/')+1)+holdName;
                item.status='committing';writeReport();
                var heldFile=File(file.parent.fsName+'/'+holdName);
                if(!file.rename(holdName))throw Error('Cannot preserve old file for commit');
                if(!temporary.rename(name)){heldFile.rename(name);throw Error('Cannot commit repaired image; check the original/recovery file');}
                committed=true;
                item.status='done';item.completed_at=new Date().toUTCString();writeReport();
                if(heldFile.exists)heldFile.remove(); // Only the transaction's .hold file, after commit.
                if(rendered.exists)rendered.remove();
            } catch(error){
                if(owned){try{owned.close(SaveOptions.DONOTSAVECHANGES);}catch(_){}owned=null;}
                item.error=String(error);item.status=committed||item.status==='committing'?'committing':'needs_attention';
                report.status='needs_attention';writeReport();break;
            }
        }
        if(report.status==='running')report.status='completed';
        report.done=0;for(var j=0;j<report.items.length;j++)if(report.items[j].status==='done')report.done++;
        writeReport();
        if(palette){palette.close();palette=null;}
        alert('Janvi padding repair: '+report.status+'\nCompleted '+report.done+' / '+queue.entries.length+'\n'+reportFile.fsName+'\nReview the repaired images before logo placement.');
    } catch(error){alert('Janvi repair stopped: '+error);}
    finally{
        if(owned){try{owned.close(SaveOptions.DONOTSAVECHANGES);}catch(_){} }
        if(palette)try{palette.close();}catch(_){}
        app.displayDialogs=originalDialogs;app.preferences.rulerUnits=originalUnits;
        // Remove only the lock acquired by this invocation.
        if(lockAcquired && lock.exists)lock.remove();
    }
})();

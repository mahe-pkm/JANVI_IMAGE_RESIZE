"""Build a per-user MSI from the verified, clean portable release folder."""
from pathlib import Path
import hashlib
import subprocess
import uuid
import xml.etree.ElementTree as ET
import argparse

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'dist' / 'Janvi-Image-Resize-0.2.0-icon-win-x64'
WIX = ROOT / '.build' / 'wix' / 'wix.exe'
BUILD = ROOT / '.build' / 'msi'
OUTPUT = ROOT / 'dist' / 'Janvi-Image-Resize-0.2.1-win-x64.msi'
NS = 'http://wixtoolset.org/schemas/v4/wxs'
UI = 'http://wixtoolset.org/schemas/v4/wxs/ui'
ET.register_namespace('', NS)
ET.register_namespace('ui', UI)

def tag(name): return f'{{{NS}}}{name}'
def stable_id(prefix, value): return prefix + hashlib.sha256(value.encode('utf-8')).hexdigest()[:24]
def main():
    global RELEASE, OUTPUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', type=Path, default=RELEASE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--desktop', action='store_true')
    parser.add_argument('--version')
    args = parser.parse_args()
    RELEASE, OUTPUT = args.release.resolve(), args.output.resolve()
    product_name = 'Janvi Image Studio' if args.desktop else 'Janvi Image Resize'
    launcher_name = 'Janvi Image Studio.exe' if args.desktop else 'JanviLauncher.exe'
    version = args.version or ('0.3.0' if args.desktop else '0.2.1')
    upgrade_code = '{54DFEB8B-3BF8-45DD-BF79-C9F1A89A4BA7}' if args.desktop else '{C1336DA9-0C77-468D-9157-8819DDB83D22}'
    registry = r'Software\Janvi\ImageStudio' if args.desktop else r'Software\Janvi\ImageResize'
    icon = RELEASE / ('resources/backend/assets/janvi-app.ico' if args.desktop else 'assets/janvi-app.ico')
    if OUTPUT.exists(): raise FileExistsError(f'Preserving existing installer: {OUTPUT}')
    if not (RELEASE / launcher_name).is_file() or not WIX.is_file():
        raise RuntimeError('The clean release folder or local WiX tool is missing.')
    if any((RELEASE / p).exists() for p in ('data', '.runtime', 'resources/backend/data', 'resources/backend/.runtime')):
        raise RuntimeError('Release folder contains user data or a private runtime; refuse to package it.')
    BUILD.mkdir(parents=True, exist_ok=True)
    notice = BUILD / 'notice.rtf'
    notice.write_text(r'{\rtf1\ansi\deff0 {\fonttbl {\f0 Segoe UI;}}\f0\fs20 Janvi Image Resize setup.\par This package contains third-party software; see THIRD_PARTY_NOTICES.md in the installed folder for license notices.}', encoding='ascii')
    wix = ET.Element(tag('Wix'))
    package = ET.SubElement(wix, tag('Package'), Name=product_name, Manufacturer='Janvi', Version=version,
                            UpgradeCode=upgrade_code, Scope='perUser')
    ET.SubElement(package, tag('MajorUpgrade'), DowngradeErrorMessage=f'A newer version of {product_name} is already installed.')
    ET.SubElement(package, tag('MediaTemplate'), EmbedCab='yes')
    ET.SubElement(package, tag('Icon'), Id='JanviIcon', SourceFile=str(icon))
    ET.SubElement(package, tag('Property'), Id='ARPPRODUCTICON', Value='JanviIcon')
    install_location = ET.SubElement(package, tag('Property'), Id='INSTALLFOLDER')
    ET.SubElement(install_location, tag('RegistrySearch'), Id='PreviousInstallFolder', Root='HKCU', Key=registry, Name='InstallFolder', Type='raw')
    ET.SubElement(package, tag('WixVariable'), Id='WixUILicenseRtf', Value=str(notice))
    ET.SubElement(package, f'{{{UI}}}WixUI', Id='WixUI_Minimal')
    local = ET.SubElement(package, tag('StandardDirectory'), Id='LocalAppDataFolder')
    appdir = ET.SubElement(local, tag('Directory'), Id='INSTALLFOLDER', Name=product_name)
    ET.SubElement(package, tag('StandardDirectory'), Id='ProgramMenuFolder')
    ET.SubElement(package, tag('StandardDirectory'), Id='DesktopFolder')
    components = ET.SubElement(package, tag('ComponentGroup'), Id='AppComponents', Directory='INSTALLFOLDER')
    directory_ids = {Path('.'): 'INSTALLFOLDER'}
    for path in sorted((p for p in RELEASE.rglob('*') if p.is_dir()), key=lambda p: (len(p.relative_to(RELEASE).parts), str(p))):
        relative = path.relative_to(RELEASE)
        parent = directory_ids.get(relative.parent)
        if parent is None: raise RuntimeError('Directory order error')
        directory_ids[relative] = stable_id('D', relative.as_posix())
        parent_node = appdir if relative.parent == Path('.') else next(node for node in appdir.iter() if node.get('Id') == parent)
        ET.SubElement(parent_node, tag('Directory'), Id=directory_ids[relative], Name=relative.name)
    launcher_id = None
    for path in sorted(p for p in RELEASE.rglob('*') if p.is_file()):
        relative = path.relative_to(RELEASE)
        ident = stable_id('F', relative.as_posix())
        if relative.as_posix() == launcher_name: launcher_id = ident
        component = ET.SubElement(components, tag('Component'), Id=stable_id('C', relative.as_posix()), Directory=directory_ids[relative.parent],
                                  Guid=str(uuid.uuid5(uuid.UUID(upgrade_code.strip('{}')), relative.as_posix())))
        ET.SubElement(component, tag('File'), Id=ident, Source=str(path))
        ET.SubElement(component, tag('RegistryValue'), Root='HKCU', Key=registry + r'\Components',
                      Name=ident, Type='integer', Value='1', KeyPath='yes')
    shortcuts = ET.SubElement(components, tag('Component'), Id='ApplicationShortcuts', Guid=str(uuid.uuid5(uuid.UUID(upgrade_code.strip('{}')), 'shortcuts')))
    for directory, identifier in [('ProgramMenuFolder', 'StartMenuShortcut'), ('DesktopFolder', 'DesktopShortcut')]:
        ET.SubElement(shortcuts, tag('Shortcut'), Id=identifier, Directory=directory, Name=product_name,
                      Target=f'[#{launcher_id}]', WorkingDirectory='INSTALLFOLDER', Icon='JanviIcon', Description=f'Open {product_name}')
    ET.SubElement(shortcuts, tag('RegistryValue'), Root='HKCU', Key=registry, Name='Shortcuts', Type='integer', Value='1', KeyPath='yes')
    ET.SubElement(shortcuts, tag('RegistryValue'), Root='HKCU', Key=registry, Name='InstallFolder', Type='string', Value='[INSTALLFOLDER]')
    if args.desktop:
        ET.SubElement(shortcuts, tag('Environment'), Id='JanviUserPath', Name='PATH', Value='[INSTALLFOLDER]', Action='set', Part='last', System='no')
        for shell_key in (r'Software\Classes\Directory\shell\JanviImageStudio', r'Software\Classes\Directory\Background\shell\JanviImageStudio'):
            ET.SubElement(shortcuts, tag('RegistryValue'), Root='HKCU', Key=shell_key, Type='string', Value='Open with Janvi Image Studio')
            ET.SubElement(shortcuts, tag('RegistryValue'), Root='HKCU', Key=shell_key + r'\command', Type='string', Value=f'"[#{launcher_id}]" --folder "%V"')
    feature = ET.SubElement(package, tag('Feature'), Id='MainFeature', Title=product_name, Level='1')
    ET.SubElement(feature, tag('ComponentGroupRef'), Id='AppComponents')
    source = BUILD / 'Janvi.wxs'
    ET.ElementTree(wix).write(source, encoding='utf-8', xml_declaration=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(WIX), 'build', '-arch', 'x64', '-ext', 'WixToolset.UI.wixext', '-out', str(OUTPUT), '-pdb', str(BUILD / ('desktop.wixpdb' if args.desktop else 'portable.wixpdb')), str(source)], check=True, cwd=ROOT)
    checksum = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    OUTPUT.with_suffix('.msi.sha256').write_text(f'{checksum}  {OUTPUT.name}\n', encoding='ascii')
    print(f'Created {OUTPUT} SHA256 {checksum}')

if __name__ == '__main__': main()

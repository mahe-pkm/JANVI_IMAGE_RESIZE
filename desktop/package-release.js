const fs = require('node:fs');
const path = require('node:path');
const {packager} = require('@electron/packager');

async function main() {
  const root = path.resolve(__dirname, '..');
  const version = require('./package.json').version;
  const build = process.env.JANVI_BUILD_ROOT || path.join(root, '.build', `desktop-build-${version}`);
  const stage = path.join(build, 'source');
  if (fs.existsSync(stage)) throw new Error('Desktop staging directory already exists; preserve it and use a new release version.');
  fs.mkdirSync(stage, {recursive: true});
  for (const name of ['main.js', 'preload.js', 'janvi-app.ico']) fs.copyFileSync(path.join(__dirname, name), path.join(stage, name));
  fs.writeFileSync(path.join(stage, 'package.json'), JSON.stringify({name: 'janvi-image-studio', productName: 'Janvi Image Studio', version, main: 'main.js'}));
  const outputs = await packager({dir: stage, name: 'Janvi Image Studio', platform: 'win32', arch: 'x64',
    electronVersion: require('electron/package.json').version, out: path.join(build, 'package'),
    icon: path.join(__dirname, 'janvi-app.ico'), asar: true, prune: false, appVersion: version,
    win32metadata: {CompanyName: 'Janvi', FileDescription: 'Janvi Image Studio', ProductName: 'Janvi Image Studio'}});
  console.log(outputs[0]);
}
main().catch(error => { console.error(error); process.exitCode = 1; });

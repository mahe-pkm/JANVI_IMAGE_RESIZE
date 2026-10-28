use std::{env, fs, path::{Path, PathBuf}, process::Command};

fn main() {
    if env::var("CARGO_CFG_TARGET_OS").unwrap_or_default() != "windows" { return; }
    let manifest = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap());
    let icon = manifest.join("../assets/janvi-app.ico").canonicalize().expect("Janvi application icon missing");
    println!("cargo:rerun-if-changed={}", icon.display());
    let output = PathBuf::from(env::var_os("OUT_DIR").unwrap());
    let script = output.join("janvi-icon.rc");
    let resource = output.join("janvi-icon.res");
    fs::write(&script, format!("1 ICON \"{}\"\n", icon.display().to_string().replace('\\', "\\\\"))).expect("Cannot create resource script");
    let sdk_root = env::var_os("WindowsSdkDir").map(PathBuf::from).unwrap_or_else(|| {
        PathBuf::from(env::var_os("ProgramFiles(x86)").expect("Windows SDK directory unavailable")).join("Windows Kits/10")
    });
    let mut compilers: Vec<_> = fs::read_dir(sdk_root.join("bin")).expect("Windows SDK resource compiler is required")
        .filter_map(Result::ok).map(|entry| entry.path().join("x64/rc.exe")).filter(|path| Path::new(path).is_file()).collect();
    compilers.sort();
    let rc = compilers.last().expect("Windows SDK rc.exe is required");
    let result = Command::new(rc).arg("/nologo").arg(format!("/fo{}", resource.display())).arg(&script).status().expect("Cannot run resource compiler");
    assert!(result.success(), "Resource compilation failed");
    println!("cargo:rustc-link-arg={}", resource.display());
}

use std::{env, io, process::{Command, ExitCode}};

fn main() -> ExitCode {
    let outcome = (|| -> io::Result<bool> {
        let executable = env::current_exe()?;
        let root = executable.parent().ok_or_else(|| io::Error::other("Launcher directory missing"))?;
        println!("Janvi Image Resize — preparing the local dashboard...");
        let status = Command::new("powershell.exe")
            // Let Windows PowerShell build its own module path even when this
            // launcher is invoked from PowerShell 7 or a development terminal.
            .env_remove("PSModulePath")
            .args(["-NoProfile", "-ExecutionPolicy", "Bypass", "-File"])
            .arg(root.join("Start.ps1"))
            .args(env::args_os().skip(1))
            .current_dir(root)
            .status()?;
        Ok(status.success())
    })();
    match outcome {
        Ok(true) => ExitCode::SUCCESS,
        outcome => {
            eprintln!("Setup/start failed: {outcome:?}. Check the message above and data/server-error.log.");
            eprintln!("Press Enter to close.");
            let _ = io::stdin().read_line(&mut String::new());
            ExitCode::FAILURE
        }
    }
}

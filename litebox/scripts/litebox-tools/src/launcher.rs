use std::ffi::OsString;
use std::path::PathBuf;
use std::process::{Command, ExitCode};

struct Options {
    runner: PathBuf,
    initial_files: PathBuf,
    program: OsString,
    environment: Vec<OsString>,
    arguments: Vec<OsString>,
}

fn usage() -> &'static str {
    "Usage: litebox-launcher [--runner PATH] --initial-files ROOTFS.tar \
     [--env NAME=VALUE]... --program /linux/path [--] [ARG]..."
}

fn parse() -> Result<Options, String> {
    let own_exe = std::env::current_exe().map_err(|error| error.to_string())?;
    let mut runner = own_exe
        .parent()
        .unwrap_or_else(|| std::path::Path::new("."))
        .join("litebox-runner.exe");
    let mut initial_files = None;
    let mut program = None;
    let mut environment = Vec::new();
    let mut arguments = Vec::new();
    let mut input = std::env::args_os().skip(1);

    while let Some(argument) = input.next() {
        if argument == "--" {
            arguments.extend(input);
            break;
        }
        match argument.to_str() {
            Some("--runner") => {
                runner = PathBuf::from(input.next().ok_or("missing --runner value")?)
            }
            Some("--initial-files") => {
                initial_files = Some(PathBuf::from(
                    input.next().ok_or("missing --initial-files value")?,
                ));
            }
            Some("--program") => program = Some(input.next().ok_or("missing --program value")?),
            Some("--env") => environment.push(input.next().ok_or("missing --env value")?),
            Some(flag) if flag.starts_with('-') => return Err(format!("unknown option: {flag}")),
            _ => arguments.push(argument),
        }
    }
    let initial_files = initial_files.ok_or("--initial-files is required")?;
    let program = program.ok_or("--program is required")?;
    if !runner.is_file() {
        return Err(format!("runner not found: {}", runner.display()));
    }
    if !initial_files.is_file() {
        return Err(format!("TAR not found: {}", initial_files.display()));
    }
    Ok(Options {
        runner,
        initial_files,
        program,
        environment,
        arguments,
    })
}

fn main() -> ExitCode {
    if std::env::args_os()
        .skip(1)
        .any(|arg| arg == "-h" || arg == "--help")
    {
        println!("{}", usage());
        return ExitCode::SUCCESS;
    }
    let result = parse().and_then(|options| {
        let mut command = Command::new(options.runner);
        command.arg("--initial-files").arg(options.initial_files);
        for item in options.environment {
            command.arg("--env").arg(item);
        }
        command.arg(options.program).args(options.arguments);
        command.status().map_err(|error| error.to_string())
    });
    match result {
        Ok(status) if status.success() => ExitCode::SUCCESS,
        Ok(_) => ExitCode::FAILURE,
        Err(message) => {
            eprintln!("{message}\n{}", usage());
            ExitCode::FAILURE
        }
    }
}

use std::fs::{self, File};
use std::io;
use std::path::{Component, Path, PathBuf};
use std::process::ExitCode;
use tar::{Archive, Builder, EntryType, Header};
use walkdir::WalkDir;

struct Options {
    input: PathBuf,
    output: PathBuf,
    host: PathBuf,
    target: PathBuf,
}

fn usage() -> &'static str {
    "Usage: litebox-tar-sync --input ROOTFS.tar --output SYNCED.tar \
     --host WINDOWS_DIR --target workspace/project"
}

fn safe_tar_path(value: &Path) -> Result<PathBuf, String> {
    let mut clean = PathBuf::new();
    for component in value.components() {
        match component {
            Component::Normal(part) => clean.push(part),
            Component::RootDir | Component::CurDir => {}
            _ => return Err(format!("unsafe TAR path: {}", value.display())),
        }
    }
    Ok(clean)
}

fn parse() -> Result<Options, String> {
    let mut input = None;
    let mut output = None;
    let mut host = None;
    let mut target = None;
    let mut args = std::env::args_os().skip(1);
    while let Some(arg) = args.next() {
        match arg.to_str() {
            Some("--input") => input = args.next().map(PathBuf::from),
            Some("--output") => output = args.next().map(PathBuf::from),
            Some("--host") => host = args.next().map(PathBuf::from),
            Some("--target") => target = args.next().map(PathBuf::from),
            Some(flag) => return Err(format!("unknown option: {flag}")),
            None => return Err("arguments must be valid Unicode".into()),
        }
    }
    let input = input.ok_or("--input is required")?;
    let output = output.ok_or("--output is required")?;
    let host = host.ok_or("--host is required")?;
    let target = safe_tar_path(&target.ok_or("--target is required")?)?;
    if target.as_os_str().is_empty() {
        return Err("empty TAR target".into());
    }
    if !input.is_file() {
        return Err(format!("input TAR not found: {}", input.display()));
    }
    if !host.is_dir() {
        return Err(format!("host directory not found: {}", host.display()));
    }
    if input == output {
        return Err("--output must differ from --input".into());
    }
    if output.exists() {
        return Err(format!("output already exists: {}", output.display()));
    }
    Ok(Options {
        input,
        output,
        host,
        target,
    })
}

fn append_file(builder: &mut Builder<File>, source: &Path, path: &Path) -> io::Result<()> {
    let metadata = fs::symlink_metadata(source)?;
    if metadata.file_type().is_symlink() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            format!("host symlink rejected: {}", source.display()),
        ));
    }
    let mut header = Header::new_ustar();
    header.set_uid(1000);
    header.set_gid(1000);
    header.set_mtime(0);
    if metadata.is_dir() {
        header.set_entry_type(EntryType::Directory);
        header.set_mode(0o755);
        header.set_size(0);
        header.set_cksum();
        builder.append_data(&mut header, path, io::empty())
    } else {
        header.set_entry_type(EntryType::Regular);
        header.set_mode(0o644);
        header.set_size(metadata.len());
        header.set_cksum();
        builder.append_data(&mut header, path, File::open(source)?)
    }
}

fn run(options: Options) -> Result<(), Box<dyn std::error::Error>> {
    let output_parent = options.output.parent().unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(output_parent)?;
    let temporary_path = options
        .output
        .with_extension(format!("tmp-{}", std::process::id()));
    if temporary_path.exists() {
        return Err(format!(
            "temporary output already exists: {}",
            temporary_path.display()
        )
        .into());
    }
    let output_file = File::create(&temporary_path)?;
    let mut builder = Builder::new(output_file);

    for entry in Archive::new(File::open(&options.input)?).entries()? {
        let mut entry = entry?;
        let entry_type = entry.header().entry_type();
        if entry_type.is_symlink() || entry_type.is_hard_link() {
            return Err(format!("link entry rejected: {}", entry.path()?.display()).into());
        }
        let path = safe_tar_path(entry.path()?.as_ref())?;
        if path.as_os_str().is_empty() {
            continue;
        }
        if path != options.target && !path.starts_with(&options.target) {
            let mut header = entry.header().clone();
            builder.append_data(&mut header, path, &mut entry)?;
        }
    }
    append_file(&mut builder, &options.host, &options.target)?;
    for entry in WalkDir::new(&options.host).min_depth(1).sort_by_file_name() {
        let entry = entry?;
        let relative = entry.path().strip_prefix(&options.host)?;
        append_file(&mut builder, entry.path(), &options.target.join(relative))?;
    }
    builder.finish()?;
    drop(builder);
    fs::rename(temporary_path, &options.output)?;
    println!("created {}", options.output.display());
    Ok(())
}

fn main() -> ExitCode {
    if std::env::args_os()
        .skip(1)
        .any(|arg| arg == "-h" || arg == "--help")
    {
        println!("{}", usage());
        return ExitCode::SUCCESS;
    }
    match parse().and_then(|options| run(options).map_err(|error| error.to_string())) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("{message}\n{}", usage());
            ExitCode::FAILURE
        }
    }
}

pub mod bing;
pub mod pexel;
mod resolution;
pub mod wallhaven;
mod zone;

use crate::wp_selector::WallPaper;
use anyhow::{bail, Context, Result};
use reqwest::blocking::{Client, RequestBuilder, Response};
use reqwest::StatusCode;
use std::fs;
use std::io::ErrorKind;
use std::io::{self, Read};
use std::path::{Path, PathBuf};
use std::thread;
use std::time::Duration;
use tempfile::NamedTempFile;

/// Provider-side orientation preference; not pixel decoding (Issue #53).
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Orientation {
    Landscape,
    Portrait,
}

impl std::str::FromStr for Orientation {
    type Err = anyhow::Error;

    fn from_str(value: &str) -> Result<Self> {
        match value {
            "landscape" => Ok(Self::Landscape),
            "portrait" => Ok(Self::Portrait),
            _ => bail!("unsupported orientation: {} (landscape or portrait)", value),
        }
    }
}

impl Orientation {
    fn as_pexels(self) -> &'static str {
        match self {
            Self::Landscape => "landscape",
            Self::Portrait => "portrait",
        }
    }

    fn as_wallhaven_ratio(self) -> &'static str {
        match self {
            Self::Landscape => "16x9",
            Self::Portrait => "9x16",
        }
    }
}

pub trait GetImgUrl {
    fn get_img(&self, nums: u32) -> Result<Vec<WallPaper>>;
}

/// Shared bounded client for remote provider metadata and assets.
fn http_client() -> Result<Client> {
    Ok(Client::builder()
        .connect_timeout(Duration::from_secs(5))
        .timeout(Duration::from_secs(30))
        .build()?)
}

/// Retry only bounded transient failures. Keep authorization headers out of logs.
fn request_with_retry(request: RequestBuilder) -> Result<Response> {
    for attempt in 0..3 {
        let call = request
            .try_clone()
            .ok_or_else(|| anyhow::anyhow!("provider request cannot be retried"))?;
        match call.send() {
            Ok(response)
                if response.status() == StatusCode::TOO_MANY_REQUESTS
                    || response.status().is_server_error() =>
            {
                if attempt == 2 {
                    return Ok(response.error_for_status()?);
                }
            }
            Ok(response) => return Ok(response.error_for_status()?),
            Err(err) if err.is_connect() || err.is_timeout() => {
                if attempt == 2 {
                    return Err(err.into());
                }
            }
            Err(err) => return Err(err.into()),
        }
        thread::sleep(Duration::from_millis(100 * (1 << attempt)));
    }
    unreachable!("bounded retry loop always returns")
}

/// Assert a provider-supplied URL stays on its documented image CDN.
fn checked_image_url(raw: &str, allowed_hosts: &[&str]) -> Result<url::Url> {
    let url = url::Url::parse(raw)?;
    if url.scheme() != "https"
        || !allowed_hosts
            .iter()
            .any(|host| url.host_str() == Some(host))
        || !url.username().is_empty()
        || url.password().is_some()
    {
        bail!("provider supplied an unsupported image URL");
    }
    Ok(url)
}

/// Join one untrusted URL-provided *filename*, never an upstream relative path.
///
/// This is validation, not a sandbox: a hostile concurrent process can still
/// race between the symlink check and a later File::create. Atomic replacement
/// and race-free directory handles are a separately scoped storage decision.
fn safe_download_path(dir: &str, name: &str) -> Result<PathBuf> {
    let invalid = name.is_empty()
        || matches!(name, "." | "..")
        || name.trim() != name
        || name.ends_with('.')
        || name.chars().any(|ch| {
            ch.is_control() || matches!(ch, '/' | '\\' | ':' | '<' | '>' | '|' | '?' | '*' | '"')
        });
    if invalid {
        bail!(
            "provider returned an invalid wallpaper filename: {:?}",
            name
        );
    }

    // Windows device names are reserved even with extensions. Check on all
    // hosts so Linux CI protects output consumed by Windows CLI users.
    let stem = name
        .split('.')
        .next()
        .unwrap_or_default()
        .to_ascii_uppercase();
    if matches!(
        stem.as_str(),
        "CON"
            | "PRN"
            | "AUX"
            | "NUL"
            | "COM1"
            | "COM2"
            | "COM3"
            | "COM4"
            | "COM5"
            | "COM6"
            | "COM7"
            | "COM8"
            | "COM9"
            | "LPT1"
            | "LPT2"
            | "LPT3"
            | "LPT4"
            | "LPT5"
            | "LPT6"
            | "LPT7"
            | "LPT8"
            | "LPT9"
    ) {
        bail!(
            "provider returned a reserved wallpaper filename: {:?}",
            name
        );
    }

    let dest = Path::new(dir).join(name);
    match fs::symlink_metadata(&dest) {
        Ok(meta) if meta.file_type().is_symlink() => {
            bail!("refusing to overwrite a symbolic-link wallpaper destination");
        }
        Ok(meta) if !meta.is_file() => {
            bail!("wallpaper download destination is not a regular file");
        }
        Ok(_) => {}
        Err(err) if err.kind() == ErrorKind::NotFound => {}
        Err(err) => {
            return Err(err)
                .with_context(|| format!("cannot inspect download target: {}", dest.display()));
        }
    }
    Ok(dest)
}

/// Publish only a complete stream; unsuccessful copies never expose partial
/// data at the wallpaper path. The temporary file is securely created on the
/// same filesystem and removed automatically on failure.
///
/// This replaces the pathname (and thus its inode/metadata/hardlink identity)
/// on success rather than modifying the old file in place. This does not
/// guarantee power-loss durability or stop concurrent changes to parent paths.
fn write_complete_download<R: Read>(destination: &Path, mut source: R) -> Result<()> {
    let directory = destination
        .parent()
        .ok_or_else(|| anyhow::anyhow!("download destination has no parent"))?;
    let name = destination
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| anyhow::anyhow!("download filename is not UTF-8"))?;
    let dir = directory
        .to_str()
        .ok_or_else(|| anyhow::anyhow!("download directory is not UTF-8"))?;

    safe_download_path(dir, name)?;
    let mut stage = NamedTempFile::new_in(directory)
        .with_context(|| format!("cannot stage wallpaper in {}", directory.display()))?;
    let copied = io::copy(&mut source, stage.as_file_mut())
        .context("wallpaper stream failed before the file was complete")?;
    if copied == 0 {
        bail!("wallpaper download was empty");
    }
    // Re-check in case the destination was altered during the stream. The
    // subsequent rename still has a TOCTOU window, not a sandbox guarantee.
    safe_download_path(dir, name)?;
    stage
        .persist(destination)
        .with_context(|| format!("cannot publish wallpaper at {}", destination.display()))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn retries_bounded_429_and_rejects_untrusted_image_origins() {
        use std::io::{Read, Write};
        use std::net::TcpListener;
        use std::thread;

        let listener = TcpListener::bind("127.0.0.1:0").expect("local fixture server");
        let address = listener.local_addr().expect("local address");
        let server = thread::spawn(move || {
            for code in [429, 503, 200] {
                let (mut socket, _) = listener.accept().expect("test connection");
                let mut request = [0u8; 2048];
                let bytes = socket.read(&mut request).expect("read request");
                assert!(bytes > 0);
                let answer = format!(
                    "HTTP/1.1 {} Test\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok",
                    code
                );
                socket.write_all(answer.as_bytes()).expect("fixture reply");
            }
        });

        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(3))
            .build()
            .expect("fixture client");
        let result = request_with_retry(client.get(format!("http://{}/retry", address)))
            .expect("third attempt succeeds")
            .text()
            .expect("response body");
        assert_eq!(result, "ok");
        server.join().expect("fixture server ended");

        assert!(checked_image_url(
            "https://images.pexels.com/photos/1/photo.jpeg",
            &["images.pexels.com"]
        )
        .is_ok());
        for url in [
            "http://images.pexels.com/photo.jpg",
            "file:///etc/passwd",
            "https://evil.example/photo.jpg",
            "https://user:pass@images.pexels.com/photo.jpg",
        ] {
            assert!(checked_image_url(url, &["images.pexels.com"]).is_err());
        }
    }

    #[test]
    fn staging_replaces_existing_file_after_complete_stream() {
        let temp = tempfile::tempdir().expect("isolated target folder");
        let dest = temp.path().join("wallpaper.png");
        fs::write(&dest, b"old-good-file").expect("initial wallpaper");
        write_complete_download(&dest, &b"new-good-file"[..]).expect("publish full image");
        assert_eq!(fs::read(&dest).expect("published image"), b"new-good-file");
        assert_eq!(
            fs::read_dir(temp.path())
                .expect("directory entries")
                .count(),
            1
        );
    }

    #[test]
    fn staging_creates_new_file_only_after_successful_copy() {
        let temp = tempfile::tempdir().expect("isolated target folder");
        let dest = temp.path().join("new.jpg");
        assert!(!dest.exists());
        write_complete_download(&dest, &b"data"[..]).expect("full copy");
        assert_eq!(fs::read(&dest).expect("published file"), b"data");
    }

    struct InterruptedStream {
        sent: bool,
    }

    impl Read for InterruptedStream {
        fn read(&mut self, output: &mut [u8]) -> io::Result<usize> {
            if self.sent {
                return Err(io::Error::new(
                    io::ErrorKind::ConnectionReset,
                    "connection lost",
                ));
            }
            self.sent = true;
            output[0] = b'x';
            Ok(1)
        }
    }

    #[test]
    fn interrupted_stream_keeps_existing_file_and_removes_staging_file() {
        let temp = tempfile::tempdir().expect("isolated target folder");
        let dest = temp.path().join("existing.jpg");
        fs::write(&dest, b"keep-original").expect("original wallpaper");
        let result = write_complete_download(&dest, InterruptedStream { sent: false });
        assert!(result.is_err());
        assert_eq!(fs::read(&dest).expect("original file"), b"keep-original");
        assert_eq!(
            fs::read_dir(temp.path())
                .expect("directory entries")
                .count(),
            1
        );
    }

    #[test]
    fn interrupted_stream_does_not_create_new_wallpaper() {
        let temp = tempfile::tempdir().expect("isolated target folder");
        let dest = temp.path().join("missing.jpg");
        assert!(write_complete_download(&dest, InterruptedStream { sent: false }).is_err());
        assert!(!dest.exists());
        assert_eq!(
            fs::read_dir(temp.path())
                .expect("directory entries")
                .count(),
            0
        );
    }

    #[test]
    fn empty_stream_preserves_existing_wallpaper() {
        let temp = tempfile::tempdir().expect("isolated target folder");
        let dest = temp.path().join("wallpaper.jpg");
        fs::write(&dest, b"old").expect("original wallpaper");
        assert!(write_complete_download(&dest, &b""[..]).is_err());
        assert_eq!(fs::read(&dest).expect("existing image"), b"old");
        assert_eq!(
            fs::read_dir(temp.path())
                .expect("directory entries")
                .count(),
            1
        );
    }

    #[cfg(unix)]
    #[test]
    fn staging_rejects_symlink_destination_without_modifying_target() {
        use std::os::unix::fs::symlink;
        let temp = tempfile::tempdir().expect("isolated target folder");
        let dest = temp.path().join("alias.jpg");
        let original = temp.path().join("real.jpg");
        fs::write(&original, b"existing").expect("original image");
        symlink(&original, &dest).expect("symlink fixture");
        assert!(write_complete_download(&dest, &b"new"[..]).is_err());
        assert_eq!(
            fs::read(&original).expect("original unchanged"),
            b"existing"
        );
    }

    #[test]
    fn url_filenames_are_single_portable_components() {
        for name in [
            "OHR.Spring_EN-US123",
            "photo.jpeg",
            "image 2026.png",
            "a_b-c.webp",
        ] {
            let path = safe_download_path(".", name).expect("ordinary filenames remain valid");
            assert_eq!(path.file_name().and_then(|p| p.to_str()), Some(name));
        }
        for name in [
            "",
            ".",
            "..",
            "../escape",
            "/tmp/escape",
            "folder/file.jpg",
            "folder\\file.jpg",
            "C:\\escape.jpg",
            "evil:ads.jpg",
            "CON",
            "NUL.jpg",
            "LPT9.png",
            "photo?",
            "trailing.",
            " space.jpg",
            "space.jpg ",
            "newline\nfile.jpg",
        ] {
            assert!(
                safe_download_path(".", name).is_err(),
                "accepted unsafe name: {:?}",
                name
            );
        }
    }

    #[cfg(unix)]
    #[test]
    fn existing_symlink_output_is_rejected() {
        use std::os::unix::fs::symlink;
        use std::sync::atomic::{AtomicU64, Ordering};
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let dir = std::env::temp_dir().join(format!(
            "ezwallpaper-download-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&dir).expect("test directory");
        let target = dir.join("existing.jpg");
        fs::write(&target, b"do not truncate").expect("test target");
        symlink(&target, dir.join("linked.jpg")).expect("symlink fixture");
        assert!(safe_download_path(dir.to_str().expect("UTF-8 temp"), "linked.jpg").is_err());
        assert_eq!(fs::read(target).expect("original data"), b"do not truncate");
        fs::remove_dir_all(dir).expect("cleanup");
    }
}

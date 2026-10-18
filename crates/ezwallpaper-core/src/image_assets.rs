//! Explicit headless image validation and non-destructive output derivation.
//! This module does not change legacy filename-based catalog/manifest v1.
use crate::WallpaperManager;
use anyhow::{anyhow, bail, Context, Result};
use image::imageops::{overlay, FilterType};
use image::metadata::Orientation;
use image::{DynamicImage, ImageDecoder, ImageFormat, ImageReader, Limits};
use serde::Serialize;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use tempfile::NamedTempFile;

const MAX_FILE_BYTES: u64 = 64 * 1024 * 1024;
const MAX_INPUT_PIXELS: u64 = 32_000_000;
const MAX_INPUT_EDGE: u32 = 16_384;
const MAX_OUTPUT_EDGE: u32 = 8_192;
const MAX_OUTPUT_PIXELS: u64 = 16_000_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FitMode {
    Cover,
    Contain,
}

impl std::str::FromStr for FitMode {
    type Err = anyhow::Error;

    fn from_str(value: &str) -> Result<Self> {
        match value {
            "cover" => Ok(Self::Cover),
            "contain" => Ok(Self::Contain),
            _ => bail!("fit must be cover or contain"),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DerivedFormat {
    Png,
    Jpeg,
}

impl std::str::FromStr for DerivedFormat {
    type Err = anyhow::Error;

    fn from_str(value: &str) -> Result<Self> {
        match value {
            "png" => Ok(Self::Png),
            "jpeg" | "jpg" => Ok(Self::Jpeg),
            _ => bail!("output format must be png or jpeg"),
        }
    }
}

impl DerivedFormat {
    fn image_format(self) -> ImageFormat {
        match self {
            Self::Png => ImageFormat::Png,
            Self::Jpeg => ImageFormat::Jpeg,
        }
    }

    fn name(self) -> &'static str {
        match self {
            Self::Png => "png",
            Self::Jpeg => "jpeg",
        }
    }
}

#[derive(Debug, Serialize)]
pub struct ImageProbe {
    pub schema_version: u32,
    pub path: PathBuf,
    pub content_id: String,
    pub size_bytes: u64,
    pub format: &'static str,
    pub mime_type: &'static str,
    pub raw_width: u32,
    pub raw_height: u32,
    pub width: u32,
    pub height: u32,
    pub orientation: String,
}

#[derive(Debug, Serialize)]
pub struct DerivedImage {
    pub schema_version: u32,
    pub path: PathBuf,
    pub source_content_id: String,
    pub content_id: String,
    pub width: u32,
    pub height: u32,
    pub format: &'static str,
    pub fit: &'static str,
}

struct Decoded {
    image: DynamicImage,
    format: ImageFormat,
    orientation: Orientation,
    raw_width: u32,
    raw_height: u32,
}

fn recognized_format(format: ImageFormat) -> Result<(&'static str, &'static str)> {
    match format {
        ImageFormat::Png => Ok(("png", "image/png")),
        ImageFormat::Jpeg => Ok(("jpeg", "image/jpeg")),
        ImageFormat::WebP => Ok(("webp", "image/webp")),
        ImageFormat::Bmp => Ok(("bmp", "image/bmp")),
        _ => bail!("only PNG, JPEG, WebP and BMP static images are supported"),
    }
}

fn check_input_geometry(width: u32, height: u32) -> Result<()> {
    if width == 0
        || height == 0
        || width > MAX_INPUT_EDGE
        || height > MAX_INPUT_EDGE
        || u64::from(width) * u64::from(height) > MAX_INPUT_PIXELS
    {
        bail!("image dimensions exceed safe input geometry limits");
    }
    Ok(())
}

fn check_output_geometry(width: u32, height: u32) -> Result<()> {
    if width == 0
        || height == 0
        || width > MAX_OUTPUT_EDGE
        || height > MAX_OUTPUT_EDGE
        || u64::from(width) * u64::from(height) > MAX_OUTPUT_PIXELS
    {
        bail!("requested output dimensions exceed safe geometry limits");
    }
    Ok(())
}

/// Read actual bytes, not filename extensions, with an explicit decode bound.
fn decode_limited(path: &Path) -> Result<Decoded> {
    let metadata = fs::metadata(path).with_context(|| "cannot stat image for decoding")?;
    if !metadata.is_file() || metadata.len() > MAX_FILE_BYTES {
        bail!("image must be a regular file no larger than 64 MiB");
    }
    let reader = ImageReader::open(path)?
        .with_guessed_format()
        .context("cannot identify image file header")?;
    let format = reader
        .format()
        .ok_or_else(|| anyhow!("unrecognized image format"))?;
    recognized_format(format)?;
    let mut decoder = reader.into_decoder().context("invalid image decoder")?;
    let (raw_width, raw_height) = decoder.dimensions();
    check_input_geometry(raw_width, raw_height)?;
    let orientation = decoder
        .orientation()
        .context("invalid image orientation metadata")?;
    let mut limits = Limits::default();
    limits.max_image_width = Some(MAX_INPUT_EDGE);
    limits.max_image_height = Some(MAX_INPUT_EDGE);
    // image-rs documents max_alloc as a best-effort bound; independent dimensions
    // and pixel-count checks above remain mandatory.
    limits.max_alloc = Some(256 * 1024 * 1024);
    decoder.set_limits(limits)?;
    let mut image =
        DynamicImage::from_decoder(decoder).context("image bytes failed complete decoding")?;
    image.apply_orientation(orientation);
    Ok(Decoded {
        image,
        format,
        orientation,
        raw_width,
        raw_height,
    })
}

/// Validate the image completely and return versioned metadata without mutation.
pub fn probe_image(path: &Path) -> Result<ImageProbe> {
    let manager = WallpaperManager;
    let asset = manager.open_local(path)?;
    let decoded = decode_limited(asset.path())?;
    let (format, mime_type) = recognized_format(decoded.format)?;
    Ok(ImageProbe {
        schema_version: 1,
        path: asset.path().to_owned(),
        content_id: manager.content_id(&asset)?,
        size_bytes: asset.size_bytes(),
        format,
        mime_type,
        raw_width: decoded.raw_width,
        raw_height: decoded.raw_height,
        width: decoded.image.width(),
        height: decoded.image.height(),
        orientation: format!("{:?}", decoded.orientation),
    })
}

/// Export a new PNG/JPEG at physical pixel dimensions; refuse to overwrite.
pub fn derive_image(
    source: &Path,
    destination: &Path,
    width: u32,
    height: u32,
    fit: FitMode,
    format: DerivedFormat,
) -> Result<DerivedImage> {
    check_output_geometry(width, height)?;
    let manager = WallpaperManager;
    let source_asset = manager.open_local(source)?;
    let decoded = decode_limited(source_asset.path())?;
    let source_content_id = manager.content_id(&source_asset)?;

    let converted = match fit {
        FitMode::Cover => decoded
            .image
            .resize_to_fill(width, height, FilterType::Lanczos3),
        FitMode::Contain => {
            let scaled = decoded.image.resize(width, height, FilterType::Lanczos3);
            let mut canvas = DynamicImage::new_rgba8(width, height);
            let x = (width - scaled.width()) / 2;
            let y = (height - scaled.height()) / 2;
            overlay(&mut canvas, &scaled, i64::from(x), i64::from(y));
            canvas
        }
    };
    let parent = destination
        .parent()
        .ok_or_else(|| anyhow!("output has no parent folder"))?;
    if !parent.is_dir() {
        bail!("output parent is not an existing directory");
    }
    let mut staged = NamedTempFile::new_in(parent)?;
    let output_image = if format == DerivedFormat::Jpeg {
        DynamicImage::ImageRgb8(converted.to_rgb8())
    } else {
        converted
    };
    output_image.write_to(staged.as_file_mut(), format.image_format())?;
    staged.as_file_mut().flush()?;
    // persist_noclobber uses an atomic no-overwrite publish on supported FSs.
    // An existing source/output/symlink pathname is never intentionally replaced.
    staged.persist_noclobber(destination).with_context(|| {
        format!(
            "output exists or cannot be created: {}",
            destination.display()
        )
    })?;
    let derived_asset = manager.open_local(destination)?;
    Ok(DerivedImage {
        schema_version: 1,
        path: derived_asset.path().to_owned(),
        source_content_id,
        content_id: manager.content_id(&derived_asset)?,
        width,
        height,
        format: format.name(),
        fit: match fit {
            FitMode::Cover => "cover",
            FitMode::Contain => "contain",
        },
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use image::{ImageBuffer, Rgba};

    fn fixture(path: &Path, width: u32, height: u32) {
        let mut pixels = ImageBuffer::from_pixel(width, height, Rgba([245u8, 5, 5, 255]));
        for y in 0..height {
            for x in width / 2..width {
                pixels.put_pixel(x, y, Rgba([5, 5, 245, 255]));
            }
        }
        pixels.save(path).expect("fixture saved");
    }

    #[test]
    fn probes_decoded_png_not_extension_and_rejects_invalid_bytes() {
        let dir = tempfile::tempdir().expect("sandbox");
        let png = dir.path().join("valid.png");
        fixture(&png, 8, 4);
        let probe = probe_image(&png).expect("decoded fixture");
        assert_eq!((probe.raw_width, probe.raw_height), (8, 4));
        assert_eq!((probe.width, probe.height), (8, 4));
        assert_eq!(probe.format, "png");
        assert_eq!(probe.mime_type, "image/png");
        assert!(probe.content_id.starts_with("sha256:"));
        assert_eq!(probe.orientation, "NoTransforms");
        assert_eq!(probe.schema_version, 1);

        let bogus = dir.path().join("not-an-image.png");
        fs::write(&bogus, b"this is not image bytes").expect("fixture");
        assert!(probe_image(&bogus).is_err());
        assert!(probe_image(&dir.path().join("missing.jpg")).is_err());
    }

    #[test]
    fn cover_and_contain_preserve_original_and_output_geometry() {
        let dir = tempfile::tempdir().expect("sandbox");
        let input = dir.path().join("source.png");
        fixture(&input, 16, 8);
        let original = fs::read(&input).expect("source");
        let cover = dir.path().join("portrait.png");
        let result = derive_image(&input, &cover, 6, 12, FitMode::Cover, DerivedFormat::Png)
            .expect("cover image");
        assert_eq!((result.width, result.height), (6, 12));
        assert_eq!(image::open(&cover).expect("decode cover").width(), 6);
        assert_eq!(image::open(&cover).expect("decode cover").height(), 12);
        assert_eq!(result.fit, "cover");
        assert!(derive_image(&input, &cover, 6, 12, FitMode::Cover, DerivedFormat::Png).is_err());
        assert_eq!(fs::read(&input).expect("unchanged source"), original);

        let contain = dir.path().join("landscape.jpg");
        let info = derive_image(
            &input,
            &contain,
            12,
            12,
            FitMode::Contain,
            DerivedFormat::Jpeg,
        )
        .expect("contain JPEG");
        assert_eq!(info.format, "jpeg");
        let image = image::open(&contain).expect("JPEG");
        assert_eq!((image.width(), image.height()), (12, 12));
    }

    #[test]
    fn rejects_output_overflow_and_fake_destination() {
        assert!(check_input_geometry(30_000, 1).is_err());
        assert!(check_input_geometry(8_192, 8_192).is_err());
        assert!(check_output_geometry(0, 100).is_err());
        assert!(check_output_geometry(9_000, 100).is_err());
        assert!(check_output_geometry(4_096, 4_096).is_err());
        assert!(check_output_geometry(3_840, 2_160).is_ok());
        let dir = tempfile::tempdir().expect("sandbox");
        let input = dir.path().join("source.png");
        fixture(&input, 8, 4);
        assert!(derive_image(
            &input,
            &dir.path().join("absent/image.png"),
            2,
            2,
            FitMode::Contain,
            DerivedFormat::Png
        )
        .is_err());
    }
}

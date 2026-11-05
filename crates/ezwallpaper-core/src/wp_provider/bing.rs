use super::resolution::Resolution;
use super::zone::Zone;
use super::{checked_image_url, http_client, request_with_retry, GetImgUrl};
use crate::wp_selector::{WallPaper, WpType};
use anyhow::{anyhow, bail, Result};
use log::debug;
use serde::Deserialize;
use std::collections::BTreeSet;
use std::str::FromStr;
use url::Url;

/// Recent Bing homepage feed: idx 0..7, at most eight available daily images.
#[derive(Debug, Default)]
pub struct BingProvider {
    zone: Zone,
    resolution: Resolution,
    time_offset: i32,
    dir: String,
    max_download_bytes: u64,
}

impl BingProvider {
    pub fn new() -> Self {
        BingProvider {
            zone: Zone::Cn,
            resolution: Resolution::R1920x1200,
            time_offset: 0,
            dir: ".".to_string(),
            max_download_bytes: super::DEFAULT_DOWNLOAD_LIMIT,
        }
    }

    pub fn with_zone(mut self, zone: &str) -> Result<Self> {
        self.zone = Zone::from_str(zone)?;
        Ok(self)
    }

    pub fn with_resolution(mut self, resolution: &str) -> Result<Self> {
        self.resolution = Resolution::from_str(resolution)?;
        Ok(self)
    }

    pub fn with_time_offset(mut self, time_offset: i32) -> Self {
        self.time_offset = time_offset;
        self
    }

    pub fn with_dir(mut self, path: &str) -> Self {
        self.dir = path.to_owned();
        self
    }

    pub fn with_max_download_bytes(mut self, bytes: u64) -> Result<Self> {
        self.max_download_bytes = super::checked_download_limit(bytes)?;
        Ok(self)
    }

    fn archive_url(&self, count: u32) -> Result<Url> {
        if !(1..=8).contains(&count)
            || !(0..=7).contains(&self.time_offset)
            || self.time_offset as u32 + count > 8
        {
            bail!("Bing recent archive supports 1..8 items within idx 0..7; count plus idx must not exceed 8");
        }
        let mut url = Url::parse("https://www.bing.com/HPImageArchive.aspx")?;
        url.query_pairs_mut()
            .append_pair("format", "js")
            .append_pair("idx", &self.time_offset.to_string())
            .append_pair("n", &count.to_string())
            .append_pair("mkt", &self.zone.to_string());
        Ok(url)
    }

    fn image_urls(&self, body: &str) -> Result<Vec<Url>> {
        let response: Images = serde_json::from_str(body)?;
        if response.images.len() > 8 {
            bail!("Bing archive returned more than eight image entries");
        }
        let mut filenames = BTreeSet::new();
        let mut urls = Vec::with_capacity(response.images.len());
        for image in &response.images {
            if !image.urlbase.starts_with("/th?id=") {
                bail!("Bing returned unexpected image base path");
            }
            // Parse BEFORE appending the requested resolution: an untrusted
            // fragment or additional parameter can otherwise swallow the
            // suffix and change the local filename/remote request.
            let base = Url::parse(&format!("https://www.bing.com{}", image.urlbase))?;
            let mut parameters = base.query_pairs();
            let id = parameters.next();
            if base.path() != "/th"
                || base.fragment().is_some()
                || id.as_ref().is_none_or(|(key, value)| key != "id" || value.is_empty())
                || parameters.next().is_some()
            {
                bail!("Bing image base must contain one id query parameter");
            }
            let url = checked_image_url(
                &format!(
                    "https://www.bing.com{}_{}.jpg",
                    image.urlbase, self.resolution
                ),
                &["www.bing.com"],
            )?;
            // Match the same decoded filename used by download_image. Validate
            // ALL names before the first image transfer, including Windows
            // aliases and reserved path components.
            let filename = url
                .query_pairs()
                .find(|(key, _)| key == "id")
                .map(|(_, value)| value.into_owned())
                .ok_or_else(|| anyhow!("Bing image URL has no id filename"))?;
            super::safe_download_path(&self.dir, &filename)?;
            if !filenames.insert(filename.to_ascii_lowercase()) {
                bail!("Bing archive contains colliding image filenames");
            }
            urls.push(url);
        }
        Ok(urls)
    }
}

impl GetImgUrl for BingProvider {
    fn get_img(&self, nums: u32) -> Result<Vec<WallPaper>> {
        let archive = self.archive_url(nums)?;
        let client = http_client()?;
        let body = super::read_metadata_response(request_with_retry(client.get(archive))?)?;
        let urls = self.image_urls(&body)?;
        if urls.len() > nums as usize {
            bail!("Bing returned more images than requested");
        }
        urls.iter()
            .map(|url| {
                let path = download_image(&client, url, &self.dir, self.max_download_bytes)?;
                Ok(WallPaper::new()
                    .with_type(WpType::FromLocal)
                    .with_path(path))
            })
            .collect()
    }
}

fn download_image(
    client: &reqwest::blocking::Client,
    url: &Url,
    dir: &str,
    max_bytes: u64,
) -> Result<String> {
    let file_name = url
        .query_pairs()
        .find(|(key, _)| key == "id")
        .map(|(_, value)| value.into_owned())
        .ok_or_else(|| anyhow!("Bing image URL has no id filename"))?;
    let file_path = super::safe_download_path(dir, &file_name)?;
    let mut response = request_with_retry(client.get(url.clone()))?;
    super::reject_excess_content_length(response.content_length(), max_bytes)?;
    debug!("downloading Bing image to {:?}", file_path);
    let transferred =
        super::write_complete_download_with_limit(&file_path, &mut response, max_bytes)?;
    debug!("staged {} Bing image bytes", transferred);
    Ok(file_path
        .to_str()
        .ok_or_else(|| anyhow!("download output path is not UTF-8"))?
        .to_owned())
}

#[derive(Debug, Deserialize)]
struct Images {
    images: Vec<Image>,
}

#[derive(Debug, Deserialize)]
struct Image {
    urlbase: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn recent_archive_is_bounded_and_parameterized() {
        let base = BingProvider::new().with_zone("en-US").expect("locale");
        let url = base.archive_url(8).expect("8 images");
        assert!(url.as_str().contains("n=8"));
        assert!(url.as_str().contains("mkt=en-US"));
        let older = BingProvider::new().with_time_offset(4);
        assert!(older.archive_url(4).is_ok());
        assert!(older.archive_url(5).is_err());
        for idx in [-1, 8, 100] {
            assert!(BingProvider::new()
                .with_time_offset(idx)
                .archive_url(1)
                .is_err());
        }
        assert!(base.archive_url(0).is_err());
        assert!(base.archive_url(9).is_err());
    }

    #[test]
    fn reduced_json_response_and_untrusted_urlbase() {
        let provider = BingProvider::new();
        let urls = provider
            .image_urls(r#"{"images":[{"urlbase":"/th?id=OHR.Flower_EN-US"}]}"#)
            .expect("valid reduced fixture");
        assert_eq!(urls.len(), 1);
        assert!(urls[0].as_str().contains("OHR.Flower_EN-US"));
        assert!(provider
            .image_urls(r#"{"images":[{"urlbase":"https://evil.test/th?id=x"}]}"#)
            .is_err());
        assert!(provider
            .image_urls(r#"{"images":[{"urlbase":"/th?id=..%2Fescape"}]}"#)
            .is_err());
        assert!(provider.image_urls("not json").is_err());
    }

    #[test]
    fn bing_archive_rejects_duplicate_and_encoded_alias_filenames() {
        let provider = BingProvider::new();
        let duplicate = r#"{"images":[
            {"urlbase":"/th?id=OHR.Flower_EN-US"},
            {"urlbase":"/th?id=OHR.Flower_EN-US"}
        ]}"#;
        assert!(provider.image_urls(duplicate).is_err());

        let alias = r#"{"images":[
            {"urlbase":"/th?id=OHR.Flower_EN-US"},
            {"urlbase":"/th?id=OHR.%46lower_EN-US"}
        ]}"#;
        assert!(provider.image_urls(alias).is_err());

        let unique = r#"{"images":[
            {"urlbase":"/th?id=OHR.Flower_EN-US"},
            {"urlbase":"/th?id=OHR.Forest_EN-US"}
        ]}"#;
        let urls = provider.image_urls(unique).expect("two distinct images");
        assert_eq!(urls.len(), 2);
        assert_ne!(urls[0], urls[1]);
    }

    #[test]
    fn archive_preflight_refuses_query_injection_and_bad_filenames() {
        let provider = BingProvider::new();
        for urlbase in [
            "/th?id=OHR.Photo_EN-US&other=value",
            "/th?id=OHR.Photo_EN-US#fragment",
            "/th?id=",
            "/th?id=..%2Fescape",
            "/th?id=OHR.Photo_EN-US%5Cescape",
            "/other?id=OHR.Photo_EN-US",
        ] {
            let body = serde_json::json!({"images": [{"urlbase": urlbase}]}).to_string();
            assert!(provider.image_urls(&body).is_err(), "rejected: {}", urlbase);
        }
    }

    #[test]
    fn archive_preflight_rejects_portable_case_collisions_and_oversized_lists() {
        let provider = BingProvider::new();
        let aliases = r#"{"images":[
            {"urlbase":"/th?id=OHR.Forest_EN-US"},
            {"urlbase":"/th?id=ohr.forest_en-us"}
        ]}"#;
        assert!(provider.image_urls(aliases).is_err());
        let entries: Vec<_> = (0..9)
            .map(|i| serde_json::json!({"urlbase": format!("/th?id=OHR.Day{i}_EN-US")}))
            .collect();
        let body = serde_json::json!({"images": entries}).to_string();
        assert!(provider.image_urls(&body).is_err());
        let valid = r#"{"images":[
            {"urlbase":"/th?id=OHR.Forest_EN-US"},
            {"urlbase":"/th?id=OHR.Desert_EN-US"}
        ]}"#;
        assert_eq!(provider.image_urls(valid).expect("valid archive").len(), 2);
    }

    #[test]
    fn bing_query_id_cannot_traverse_download_directory() {
        let url =
            Url::parse("https://www.bing.com/th?id=..%2Fescape.jpg").expect("valid URL fixture");
        let name = url
            .query_pairs()
            .find(|(key, _)| key == "id")
            .expect("id parameter")
            .1
            .into_owned();
        assert!(super::super::safe_download_path(".", &name).is_err());
    }
}

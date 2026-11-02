use anyhow::{anyhow, bail, Result};
use log::debug;
use serde::Deserialize;
use std::str::FromStr;
use url::Url;

use super::zone::Zone;
use super::{checked_image_url, http_client, request_with_retry, GetImgUrl, Orientation};
use crate::wp_selector::{WallPaper, WpType};

/// Pexels calls the endpoint /v1/search; retain the legacy PexelProvider spelling.
#[derive(Debug)]
pub struct PexelProvider {
    zone: Zone,
    dir: String,
    token: String,
    orientation: Orientation,
    query: String,
    page: u32,
    min_size: Option<(u32, u32)>,
    max_download_bytes: u64,
}

#[derive(Debug, Deserialize)]
struct Images {
    #[serde(default)]
    photos: Vec<Image>,
    #[serde(default)]
    next_page: Option<String>,
}

#[derive(Debug, Deserialize)]
struct Image {
    width: u32,
    height: u32,
    src: ImagesSrc,
}

#[derive(Debug, Deserialize)]
struct ImagesSrc {
    original: String,
}

impl Default for PexelProvider {
    fn default() -> Self {
        Self::new()
    }
}

impl PexelProvider {
    pub fn new() -> Self {
        Self {
            zone: Zone::Cn,
            dir: ".".to_string(),
            token: String::new(),
            orientation: Orientation::Landscape,
            query: "landscape wallpaper".to_string(),
            page: 1,
            min_size: None,
            max_download_bytes: super::DEFAULT_DOWNLOAD_LIMIT,
        }
    }

    pub fn with_zone(mut self, zone: &str) -> Result<Self> {
        self.zone = Zone::from_str(zone)?;
        Ok(self)
    }

    pub fn with_token(mut self, token: &str) -> Result<Self> {
        if token.trim().is_empty() {
            bail!("pexel token is empty");
        }
        self.token = token.to_string();
        Ok(self)
    }

    pub fn with_dir(mut self, path: &str) -> Self {
        self.dir = path.to_owned();
        self
    }

    pub fn with_orientation(mut self, orientation: Orientation) -> Self {
        self.orientation = orientation;
        self
    }

    pub fn with_query(mut self, query: &str) -> Result<Self> {
        if query.trim().is_empty() || query.len() > 200 || query.contains('\0') {
            bail!("Pexels query must contain 1..200 nonblank bytes and no NUL");
        }
        self.query = query.to_owned();
        Ok(self)
    }

    pub fn with_page(mut self, page: u32) -> Result<Self> {
        if !(1..=20).contains(&page) {
            bail!("Pexels page must be between 1 and 20");
        }
        self.page = page;
        Ok(self)
    }

    pub fn with_min_size(mut self, width: u32, height: u32) -> Result<Self> {
        if width == 0 || height == 0 || width > 16384 || height > 16384 {
            bail!("minimum dimensions must each be in 1..16384");
        }
        self.min_size = Some((width, height));
        Ok(self)
    }

    pub fn with_max_download_bytes(mut self, bytes: u64) -> Result<Self> {
        self.max_download_bytes = super::checked_download_limit(bytes)?;
        Ok(self)
    }

    fn search_url(&self, page: u32, count: u32) -> Result<Url> {
        if !(1..=64).contains(&count) {
            bail!("Pexels batch count must be 1..64");
        }
        if !(1..=20).contains(&page) {
            bail!("Pexels page must be between 1 and 20");
        }
        let mut url = Url::parse("https://api.pexels.com/v1/search")?;
        url.query_pairs_mut()
            .append_pair("query", &self.query)
            .append_pair("per_page", &count.min(80).to_string())
            .append_pair("page", &page.to_string())
            .append_pair("orientation", self.orientation.as_pexels())
            .append_pair("size", "large")
            .append_pair("locale", &self.zone.to_string());
        Ok(url)
    }

    fn accepted_urls(&self, body: &str) -> Result<Vec<Url>> {
        let response: Images = serde_json::from_str(body)?;
        response
            .photos
            .iter()
            .filter(|image| {
                self.min_size
                    .is_none_or(|(w, h)| image.width >= w && image.height >= h)
            })
            .map(|image| checked_image_url(&image.src.original, &["images.pexels.com"]))
            .collect()
    }
}

impl GetImgUrl for PexelProvider {
    fn get_img(&self, nums: u32) -> Result<Vec<WallPaper>> {
        if !(1..=64).contains(&nums) {
            bail!("Pexels batch count must be 1..64");
        }
        if self.token.trim().is_empty() {
            bail!("pexel token is empty");
        }
        let client = http_client()?;
        let mut wallpapers = Vec::with_capacity(nums as usize);
        // Bounded pagination: at most three pages, fail closed on empty/exhausted pages.
        for page in self.page..=(self.page + 2).min(20) {
            if wallpapers.len() >= nums as usize {
                break;
            }
            let url = self.search_url(page, nums)?;
            let response =
                request_with_retry(client.get(url).header("Authorization", &self.token))?;
            let body = response.text()?;
            let urls = self.accepted_urls(&body)?;
            let parsed: Images = serde_json::from_str(&body)?;
            if urls.is_empty() && parsed.next_page.is_none() {
                break;
            }
            for url in urls.into_iter().take(nums as usize - wallpapers.len()) {
                let path = download_image(&client, &url, &self.dir, self.max_download_bytes)?;
                wallpapers.push(
                    WallPaper::new()
                        .with_type(WpType::FromLocal)
                        .with_path(path),
                );
            }
            if parsed.next_page.is_none() {
                break;
            }
        }
        Ok(wallpapers)
    }
}

fn download_image(
    client: &reqwest::blocking::Client,
    url: &Url,
    dir: &str,
    max_bytes: u64,
) -> Result<String> {
    let name = url
        .path_segments()
        .and_then(|mut segments| segments.next_back())
        .ok_or_else(|| anyhow!("Pexels image URL has no path filename"))?;
    let path = super::safe_download_path(dir, name)?;
    let mut response = request_with_retry(client.get(url.clone()))?;
    super::reject_excess_content_length(response.content_length(), max_bytes)?;
    debug!("downloading Pexels image to {:?}", path);
    let transferred = super::write_complete_download_with_limit(&path, &mut response, max_bytes)?;
    debug!("staged {} Pexels image bytes", transferred);
    Ok(path
        .to_str()
        .ok_or_else(|| anyhow!("non-UTF8 download path"))?
        .to_owned())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn search_encodes_query_orientation_and_page() {
        let base = PexelProvider::new()
            .with_zone("en-US")
            .expect("locale")
            .with_query("winter woods & sky")
            .expect("query")
            .with_orientation(Orientation::Portrait)
            .with_page(3)
            .expect("page");
        let url = base.search_url(3, 24).expect("valid search");
        let params: std::collections::HashMap<_, _> = url.query_pairs().into_owned().collect();
        assert_eq!(params["query"], "winter woods & sky");
        assert_eq!(params["orientation"], "portrait");
        assert_eq!(params["locale"], "en-US");
        assert_eq!(params["page"], "3");
        assert_eq!(params["per_page"], "24");
        assert!(base.search_url(21, 1).is_err());
        assert!(base.search_url(1, 65).is_err());
    }

    #[test]
    fn filters_dimensions_using_metadata_before_download() {
        let provider = PexelProvider::new()
            .with_min_size(3840, 2160)
            .expect("size");
        let body = r#"{"photos":[
          {"width":1920,"height":1080,"src":{"original":"https://images.pexels.com/photos/1/small.jpeg"}},
          {"width":4096,"height":2304,"src":{"original":"https://images.pexels.com/photos/2/large.jpeg"}}
        ],"next_page":null}"#;
        let urls = provider.accepted_urls(body).expect("parse fixture");
        assert_eq!(urls.len(), 1);
        assert!(urls[0].as_str().ends_with("/large.jpeg"));
        assert!(provider.accepted_urls(r#"{"photos":[{"width":4000,"height":3000,"src":{"original":"http://example.com/a.jpg"}}]}"#).is_err());
        assert_eq!(
            provider
                .accepted_urls(r#"{"photos":[]}"#)
                .expect("empty")
                .len(),
            0
        );
        assert!(provider.accepted_urls("bad json").is_err());
    }

    #[test]
    fn query_page_and_resolution_are_bounded() {
        assert!(PexelProvider::new().with_query("").is_err());
        assert!(PexelProvider::new().with_query("  ").is_err());
        assert!(PexelProvider::new().with_page(0).is_err());
        assert!(PexelProvider::new().with_page(21).is_err());
        assert!(PexelProvider::new().with_min_size(0, 10).is_err());
        assert!(PexelProvider::new().with_min_size(3840, 2160).is_ok());
    }
}

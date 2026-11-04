//! Wallhaven's public SFW API (no API key required for public results).
use anyhow::{anyhow, bail, Result};
use log::debug;
use serde::Deserialize;
use std::collections::BTreeSet;
use url::Url;

use super::{checked_image_url, http_client, request_with_retry, GetImgUrl, Orientation};
use crate::wp_selector::{WallPaper, WpType};

#[derive(Debug)]
pub struct WallhavenProvider {
    dir: String,
    query: String,
    orientation: Orientation,
    min_size: Option<(u32, u32)>,
    page: u32,
    max_download_bytes: u64,
}

#[derive(Debug, Deserialize)]
struct SearchResults {
    #[serde(default)]
    data: Vec<WallpaperResult>,
    meta: Option<SearchMeta>,
}

#[derive(Debug, Deserialize)]
struct SearchMeta {
    last_page: u32,
}

#[derive(Debug, Deserialize)]
struct WallpaperResult {
    path: String,
    purity: String,
    dimension_x: u32,
    dimension_y: u32,
}

impl Default for WallhavenProvider {
    fn default() -> Self {
        Self::new()
    }
}

impl WallhavenProvider {
    pub fn new() -> Self {
        Self {
            dir: ".".to_owned(),
            query: "nature".to_owned(),
            orientation: Orientation::Landscape,
            min_size: None,
            page: 1,
            max_download_bytes: super::DEFAULT_DOWNLOAD_LIMIT,
        }
    }

    pub fn with_dir(mut self, dir: &str) -> Self {
        self.dir = dir.to_owned();
        self
    }

    pub fn with_query(mut self, query: &str) -> Result<Self> {
        if query.trim().is_empty() || query.len() > 200 || query.contains('\0') {
            bail!("Wallhaven query must contain 1..200 nonblank bytes and no NUL");
        }
        self.query = query.to_owned();
        Ok(self)
    }

    pub fn with_orientation(mut self, orientation: Orientation) -> Self {
        self.orientation = orientation;
        self
    }

    pub fn with_min_size(mut self, width: u32, height: u32) -> Result<Self> {
        if width == 0 || height == 0 || width > 16384 || height > 16384 {
            bail!("minimum dimensions must each be in 1..16384");
        }
        self.min_size = Some((width, height));
        Ok(self)
    }

    pub fn with_page(mut self, page: u32) -> Result<Self> {
        if !(1..=20).contains(&page) {
            bail!("Wallhaven page must be in 1..20");
        }
        self.page = page;
        Ok(self)
    }

    pub fn with_max_download_bytes(mut self, bytes: u64) -> Result<Self> {
        self.max_download_bytes = super::checked_download_limit(bytes)?;
        Ok(self)
    }

    fn search_url(&self, page: u32) -> Result<Url> {
        if !(1..=20).contains(&page) {
            bail!("Wallhaven page must be in 1..20");
        }
        let mut url = Url::parse("https://wallhaven.cc/api/v1/search")?;
        {
            let mut params = url.query_pairs_mut();
            params
                .append_pair("q", &self.query)
                .append_pair("purity", "100")
                .append_pair("categories", "100")
                .append_pair("ratios", self.orientation.as_wallhaven_ratio())
                .append_pair("page", &page.to_string());
            if let Some((w, h)) = self.min_size {
                params.append_pair("atleast", &format!("{}x{}", w, h));
            }
        }
        Ok(url)
    }

    /// Check local targets for the entire selected page before making any
    /// image request, and reject same-name results across prior pages.
    fn preflight_downloads(
        &self,
        urls: &[Url],
        seen: &BTreeSet<String>,
    ) -> Result<BTreeSet<String>> {
        let mut filenames = seen.clone();
        for url in urls {
            let name = image_filename(url)?;
            super::safe_download_path(&self.dir, name)?;
            // Portable collision rule for case-insensitive target volumes.
            if !filenames.insert(name.to_ascii_lowercase()) {
                bail!("Wallhaven response contains colliding download filenames");
            }
        }
        Ok(filenames)
    }

    fn accepted_urls(&self, body: &str) -> Result<(Vec<Url>, Option<u32>)> {
        let response: SearchResults = serde_json::from_str(body)?;
        let urls = response
            .data
            .iter()
            .filter(|image| image.purity == "sfw")
            .filter(|image| {
                self.min_size
                    .is_none_or(|(w, h)| image.dimension_x >= w && image.dimension_y >= h)
            })
            .map(|image| checked_image_url(&image.path, &["w.wallhaven.cc"]))
            .collect::<Result<Vec<_>>>()?;
        Ok((urls, response.meta.map(|m| m.last_page)))
    }
}

fn image_filename(url: &Url) -> Result<&str> {
    url.path_segments()
        .and_then(|mut segments| segments.next_back())
        .filter(|name| !name.is_empty())
        .ok_or_else(|| anyhow!("Wallhaven image has no filename"))
}

impl GetImgUrl for WallhavenProvider {
    fn get_img(&self, nums: u32) -> Result<Vec<WallPaper>> {
        if !(1..=48).contains(&nums) {
            bail!("Wallhaven batch count must be in 1..48");
        }
        let client = http_client()?;
        let mut wallpapers = Vec::with_capacity(nums as usize);
        let mut seen = BTreeSet::new();
        // Wallhaven returns at most 24 per page. Fetch no more than 3 pages.
        for page in self.page..=(self.page + 2).min(20) {
            if wallpapers.len() >= nums as usize {
                break;
            }
            let body = super::read_metadata_response(request_with_retry(
                client.get(self.search_url(page)?),
            )?)?;
            let (urls, last_page) = self.accepted_urls(&body)?;
            let no_candidates = urls.is_empty();
            let chosen: Vec<_> = urls.into_iter().take(nums as usize - wallpapers.len()).collect();
            let validated_names = self.preflight_downloads(&chosen, &seen)?;
            for url in chosen {
                let file_name = image_filename(&url)?;
                let path = super::safe_download_path(&self.dir, file_name)?;
                let mut response = request_with_retry(client.get(url))?;
                super::reject_excess_content_length(
                    response.content_length(),
                    self.max_download_bytes,
                )?;
                debug!("downloading Wallhaven image to {:?}", path);
                let transferred = super::write_complete_download_with_limit(
                    &path,
                    &mut response,
                    self.max_download_bytes,
                )?;
                debug!("staged {} Wallhaven image bytes", transferred);
                wallpapers.push(
                    WallPaper::new().with_type(WpType::FromLocal).with_path(
                        path.to_str()
                            .ok_or_else(|| anyhow!("non-UTF8 download path"))?
                            .to_owned(),
                    ),
                );
            }
            seen = validated_names;
            if last_page.is_some_and(|last| page >= last) || (no_candidates && last_page.is_none())
            {
                break;
            }
        }
        Ok(wallpapers)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn search_is_sfw_and_filters_orientation_and_resolution() {
        let p = WallhavenProvider::new()
            .with_query("forests & lakes")
            .expect("query")
            .with_orientation(Orientation::Portrait)
            .with_min_size(1080, 1920)
            .expect("size")
            .with_page(2)
            .expect("page");
        let url = p.search_url(2).expect("URL");
        let params: std::collections::HashMap<_, _> = url.query_pairs().into_owned().collect();
        assert_eq!(params["q"], "forests & lakes");
        assert_eq!(params["purity"], "100");
        assert_eq!(params["categories"], "100");
        assert_eq!(params["ratios"], "9x16");
        assert_eq!(params["atleast"], "1080x1920");
        assert_eq!(params["page"], "2");
        assert!(p.search_url(21).is_err());
    }

    #[test]
    fn parses_sfw_candidates_and_rejects_external_image_hosts() {
        let provider = WallhavenProvider::new()
            .with_min_size(1920, 1080)
            .expect("size");
        let body = r#"{"data":[
          {"purity":"sfw","dimension_x":3840,"dimension_y":2160,"path":"https://w.wallhaven.cc/ab/wallhaven-abc123.jpg"},
          {"purity":"sketchy","dimension_x":3840,"dimension_y":2160,"path":"https://w.wallhaven.cc/ab/wallhaven-bcd234.jpg"},
          {"purity":"sfw","dimension_x":800,"dimension_y":600,"path":"https://w.wallhaven.cc/ab/wallhaven-cde345.jpg"}
        ],"meta":{"last_page":2}}"#;
        let (urls, last) = provider.accepted_urls(body).expect("fixture");
        assert_eq!(urls.len(), 1);
        assert_eq!(last, Some(2));
        assert!(urls[0].as_str().ends_with("wallhaven-abc123.jpg"));
        let hostile = r#"{"data":[{"purity":"sfw","dimension_x":4000,"dimension_y":3000,"path":"https://evil.invalid/a.jpg"}]}"#;
        assert!(provider.accepted_urls(hostile).is_err());
        assert!(provider.accepted_urls("not json").is_err());
        assert!(provider.accepted_urls(r#"{"data":[]}"#).is_ok());
    }

    #[test]
    fn page_preflight_rejects_colliding_and_unsafe_wallhaven_targets() {
        let temp = tempfile::tempdir().expect("sandbox");
        let provider = WallhavenProvider::new().with_dir(temp.path().to_str().expect("path"));
        let duplicates = [
            Url::parse("https://w.wallhaven.cc/aa/wallhaven-abc.jpg").expect("URL"),
            Url::parse("https://w.wallhaven.cc/bb/wallhaven-abc.jpg").expect("URL"),
        ];
        assert!(provider
            .preflight_downloads(&duplicates, &BTreeSet::new())
            .is_err());
        let aliases = [
            Url::parse("https://w.wallhaven.cc/aa/ABC.jpeg").expect("URL"),
            Url::parse("https://w.wallhaven.cc/bb/abc.JPEG").expect("URL"),
        ];
        assert!(provider
            .preflight_downloads(&aliases, &BTreeSet::new())
            .is_err());
        let unsafe_name = [Url::parse("https://w.wallhaven.cc/aa/CON.jpg").expect("URL")];
        assert!(provider
            .preflight_downloads(&unsafe_name, &BTreeSet::new())
            .is_err());
        assert_eq!(std::fs::read_dir(temp.path()).expect("empty").count(), 0);
    }

    #[test]
    fn page_preflight_blocks_later_page_collisions_but_keeps_unique_names() {
        let temp = tempfile::tempdir().expect("sandbox");
        let provider = WallhavenProvider::new().with_dir(temp.path().to_str().expect("path"));
        let first = [Url::parse("https://w.wallhaven.cc/aa/a.png").expect("URL")];
        let second = [Url::parse("https://w.wallhaven.cc/bb/b.png").expect("URL")];
        let seen = provider
            .preflight_downloads(&first, &BTreeSet::new())
            .expect("first batch");
        let seen = provider
            .preflight_downloads(&second, &seen)
            .expect("distinct next page");
        assert_eq!(seen.len(), 2);
        assert!(provider.preflight_downloads(&first, &seen).is_err());
    }

    #[test]
    fn invalid_pages_queries_and_sizes_fail() {
        assert!(WallhavenProvider::new().with_page(0).is_err());
        assert!(WallhavenProvider::new().with_page(21).is_err());
        assert!(WallhavenProvider::new().with_query("").is_err());
        assert!(WallhavenProvider::new().with_min_size(0, 1080).is_err());
    }
}

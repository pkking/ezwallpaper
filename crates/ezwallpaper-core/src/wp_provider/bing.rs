use super::resolution::Resolution;
use super::zone::Zone;
use super::GetImgUrl;
use crate::wp_selector::{WallPaper, WpType};
use serde::{Deserialize, Serialize};

use anyhow::{anyhow, Result};
use log::debug;
use std::str::FromStr;
use std::vec::Vec;
use url::Url;

#[derive(Debug, Default)]
pub struct BingProvider {
    zone: Zone,
    resolution: Resolution,
    time_offset: i32,
    dir: String,
}

#[allow(dead_code)]
impl BingProvider {
    pub fn new() -> Self {
        BingProvider {
            zone: Zone::Cn,
            resolution: Resolution::R1920x1200,
            time_offset: 0,
            dir: ".".to_string(),
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
        self.dir = path.to_string();
        self
    }
}

impl GetImgUrl for BingProvider {
    fn get_img(&self, nums: u32) -> Result<Vec<WallPaper>> {
        let body = reqwest::blocking::get(format!(
            "https://www.bing.com/HPImageArchive.aspx?format=js&idx={}&n={}&mkt={}",
            self.time_offset, nums, self.zone
        ))?
        .text()?;
        let mut res = Vec::with_capacity(nums as usize);
        let mut p: Images = serde_json::from_str(&body)?;
        //wallpaper::set_from_url("https://source.unsplash.com/random").unwrap();
        //println!("{:?}", wallpaper::get());
        for u in p.images.iter_mut() {
            let path = download_image(
                &Url::parse(&format!(
                    "https://www.bing.com{}_{}.jpg",
                    u.urlbase, self.resolution
                ))?,
                &self.dir,
            )?;
            res.push(
                WallPaper::new()
                    .with_type(WpType::FromLocal)
                    .with_path(path),
            );
        }
        Ok(res)
    }
}

fn download_image(url: &Url, dir: &str) -> Result<String> {
    let file_name = url
        .query_pairs()
        .find(|(key, _)| key == "id")
        .map(|(_, value)| value.into_owned())
        .ok_or_else(|| anyhow!("Bing image URL has no id filename: {}", url.as_str()))?;
    let file_path = super::safe_download_path(dir, &file_name)?;
    // An unsuccessful HTTP response must not truncate an existing wallpaper.
    let mut response = reqwest::blocking::get(url.as_str())?.error_for_status()?;
    debug!("download dest {:?} ", file_path);
    super::write_complete_download(&file_path, &mut response)?;
    debug!("download {:?} pic to {:?}", url, file_path);
    Ok(file_path
        .to_str()
        .ok_or_else(|| anyhow!("download output path is not UTF-8"))?
        .to_owned())
}

#[derive(Serialize, Deserialize, Debug)]
struct Images {
    images: Vec<Image>,
}

#[derive(Serialize, Deserialize, Debug)]
struct Image {
    startdate: String,
    fullstartdate: String,
    enddate: String,
    url: String,
    urlbase: String,
    copyright: String,
    copyrightlink: String,
    title: String,
    quiz: String,
    wp: bool,
    hsh: String,
    drk: i32,
    top: i32,
    bot: i32,
    hs: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

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

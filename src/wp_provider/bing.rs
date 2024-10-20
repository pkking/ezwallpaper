use super::resolution::Resolution;
use super::zone::Zone;
use super::GetImgUrl;
use crate::wp_selector::{WallPaper, WpType};
use serde::{Deserialize, Serialize};

use anyhow::{anyhow, Result};
use log::debug;
use std::fs::File;
use std::vec::Vec;
use std::{path::Path, str::FromStr};
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
    let (_, mut file_name) = url
        .query_pairs()
        .into_owned()
        .next()
        .ok_or(anyhow!("no file name found in url: {}", url.as_str()))?;
    if file_name.is_empty() {
        file_name = "wallpaper".to_string();
    }
    let file_path = Path::new(dir).join(&file_name);
    debug!("download dest {:?} ", file_path);
    let mut file = File::create(&file_path)?;
    debug!("file created");
    reqwest::blocking::get(url.as_str())?.copy_to(&mut file)?;
    debug!("download {:?} pic to {:?}", url, file_path.to_str());
    Ok(file_path.to_str().to_owned().expect("get file path").into())
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

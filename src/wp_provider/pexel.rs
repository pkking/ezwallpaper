use core::panic;
use std::{fs::File, str::FromStr};

use anyhow::Result;
use serde::{Deserialize, Serialize};
use url::Url;

use super::zone::Zone;
use super::GetImgUrl;
use crate::wp_selector::{WallPaper, WpType};
use log::debug;

#[derive(Debug, Default)]
pub struct PexelProvider {
    zone: Zone,
    dir: String,
    token: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Images {
    total_results: u32,
    page: u32,
    per_page: u32,
    photos: Vec<Image>,
    next_page: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Image {
    id: u32,
    width: u32,
    height: u32,
    url: String,
    photographer: String,
    photographer_url: String,
    photographer_id: u32,
    avg_color: String,
    src: ImagesSrc,

    liked: bool,
    alt: String,
}
#[derive(Debug, Deserialize, Serialize)]
pub struct ImagesSrc {
    original: String,
    large2x: String,
    large: String,
    medium: String,
    small: String,
    portrait: String,
    landscape: String,
    tiny: String,
}
#[allow(dead_code)]
impl PexelProvider {
    pub fn new() -> Self {
        PexelProvider {
            zone: Zone::Cn,
            dir: ".".to_string(),
            token: "".to_string(),
        }
    }
    pub fn with_zone(mut self, zone: &str) -> Self {
        self.zone = Zone::from_str(zone).unwrap();
        self
    }

    pub fn with_token(mut self, token: &str) -> Self {
        if token.is_empty() {
            panic!("pexel token is empty");
        }
        self.token = token.to_string();
        self
    }

    pub fn with_dir(mut self, path: &str) -> Self {
        self.dir = path.to_string();
        self
    }
}

impl GetImgUrl for PexelProvider {
    fn get_img(&self, nums: u32) -> Result<Vec<WallPaper>> {
        let url = format!(
            "https://api.pexels.com/v1/search?query=landscape%20wallpaper&per_page={}&orientation=landscape&size=large&location={}",
            nums,
            self.zone
        );

        let client = reqwest::blocking::Client::new();
        let response: Images = client
            .get(url)
            .header("authorization", self.token.clone())
            .send()?
            .json()?;

        let mut res: Vec<WallPaper> = Vec::with_capacity(nums as usize);
        // TODO: get image from unsplash like wallpaper::set_from_url("https://source.unsplash.com/photos/random").unwrap();
        // see: https://unsplash.com/documentation#get-a-random-photo
        for i in response.photos.iter() {
            let path = download_image(&Url::parse(&i.src.original)?, &self.dir)?;
            debug!("{:?}", path);
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
    let path = format!("{}/{}", dir, url.path_segments().unwrap().last().unwrap());
    debug!("download {:?} to {:?}", url.as_str(), dir);
    let mut file = File::create(&path)?;

    reqwest::blocking::get(url.as_str())?.copy_to(&mut file)?;
    Ok(path)
}

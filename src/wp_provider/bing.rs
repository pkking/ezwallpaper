use super::errors::BingProviderErr;
use super::GetImgUrl;
use crate::wp_selector::{WallPaper, WpType};
use serde::{Deserialize, Serialize};
use std::error::Error;
use std::fs::File;
use std::path::Path;
use std::str::FromStr;
use std::vec::Vec;
use url::Url;

const R1280X768: &str = "1280x768";
const R640X480: &str = "640x480";
const R800X600: &str = "800x600";
const R1024X768: &str = "1024x768";
const R280X720: &str = "280x720";
const R1920X1080: &str = "1920x1080";
const R800X480: &str = "800x480";
const R1366X768: &str = "1366x768";
const R1920X1200: &str = "1920x1200";

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
    pub fn with_zone(mut self, zone: Zone) -> Self {
        self.zone = zone;
        self
    }

    pub fn with_resolution(mut self, resolution: Resolution) -> Self {
        self.resolution = resolution;
        self
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

fn download_image(url: &Url, dir: &str) -> Result<String, Box<dyn Error>> {
    let (_, mut file_name) = url
        .query_pairs()
        .into_owned()
        .next()
        .ok_or("no file name")?;
    if file_name.is_empty() {
        file_name = "wallpaper".to_string();
    }
    let file_path = Path::new(dir).join(&file_name);
    //println!("download dest {:?} ", file_path);
    let mut file = File::create(&file_path)?;
    //println!("file created");
    reqwest10::blocking::get(url.as_str())?.copy_to(&mut file)?;
    //println!("download {:?} pic to {:?}", url, file_path.to_str());
    Ok(file_path.to_str().to_owned().unwrap().into())
}

impl GetImgUrl for BingProvider {
    fn get_img(&self, nums: u32) -> Result<Vec<WallPaper>, BingProviderErr> {
        let body = reqwest10::blocking::get(&format!(
            "https://www.bing.com/HPImageArchive.aspx?format=js&idx={}&n={}&mkt={}",
            self.time_offset,
            nums,
            self.zone.to_string()
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
                    u.urlbase.to_string(),
                    self.resolution.to_string()
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
#[derive(Debug)]
#[allow(dead_code)]
pub enum Resolution {
    R640x480,
    R800x600,
    R1024x768,
    R280x720,
    R1920x1080,
    R800x480,
    R1366x768,
    R1920x1200,
    R1280x768,
}
impl Default for Resolution {
    fn default() -> Self {
        Resolution::R1920x1080
    }
}
impl std::fmt::Display for Resolution {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Resolution::R640x480 => write!(f, "{}", R640X480),
            Resolution::R800x600 => write!(f, "{}", R800X600),
            Resolution::R1024x768 => write!(f, "{}", R1024X768),
            Resolution::R280x720 => write!(f, "{}", R280X720),
            Resolution::R1920x1080 => write!(f, "{}", R1920X1080),
            Resolution::R800x480 => write!(f, "{}", R800X480),
            Resolution::R1366x768 => write!(f, "{}", R1366X768),
            Resolution::R1920x1200 => write!(f, "{}", R1920X1200),
            Resolution::R1280x768 => write!(f, "{}", R1280X768),
        }
    }
}

impl FromStr for Resolution {
    type Err = BingProviderErr;

    fn from_str(val: &str) -> Result<Self, Self::Err> {
        match val {
            R640X480 => Ok(Resolution::R640x480),
            R800X600 => Ok(Resolution::R800x600),
            R1024X768 => Ok(Resolution::R1024x768),
            R280X720 => Ok(Resolution::R280x720),
            R1920X1080 => Ok(Resolution::R1920x1080),
            R800X480 => Ok(Resolution::R800x480),
            R1366X768 => Ok(Resolution::R1366x768),
            R1920X1200 => Ok(Resolution::R1920x1200),
            R1280X768 => Ok(Resolution::R1280x768),
            _ => Err(BingProviderErr::InvalidParam),
        }
    }
}
#[derive(Debug)]
#[allow(dead_code)]
pub enum Zone {
    Cn,
    En,
    Jp,
    Au,
    De,
    Nz,
    Ca,
}
const CN: &str = "zh-CN";
const US: &str = "en-US";
const JP: &str = "ja-JP";
const AU: &str = "en-AU";
const DE: &str = "de-DE";
const NZ: &str = "en-NZ";
const CA: &str = "en-CA";
impl Default for Zone {
    fn default() -> Self {
        Zone::Cn
    }
}
impl FromStr for Zone {
    type Err = BingProviderErr;

    fn from_str(val: &str) -> Result<Self, Self::Err> {
        match val {
            CN => Ok(Zone::Cn),
            US => Ok(Zone::En),
            JP => Ok(Zone::Jp),
            AU => Ok(Zone::Au),
            DE => Ok(Zone::De),
            NZ => Ok(Zone::Nz),
            CA => Ok(Zone::Ca),
            _ => Err(BingProviderErr::InvalidParam),
        }
    }
}

impl std::fmt::Display for Zone {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Zone::Cn => write!(f, "{}", CN),
            Zone::En => write!(f, "{}", US),
            Zone::Jp => write!(f, "{}", JP),
            Zone::Au => write!(f, "{}", AU),
            Zone::De => write!(f, "{}", DE),
            Zone::Nz => write!(f, "{}", NZ),
            Zone::Ca => write!(f, "{}", CA),
        }
    }
}

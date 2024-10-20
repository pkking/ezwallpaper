use std::str::FromStr;
use anyhow::Result;

const R1280X768: &str = "1280x768";
const R640X480: &str = "640x480";
const R800X600: &str = "800x600";
const R1024X768: &str = "1024x768";
const R280X720: &str = "280x720";
const R1920X1080: &str = "1920x1080";
const R800X480: &str = "800x480";
const R1366X768: &str = "1366x768";
const R1920X1200: &str = "1920x1200";
const UHD: &str = "UHD";

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
    UHD,
}
impl Default for Resolution {
    fn default() -> Self {
        Resolution::UHD
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
            Resolution::UHD => write!(f, "{}", UHD),
        }
    }
}

impl FromStr for Resolution {
    type Err = anyhow::Error;

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
            UHD => Ok(Resolution::UHD),
            _ => Err(anyhow::anyhow!("unknown resolution: {}", val)),
        }
    }
}
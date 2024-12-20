use anyhow::Result;
use std::str::FromStr;

#[derive(Debug, Default)]
#[allow(dead_code)]
pub enum Zone {
    #[default]
    Cn,
    En,
    Jp,
    De,
}
const CN: &str = "zh-CN";
const US: &str = "en-US";
const JP: &str = "ja-JP";
const DE: &str = "de-DE";

impl FromStr for Zone {
    fn from_str(val: &str) -> Result<Self> {
        match val {
            CN => Ok(Zone::Cn),
            US => Ok(Zone::En),
            JP => Ok(Zone::Jp),
            DE => Ok(Zone::De),
            _ => Err(anyhow::anyhow!("unknown zone {}", val)),
        }
    }

    type Err = anyhow::Error;
}

impl std::fmt::Display for Zone {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Zone::Cn => write!(f, "{}", CN),
            Zone::En => write!(f, "{}", US),
            Zone::Jp => write!(f, "{}", JP),
            Zone::De => write!(f, "{}", DE),
        }
    }
}

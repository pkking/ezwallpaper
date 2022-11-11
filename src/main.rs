extern crate derivative;
extern crate dirs;
extern crate reqwest10;
extern crate serde_json;
extern crate url;
extern crate wallpaper;

mod wp_provider;
mod wp_selector;
use std::str::FromStr;
use wp_provider::bing::{BingProvider, Resolution, Zone};
use wp_provider::GetImgUrl;
use clap::Parser;

const  DEFAULT_RESOLUTION: &str = "1920x1080";
const DEFAULT_LOCALE:  &str = "zh-CN";

/// Simple program to greet a person
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// pic resolution
    #[arg(short, long, default_value_t = DEFAULT_RESOLUTION.to_string())]
    resolution: String,

    /// zone info for searching in bing
    #[arg(short, long, default_value_t = DEFAULT_LOCALE.to_string())]
    locale: String,

    /// dir to store downloaded pictures
    #[arg(short, long, default_value_t = dirs::picture_dir().unwrap().to_str().unwrap().to_string())]
    dir: String,
}

fn main() {
    let cli = Args::parse();

    let bing: BingProvider = BingProvider::new()
        .with_zone(
            Zone::from_str(&cli.locale).expect(format!("invalid locale argument {}", cli.locale).as_str()),
        )
        .with_resolution(
            Resolution::from_str(&cli.resolution)
                .expect(format!("invalid resolution argument {}", cli.resolution).as_str()),
        )
        .with_time_offset(0)
        .with_dir(&cli.dir);
    // TODO: using wp selector to get pics
    let result_vec = bing.get_img(1).unwrap();
    println!("using wallpaper from {}", result_vec[0].path());
    wallpaper::set_from_path(result_vec[0].path()).unwrap();
}

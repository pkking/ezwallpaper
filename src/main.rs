extern crate derivative;
extern crate dirs;
extern crate reqwest;
extern crate serde_json;
extern crate url;
extern crate wallpaper;

mod wp_provider;
mod wp_selector;
use clap::Parser;
use log::debug;
use wp_provider::bing::BingProvider;
use wp_provider::GetImgUrl;

const DEFAULT_RESOLUTION: &str = "UHD";
const DEFAULT_LOCALE: &str = "zh-CN";
const DEFAULT_BACKEND: &str = "bing";

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

    /// backend for wallpaper, can be bing or pexel
    #[arg(short, long, default_value_t = DEFAULT_BACKEND.to_string())]
    backend: String,

    /// token for pexel, only valid when backend is pexel
    #[arg(long, default_value_t = String::from(""))]
    token: String,
}

fn build_provider(cli: &Args) -> Box<dyn GetImgUrl> {
    match cli.backend.as_str() {
        "bing" => Box::new(
            BingProvider::new()
                .with_zone(&cli.locale)
                .with_resolution(&cli.resolution)
                .with_time_offset(0)
                .with_dir(&cli.dir),
        ),
        "pexel" => Box::new(
            wp_provider::pexel::PexelProvider::new()
                .with_dir(&cli.dir)
                .with_token(&cli.token)
                .with_zone(&cli.locale),
        ),
        _ => panic!("unsupported backend"),
    }
}
fn main() {
    let cli = Args::parse();

    env_logger::init();

    let provider = build_provider(&cli);
    // TODO: using wp selector to get pics
    let result_vec = provider.get_img(1).unwrap();
    match result_vec.len() {
        0 => {}
        _ => {
            debug!("using wallpaper from {}", result_vec[0].path());
            wallpaper::set_from_path(result_vec[0].path()).unwrap();
        }
    }
}

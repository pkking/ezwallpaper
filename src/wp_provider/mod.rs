pub mod bing;
pub mod errors;

use crate::wp_selector::WallPaper;
use errors::BingProviderErr;

pub trait GetImgUrl {
    fn get_img(&self, nums: u32) -> Result<Vec<WallPaper>, BingProviderErr>;
}

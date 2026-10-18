pub mod bing;
pub mod pexel;
mod resolution;
mod zone;

use crate::wp_selector::WallPaper;
use anyhow::Result;

pub trait GetImgUrl {
    fn get_img(&self, nums: u32) -> Result<Vec<WallPaper>>;
}

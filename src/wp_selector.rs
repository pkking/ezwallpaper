use derivative::Derivative;
use std::fmt::Display;

#[derive(Debug, Derivative)]
#[derivative(Default)]
#[allow(dead_code)]
pub enum WpType {
    #[derivative(Default)]
    FromLocal,
    FromUrl,
}

impl Display for WpType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match &self {
            WpType::FromLocal => write!(f, "LOCAL"),
            WpType::FromUrl => write!(f, "URL"),
        }
    }
}
#[derive(Debug, Derivative)]
#[derivative(Default(new = "true"))]
pub struct WallPaper {
    wp_type: WpType,
    path: String,
}

impl Display for WallPaper {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "type:{} path:{}", self.wp_type, self.path)
    }
}
#[allow(dead_code)]
impl WallPaper {
    pub fn path(&self) -> &str {
        &self.path
    }

    pub fn wp_type(&self) -> &WpType {
        &self.wp_type
    }

    pub fn with_path(mut self, path: String) -> Self {
        self.path = path;
        self
    }

    pub fn with_type(mut self, wp_type: WpType) -> Self {
        self.wp_type = wp_type;
        self
    }
}

use reqwest10::Error;

#[derive(Debug)]
pub enum BingProviderErr {
    RequestErr(Error),
    InternalErr,
    InvalidParam,
}

impl From<reqwest10::Error> for BingProviderErr {
    fn from(error: reqwest10::Error) -> Self {
        BingProviderErr::RequestErr(error)
    }
}

impl From<serde_json::Error> for BingProviderErr {
    fn from(_: serde_json::Error) -> Self {
        BingProviderErr::InternalErr
    }
}

impl From<Box<url::ParseError>> for BingProviderErr {
    fn from(_: Box<url::ParseError>) -> Self {
        BingProviderErr::InternalErr
    }
}

impl From<url::ParseError> for BingProviderErr {
    fn from(_: url::ParseError) -> Self {
        BingProviderErr::InternalErr
    }
}

impl From<Box<dyn std::error::Error>> for BingProviderErr {
    fn from(_: Box<dyn std::error::Error>) -> Self {
        BingProviderErr::InternalErr
    }
}

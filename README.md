# intro
a tool to change wallpaper

# features
- support get images from [bing daliy picture](www.bing.com)
- support get images from local file system

# road map
TBC

# usage
only test bash in mingw64 on windows 10 & windows 11:)
```bash
Usage: ezwallpaper [OPTIONS]

Options:
  -r, --resolution <RESOLUTION>  pic resolution [default: 1920x1080]
  -l, --locale <LOCALE>          zone info for searching in bing [default: zh-CN]
  -d, --dir <DIR>                dir to store downloaded pictures [default: C:\Users\l00440707\Pictures]
  -h, --help                     Print help information
  -V, --version                  Print version information
```
will store the picture to [picture_dir](https://docs.rs/dirs/3.0.1/dirs/fn.picture_dir.html)
# known issues
TBC
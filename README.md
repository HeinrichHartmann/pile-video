# Pile video

Based on https://github.com/hyeonsangjeon/youtube-dl-nas

Simple Web-Application that allows to:

1. Show gallery view of video files in ./videos
2. Add videos to gallery via [yt-dlp](https://github.com/yt-dlp/yt-dlp)

Features:

- Automatic updates of yt-dlp to stay up-to date
- Async re-coding of all videos to mp4
- Async audio-extraction of all videos


## Usage

```
make serve # serve local development version at port :8080
```

## Folders

- `./videos` -- video gallery
- `./videos/pile` -- downloads go here
- `./mp3` -- extracted audio goes here

- `./cache` -- previews go here
- `./tmp` -- used during download and recoding

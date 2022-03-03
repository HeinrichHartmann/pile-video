find ./videos/ -type f -and '(' -name "*.mkv" -or -name "*.mp4" -or -name "*.webm" ')' -exec ffmpeg -i "{}" -ss 00:00:20.000 -vframes 1 "{}.png" -n \;

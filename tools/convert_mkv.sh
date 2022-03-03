find ./videos/ -type f -name '*.mkv' -exec ffmpeg -i "{}" -map 0 -c copy -c:a aac "{}.mp4" \;

# Geovideo to Geoframes

## In one sentence

Command line Python script that 1) takes video file with GPS telemetry track, 2) extracts all video metadata, 3) splits videos into frames at user defined frame rate, and 4) re-emberd original metadata into extracted frames (including geotags).

## Why we built this

Working with image files is a lot easier and less computationally intensive than video files.

Many third-party 360 image hosting services (namely Mapillary) do not support video uploads at the time of writing (June 2020).

We considered a number of open-source tools, like ffmpeg, to do this using inbuilt functionality. Sadly it could not achieve what we needed (paticularly around geotagging), and such tools would require quite a bit of retooling to do alone.

However, there were other tools, like ExifTool, we could in conjunction with ffmpeg to create a video to frame processing that retained all data.

Geovideo to Geoframes is the result.

## How it works

1. 

## Requirements

TODO

### Software Requirements

TODO

### Video Requirements

TODO

## Quick start guide

TODO

## Support 

We offer community support for all our software on our Campfire forum. [Ask a question or make a suggestion here](https://campfire.trekview.org/c/support/8).

## License

Geovideo to Geoframes is licensed under an [GNU AGPLv3 License](https://github.com/trek-view/geovideo-to-geoframes/blob/master/LICENSE.txt).
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

1. You specify the geotagged video and the framerate (frames per second) to be extracted
2. The script will extract the metadata of the video
3. The script will use ffmpeg to split the video into frames at specified frame rate
4. The script will embed a `DateTimeOriginal` to each frame using the first time and using the specified framerate to offset time value (e.g first frame = earliest time, second frame = earliest time + frame rate, ...)
5. The script will embed global metadata to each frame (e.g. camera make and model)
6. The script will geotag each frame with GPS co-ordinate (latitude, longitude, and altitude)

**Note on timestamps**

We use `GPSdatetime` for the time of the first frame rather than the `createDate` (or similar), because the reported `createDate` often represents the time of stitching not the time the imagery was actually captured.

In cases where images are stiched on computers the `createDate` will always be much later than the time imagery was taken. When on camera stitching occurs this is less of a problem (although there might be a slight delay between capture and process on the camera).

[This output shows a good example](https://gitlab.com/snippets/1979531). See all `createDate`'s refer to `2020:04:15 09:14:04` but first `GPSDateTime` is `2020:04:13 15:37:22.444`.

### OS Requirements

Works on Windows, Linux and MacOS.

### Software Requirements

* Python version 3.6+
* [exiftool](https://exiftool.org/)
* [ffmpeg](https://www.ffmpeg.org/download.html)

### Video Requirements

* Must be a video format understood by ffmpeg and exiftool
* Must be [XMP] ProjectionType=equirectangular
* Must have contain a telemetry track with GPS data
	- `GPSLatitude`
	- `GPSLongitude`
	- `GPSAltitude`
	- `GPSDateTime` OR (`GPSDateStamp` AND `GPSTimeStamp`) OR `createDate`

This software will work with most video formats. Whilst it is designed for 360 vide, it will work with traditional flat (Cartesian) videos too.

## More on metadata tracks in video (for developers)

Telemetry data is reported as a track in a video file.

[I recommend reading more about metadata tracks here](https://www.trekview.org/blog/2020/metadata-exif-xmp-360-video-files/).

[We (Trek View) also maintain a repository of example video metadata tracks from popular 360 cameras](https://github.com/trek-view/360-camera-metadata).

## Quick start guide

### Command Line Arguments

* t: time (optional: default is timegps)
	- timegps (first `GPSDateTime` of video)
	- timecapture (`CreateDate` of video)

_A note on time. We recommend using `timegps` ([EXIF] `GPSDateTime`) not `timecapture` ([EXIF] `createDate`) unless you are absolutely sure `createDate` is correct. Many 360 stitching tools rewrite `createDate` as datetime of stitching process not the datetime the image was actually captured. This can cause issues when sorting by time (e.g. images might not be stitched in capture order). Therefore, `GPSDateTime` is more likely to represent the true time of capture._

* e: extraction type (optional: default is e)
	- gpx (extracts gpx track and then rembeds to image. Is widely supported for most camera types, but usually offers lower resolution of GPS points which may cause video frame rate restrictions, and assumes GPS starts from video start which is not always the case if GPS signal takes some time to resolve)
	- full (entire gps telemetry will be extracted from video. Offers a much higher resolution but only supports cameras that write telemetry in either gmpf or camm6 format. [More on telemetry standards here](https://github.com/trek-view/360-camera-metadata/tree/master/0-standards).).

```
python gf2gv.py -t [TIME] -e [GPS EXTRACTION TYPE] VIDEO_FILE FRAME_RATE OUTPUT_FRAME_DIRECTORY
```

```
python gf2gv.py -t timegps -e gpx VIDEO_0294.mp4 1 my_video_frames/
```


TODO

## Support 

We offer community support for all our software on our Campfire forum. [Ask a question or make a suggestion here](https://campfire.trekview.org/c/support/8).

## License

Geovideo to Geoframes is licensed under a [GNU AGPLv3 License](https://github.com/trek-view/geovideo-to-geoframes/blob/master/LICENSE.txt).
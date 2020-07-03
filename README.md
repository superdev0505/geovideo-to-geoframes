# Geovideo to Geoframes

## In one sentence

Command line Python script that 1) takes video file with GPS telemetry track, 2) extracts all video metadata, 3) splits videos into frames at user defined frame rate, and 4) re-embed original metadata into extracted frames (including geotags).

## Why we built this

Working with image files is a lot easier and less computationally intensive than video files.

Many third-party 360 image hosting services (namely Mapillary) do not support video uploads at the time of writing (June 2020).

We considered a number of open-source tools, like ffmpeg, to do this using inbuilt functionality. Sadly it could not achieve what we needed (paticularly around geotagging), and such tools would require quite a bit of retooling to do alone.

However, there were other tools, like ExifTool, we could in conjunction with ffmpeg to create a video to frame processing that retained all data.

Geovideo to Geoframes is the result.

## How it works

1. You specify the geotagged video and the framerate (frames per second) to be extracted
2. The script will extract the metadata of the video
3. The script will use ffmpeg to split the video into frames (`.jpg` files) at specified frame rate
4. The script will embed a `DateTimeOriginal` to each frame using the first time and using the specified framerate to offset time value (e.g first frame = earliest time, second frame = earliest time + frame rate, ...)
5. The script will embed global metadata to each frame (e.g. camera make, model, projection...)
6. The script will geotag each frame with GPS co-ordinate (time, latitude, longitude, and altitude)

**Note on GPS extraction**

We use exiftool to extract a gpx file from the video. Exiftool extract a GPX file with timestamps which is then used to geotag extracted frames. [The process is described in more detail in this post](https://www.trekview.org/blog/2020/extracting-gps-track-from-360-timelapse-video/).
The video

We use this approach because exiftool understands the standards for most camera types.

The trade off is that:

1. the GPX track outputted sometimes has a lower resolution of GPS points (sometime video has more gps points than printed in gpx output).
2. it assumers GPS starts from video start time which is not always. For example, the video stated recording, but the gps signal is yet to lock on. If this is suspected, it is better to use `-t timecapture` when running the script (see command line arguments).

### OS Requirements

Works on Windows, Linux and MacOS.

### Software Requirements

* Python version 3.6+
* [exiftool](https://exiftool.org/)
* [ffmpeg](https://www.ffmpeg.org/download.html)
* [Gpxpy](https://pypi.org/project/gpxpy/): python -m pip install gpxpy
* [Pandas](https://pandas.pydata.org/docs/): python -m pip install pandas

### Video Requirements

* Must be a video format understood by ffmpeg and exiftool (`.mp4` recommended)
* Must be [XMP] ProjectionType=equirectangular
* Must have contain a telemetry track with GPS data
	- `GPSLatitude`
	- `GPSLongitude`
	- `GPSAltitude`
	- `GPSDateTime` OR (`GPSDateStamp` AND `GPSTimeStamp`) OR `createDate`

This software will work with most video formats. Whilst it is designed for 360 video files, it will work with traditional flat (Cartesian) videos too.

## Quick start guide

### Command Line Arguments

* `-t`: time (optional: default is timegps)
	- timegps (first `GPSDateTime` of video)
	- timecapture (`CreateDate` of video)
* `-r`: frame rate
	- number of frames per second to extract from video. Must be < 1. (e.g. `-r 0.5` = 1 frame every 2 seconds).

_A note on time. We recommend using `timegps` ([EXIF] `GPSDateTime`) not `timecapture` ([EXIF] `createDate`) unless you are absolutely sure `createDate` is correct. Many 360 stitching tools rewrite `createDate` as datetime of stitching process not the datetime the image was actually captured. This can cause issues when sorting by time (e.g. images might not be stitched in capture order). Therefore, `GPSDateTime` is more likely to represent the true time of capture. [This output shows a good example](https://gitlab.com/snippets/1979531). See all `createDate`'s refer to `2020:04:15 09:14:04` but first `GPSDateTime` is `2020:04:13 15:37:22.444`._


* e: Exif executable path (-e)

* f: FFmpeg executable path (-f)

* r: frame_rates (-r)


### Usage

_Note for Windows users_

It is recommended you place `exiftool.exe` and `ffmpeg.exe` in the script directory.

To do this for exiftool, [download exiftool](https://exiftool.org/), extract the `.zip` file, place `exiftool(-k).exe` in script directory, and rename `exiftool(-k).exe` as `exiftool.exe`

To do this for ffmpeg, [download ffmpeg](https://www.ffmpeg.org/download.html#build-windows), extract the `.zip` file, and place `ffmpeg.exe` in script directory.

If you want to run an existing exiftool install from outside the directory you can also add the path to the exiftool executable on the machine using either `--exiftool-exec-path` or `-e`.

If you want to run an existing ffmpeg install from outside the directory you can also add the path to the exiftool executable on the machine using either `'-f'` or `--ffmpeg-exec-path`.

_Note for MacOS / Unix users_

Remove the double quotes (`"`) around any directory path shown in the examples. For example `"OUTPUT_1"` becomes `OUTPUT_1`.


```
python gf2gv.py -t [TIME] -e [EXIF EXECUTABLE PATH] -f [FFMPEG EXECUTABLE PATH] -r [FRAME_RATE] VIDEO_FILE OUTPUT_FRAME_DIRECTORY
```


```
python gf2gv.py -t timegps -e exiftool.exe -f ffmpeg.exe -r 1 VIDEO_0294.mp4 my_video_frames/
```

**Using a video `"/INPUT/VIDEO_0294.mp4"` extract 1 frame every 5 seconds (`-r 0.2`) using the CreateDate value (`-t timecapture`) for the first image extracted and output all `.jpg` images to the directory `"OUTPUT_2"`**

```
python gf2gv.py -t timecapture -r 0.2 "/INPUT/VIDEO_0294.mp4" "OUTPUT_2"
```

## Support 

We offer community support for all our software on our Campfire forum. [Ask a question or make a suggestion here](https://campfire.trekview.org/c/support/8).

## License

Geovideo to Geoframes is licensed under a [GNU AGPLv3 License](/LICENSE.txt).
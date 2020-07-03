# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Author: hq@trekview.org
# Created: 2020-06-04
# Copyright: Trek View
# Licence: GNU AGPLv3
# -------------------------------------------------------------------------------

import os
import argparse
import pandas as pd
import datetime
from pathlib import Path
import subprocess
import sys
import json
import re
import traceback
import gpxpy


def run_command(*args):
    try:
        out = subprocess.Popen(list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = out.communicate()
        return stdout.decode('utf8')
    except:
        print(traceback.format_exc())
        return ''


def dms2dd(degrees, minutes, seconds, direction):
    dd = float(degrees) + float(minutes)/60 + float(seconds)/(60*60);
    if direction == 'E' or direction == 'N':
        dd *= -1
    return dd


def dd2dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return [d, m, sd]


def parse_dms(dms):
    """
    Parse degrees from dms string.
    """

    parts = re.split('[deg\'"]+', dms)
    lat = dms2dd(parts[0], parts[1], parts[2], parts[3])

    return lat


def get_seconds(time_str):
    """
    Parse time string to seconds
    ex: "00:01:20" -> 50, "20 s" -> 20
    """
    sec_group = re.search(r'(\d+\.?\d*) s', time_str)
    if sec_group:
        res = float(sec_group.group(1))
    else:
        secs = time_str.split(':')
        res = int(secs[0]) * 3600 + int(secs[1]) * 60 + int(secs[2])
    return res


def get_altitude_meters(altitude_str):
    m_group = re.search(r'(\d+\.?\d*)', altitude_str)
    if m_group:
        return float(m_group.group(1))
    return 0.0


def get_video_info(exiftool_executable, input_path):
    """
    Get Video Meta data and detail geo data
    """
    try:
        print('Fetching metadata from video\n')
        video_info_text = run_command(
            exiftool_executable, '-j', '-ee',  '-G3', '-s', '-api', 'largefilesupport=1', input_path)
        video_info = json.loads(video_info_text)[0]
        if video_info.get('Main:ProjectionType') != 'equirectangular':
            raise Exception('Not correct video')
    except:
        return None, None

    # Get the geo data for doc1, doc2, ... with all geo data
    required_values = ['GPSLatitude', 'GPSLongitude', 'GPSAltitude', 'SampleTime', 'GPSDateTime']
    available_keys = re.findall(r'(Doc\d+):GPSLatitude', video_info_text)
    minified_video_info = {
        key: val
        for key, val in video_info.items()
        if not key.startswith('Doc')
    }
    data_list = []
    for k in available_keys:
        item = {}
        try:
            for s_k in required_values:
                key = '{}:{}'.format(k, s_k)
                val = video_info[key]
                if s_k == 'GPSDateTime':
                    date_format = '%Y:%m:%d %H:%M:%S.%f'
                    if 'Z' in val:
                        date_format ='{0}Z'.format(date_format)
                    item[s_k] = datetime.datetime.strptime(val, date_format)
                elif s_k == 'SampleTime':
                    item[s_k] = get_seconds(val)
                elif s_k in ['GPSLatitude', 'GPSLongitude']:
                    item[s_k] = parse_dms(val)
                else:
                    item[s_k] = get_altitude_meters(val)

            data_list.append(item)
        except:
            continue

    df_frames = pd.DataFrame(data_list)
    df_frames.sort_values('SampleTime')
    df_frames.drop_duplicates(subset='SampleTime', inplace=True)

    return minified_video_info, df_frames


def split_video_img(ffmpeg_executable, input_path, output_path, start_secs):
    """
    Split Video from start_secs to start_secs + frame_rates
    """
    res = run_command(ffmpeg_executable, '-ss', str(start_secs), '-i', input_path, '-vframes', '1', output_path)
    return res


def update_splited_video_geo(exiftool_executable, file_path, start_time, frame_start, frame_end, video_info):
    time_key = 'GPSDateTime'
    if frame_start and frame_end:
        frame_start_time = frame_start.get(time_key) if frame_start else None
        frame_end_time = frame_end.get(time_key) if frame_end else None
        if start_time == frame_start.get(time_key):
            geo_data = frame_start
        elif start_time == frame_end.get(time_key):
            geo_data = frame_end
        else:
            calculate_keys = ['GPSLatitude', 'GPSLongitude', 'GPSAltitude']
            start_diff = (start_time - frame_start_time).total_seconds()
            end_diff = (frame_end_time - start_time).total_seconds()
            geo_data = {
                k: frame_start.get(k) + (
                        frame_end.get(k) - frame_start.get(k)) * start_diff / (start_diff + end_diff)
                for k in calculate_keys
            }
            geo_data[time_key] = start_time
    elif frame_start:
        geo_data = frame_start
    else:
        geo_data = frame_end

    res = run_command(
        exiftool_executable,
        '-DateTimeOriginal={0}'.format(start_time.strftime("%Y:%m:%d %H:%M:%S")),
        '-GPSDateStamp={0}'.format(start_time.strftime("%Y:%m:%d")),
        '-GPSTimeStamp={0}'.format(start_time.strftime("%H:%M:%S")),
        '-GPSLatitude={}'.format(geo_data.get('GPSLatitude')),
        '-GPSLatitude={}'.format(geo_data.get('GPSLatitude')),
        '-GPSLongitude={}'.format(geo_data.get('GPSLongitude')),
        '-GPSAltitude={}'.format(geo_data.get('GPSAltitude')),
        '-ProjectionType={}'.format(video_info.get('Main:ProjectionType')),
        '-Make={}'.format(video_info.get('Main:Make'), ''),
        '-Model={}'.format(video_info.get('Main:Model'), ''),
        '-ImageWidth={}'.format(video_info.get('Main:ImageWidth')),
        '-ImageHeight={}'.format(video_info.get('Main:ImageHeight')),
        '-ImageSize={}'.format(video_info.get('Main:ImageSize')),
        '-UsePanoramaViewer=true',
        '-CroppedAreaImageHeightPixels={}'.format(video_info.get('Main:ImageHeight')),
        '-CroppedAreaImageWidthPixels={}'.format(video_info.get('Main:ImageWidth')),
        '-CroppedAreaImageWidthPixels={}'.format(video_info.get('Main:ImageWidth')),
        '-FullPanoHeightPixels={}'.format(video_info.get('Main:ImageHeight')),
        '-FullPanoWidthPixels={}'.format(video_info.get('Main:ImageWidth')),
        '-overwrite_original',
        file_path
    )
    return res, geo_data


def get_dict_from_frame(frame, idx):
    if len(frame.index) > 0:
        selected_frame = frame.iloc[idx]
        return {
            'GPSDateTime': selected_frame.get('GPSDateTime'),
            'GPSLatitude': selected_frame.get('GPSLatitude'),
            'GPSLongitude': selected_frame.get('GPSLongitude'),
            'SampleTime': selected_frame.get('SampleTime'),
            'GPSAltitude': selected_frame.get('GPSAltitude')
        }
    return None


def write_gpx_file(track_logs):
    print('Writing gpx log to log.gpx')
    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    for log in track_logs:
        point = gpxpy.gpx.GPXTrackPoint(
            longitude=log.get('GPSLongitude'),
            latitude=log.get('GPSLatitude'),
            time=log.get('GPSDateTime')
        )
        gpx_segment.points.append(point)

    with open('log.gpx', 'w') as f:
        f.write(gpx.to_xml())


def goevideo_to_geoframes(exiftool_executable, ffmpeg_executable, video_info, df_frames, input_path, output_directory, frame_rates, time_mode):
    duration_secs = get_seconds(video_info.get('Main:MediaDuration'))
    start_secs = 0
    period_start = None
    period_end = None
    time_key = 'SampleTime'
    track_logs = []
    try:
        start_time = df_frames['GPSDateTime'].iloc[0] \
            if time_mode == 'timegps' \
            else datetime.datetime.strptime(video_info.get('Main:CreateDate'), '%Y:%m:%d %H:%M:%S')
    except:
        input('Your time mode is timecapture. But CreateDate is not set')
        exit()
        return

    while True:
        output_path = os.path.join(output_directory, '{}.jpg'.format(
            (start_time + datetime.timedelta(0, start_secs)).strftime('%Y_%m_%d_%H%M%S')))

        ffmpeg_res = split_video_img(ffmpeg_executable, input_path, output_path, start_secs)
        print('Got image from video at {} seconds. Path to file is {}'.format(start_secs, output_path))

        if not period_start or period_start.get(time_key) > start_secs:
            start_frame = df_frames[df_frames[time_key] <= start_secs]
            period_start = get_dict_from_frame(start_frame, len(start_frame.index) - 1)

        if not period_end or period_end.get(time_key) < start_secs:
            end_frame = df_frames[df_frames[time_key] > start_secs]
            period_end = get_dict_from_frame(end_frame, 0)

        print('Start to set the metadata of {}'.format(output_path))
        exif_res, geo_data = update_splited_video_geo(exiftool_executable, output_path, start_time + datetime.timedelta(0, start_secs),
                                 period_start, period_end, video_info)
        track_logs.append(geo_data)
        print('End to set the metadata of {}'.format(output_path))

        if start_secs > duration_secs:
            break
        start_secs += frame_rates

    write_gpx_file(track_logs)


def main_process(args):
    path = Path(__file__)
    time_mode = args.time.lower()
    frame_rate = 0

    if time_mode not in ['timegps', 'timecapture']:
        input("""Time mode should be one of "timegps", "timecapture". \n\nPress any key to quit...""")
        quit()

    try:
        frame_rate = 1 / float(args.frame_rate)
        if frame_rate < 1:
            input("""Frame Rate should less than 1. \n\nPress any key to quit...""")
            quit()
    except:
        input("""Frame Rate is required and should be number. \n\nPress any key to quit...""")
        quit()

    input_path = os.path.abspath(args.input_path)
    if not os.path.isfile(input_path):
        input("""{} file does not exist. \n\nPress any key to quit...""".format(input_path))
        quit()

    is_win_shell = True
    exiftool_executable = 'exiftool'

    if args.exif_path == 'No path specified':
        if 'win' in sys.platform and not 'darwin' in sys.platform:
            if os.path.isfile(os.path.join(path.parent.resolve(), 'exiftool.exe')):
                exiftool_executable = os.path.join(path.parent.resolve(), 'exiftool.exe')
            else:
                input("""Executing this script on Windows requires either the "-e" option
                            or store the exiftool.exe file in the working directory.\n\nPress any key to quit...""")
                quit()
        else:
            is_win_shell = False

    else:
        exiftool_executable = args.exif_path

    ffmpeg_executable = 'ffmpeg'
    if args.ffmpeg_path == 'No path specified':
        if 'win' in sys.platform and not 'darwin' in sys.platform:
            if os.path.isfile(os.path.join(path.parent.resolve(), 'ffmpeg.exe')):
                ffmpeg_executable = os.path.join(path.parent.resolve(), 'ffmpeg.exe')
            else:
                input("""Executing this script on Windows requires either the "-e" option
                            or store the ffmpeg.exe file in the working directory.\n\nPress any key to quit...""")
                quit()
        else:
            is_win_shell = False

    else:
        ffmpeg_executable = args.ffmpeg_path

    output_path = os.path.abspath(args.output_directory)
    # Create destination directory
    if not os.path.isdir(os.path.abspath(output_path)):
        os.mkdir(output_path)

    video_info, df_frames = get_video_info(exiftool_executable, input_path)
    if not video_info:
        input("""Video format is incorrect. \n\nPress any key to quit...""")
        quit()

    goevideo_to_geoframes(exiftool_executable, ffmpeg_executable, video_info, df_frames,
                          input_path, output_path, frame_rate, time_mode)

    input("""Successfully finished. \n\nPress any key to quit...""")
    quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Geovideo to Geoframes')

    parser.add_argument('-e', '--exiftool-exec-path',
                        action='store',
                        default='No path specified',
                        dest='exif_path',
                        help='Optional: path to Exiftool executable.')

    parser.add_argument('-f', '--ffmpeg-exec-path',
                        action='store',
                        default='No path specified',
                        dest='ffmpeg_path',
                        help='Optional: path to ffmpeg executable.')

    parser.add_argument('-t', '--time',
                        action='store',
                        default='timegps',
                        help='"timegps" or "timecapture"')

    parser.add_argument('input_path',
                        action='store',
                        help='Path to input video.')

    parser.add_argument('-r', '--frame-rate',
                        action='store',
                        help='Frame rates it should be less than 1')

    parser.add_argument('output_directory',
                        action="store",
                        help='Path to output folder.')

    parser.add_argument('--version',
                        action='version',
                        version='%(prog)s 1.0')

    input_args = parser.parse_args()

    main_process(input_args)

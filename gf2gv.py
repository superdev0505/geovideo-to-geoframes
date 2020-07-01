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
                    item[s_k] = datetime.datetime.strptime(val, '%Y:%m:%d %H:%M:%S.%fZ')
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


def split_video(ffmpeg_executable, input_path, output_path, start_secs, frame_rates):
    """
    Split Video from start_secs to start_secs + frame_rates
    """
    res = run_command(ffmpeg_executable, '-i', input_path, '-ss', str(start_secs), '-t', str(frame_rates), output_path)
    return res


def update_splited_video_geo(exiftool_executable, file_path, start_time, frame_start, frame_end, time_mode):
    time_key = 'GPSDateTime'
    frame_start_time = frame_start.get(time_key)
    frame_end_time = frame_end.get(time_key)
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

    res = run_command(
        exiftool_executable,
        '-DateTimeOriginal={0}'.format(start_time.strftime("%Y:%m:%d %H:%M:%S")),
        '-GPSDateStamp={0}'.format(start_time.strftime("%Y:%m:%d")),
        '-GPSTimeStamp={0}'.format(start_time.strftime("%H:%M:%S")),
        '-GPSLatitude={}'.format(geo_data.get('GPSLatitude')),
        '-GPSLatitude={}'.format(geo_data.get('GPSLatitude')),
        '-GPSLongitude={}'.format(geo_data.get('GPSLongitude')),
        '-GPSAltitude={}'.format(geo_data.get('GPSAltitude')),
        '-overwrite_original',
        file_path
    )
    return res


def goevideo_to_geoframes(exiftool_executable, ffmpeg_executable, video_info, df_frames, input_path, output_directory, frame_rates, time_mode):
    duration_secs = get_seconds(video_info.get('Main:MediaDuration'))
    start_secs = 0
    period_start = None
    period_end = None
    time_key = 'SampleTime'
    start_time = df_frames['GPSDateTime'].iloc[0]

    while True:
        output_path = os.path.join(output_directory, '{}.{}'.format(
            datetime.datetime.now().strftime('%Y_%m_%d_%H%M%S%f'), video_info.get('Main:FileTypeExtension')))

        print('Start spliting video from {} seconds. Path to file is {}'.format(start_secs, output_path))
        res = split_video(ffmpeg_executable, input_path, output_path, start_secs, frame_rates)
        print('End spliting video to {} seconds. '.format(start_secs + frame_rates))

        if not period_start or period_start.get(time_key) > start_secs:
            start_frame = df_frames[df_frames[time_key] <= start_secs]
            period_start = start_frame.iloc[len(start_frame.index) - 1] if len(start_frame.index) > 0 else None

        if not period_end or period_end.get(time_key) < start_secs:
            end_frame = df_frames[df_frames[time_key] > start_secs]
            period_end = end_frame.iloc[0] if len(end_frame.index) > 0 else None

        print('Start to set the metadata of {}'.format(output_path))
        update_splited_video_geo(exiftool_executable, output_path, start_time + datetime.timedelta(0, start_secs),
                                 period_start, period_end, time_mode)
        print('End to set the metadata of {}'.format(output_path))

        if start_secs > duration_secs:
            break
        start_secs += frame_rates


def main_process(args):
    path = Path(__file__)
    time_mode = args.time.lower()

    if time_mode not in ['timegps', 'timecapture']:
        input("""Time mode should be one of "timegps", "timecapture". \n\nPress any key to quit...""")
        quit()

    try:
        frame_rate = int(args.frame_rate)
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
                        help='Path to input video.')

    parser.add_argument('output_directory',
                        action="store",
                        help='Path to output folder.')

    parser.add_argument('--version',
                        action='version',
                        version='%(prog)s 1.0')

    input_args = parser.parse_args()

    main_process(input_args)

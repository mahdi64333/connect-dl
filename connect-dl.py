import re
import os
from shutil import copy2
import subprocess
from time import time_ns
from pathlib import Path


def time_add_sub(time0, time1, sub=False):
    time0 = list(map(int, time0.split(':')))
    time1 = list(map(int, time1.split(':')))
    time0 = time0[0] * 3600 + time0[1] * 60 + time0[2]
    time1 = time1[0] * 3600 + time1[1] * 60 + time1[2]
    time2 = [0, 0, 0]
    if sub:
        seconds_sum = time0 - time1
    else:
        seconds_sum = time0 + time1
    time2[0] = seconds_sum // 3600
    time2[1] = (seconds_sum % 3600) // 60
    time2[2] = (seconds_sum % 60)
    time2 = list(map(str, time2))
    for part in range(len(time2)):
        if len(time2[part]) < 2:
            time2[part] = '0' + time2[part]

    return(':'.join(time2))


def time_greater_than(time0, time1):
    time0 = list(map(int, time0.split(':')))
    time1 = list(map(int, time1.split(':')))
    time0 = time0[0] * 3600 + time0[1] * 60 + time0[2]
    time1 = time1[0] * 3600 + time1[1] * 60 + time1[2]
    return time0 > time1


def time_get_seconds(time):
    time = list(map(int, time.split(':')))
    return time[0] * 3600 + time[1] * 60 + time[2]


videos = []
audios = []
path = Path(__file__).parent
start_regex = re.compile(r'\d{2}\:\d{2}\:\d{2}')
duration_regex = re.compile(r'(?<=Duration: )\d{2}:\d{2}:\d{2}')
for file in path.iterdir():
    if file.name.startswith('screenshare') and file.name.endswith('.flv'):
        xml_file = open(file.name.replace('.flv', '.xml'))
        try:
            start = start_regex.findall(xml_file.read())[0]
        except IndexError:
            start = time_add_sub(videos[-1][1], videos[-1][2])
        xml_file.close()
        videos.append(
            [file.name.replace('.flv', ''),
             start,
             duration_regex.findall(subprocess.getoutput('ffprobe ' + file.name))[0]])
    if file.name.startswith('cameraVoip') and file.name.endswith('.flv'):
        xml_file = open(file.name.replace('.flv', '.xml'))
        try:
            start = start_regex.findall(xml_file.read())[0]
        except IndexError:
            start = time_add_sub(audios[-1][1], audios[-1][2])
        xml_file.close()
        audios.append(
            [file.name.replace('.flv', ''),
             start,
             duration_regex.findall(subprocess.getoutput('ffprobe ' + file.name))[0]])

workdir = path.joinpath(str(time_ns()))
workdir.mkdir()

start_moment = '99:59:59'
end_moment = '00:00:00'
num = 0
for item in videos:
    os.system('ffmpeg -i "{0}.flv" -vf fps=6 "{1}.mp4"'.format(
        path.joinpath(item[0]), workdir.joinpath(str(num))))
    if num == 0:
        os.system(
            'ffmpeg -i "{0}.mp4" -vf "select=eq(n\,0)" -vframes 1 "{0}f.png"'.format(workdir.joinpath(str(num))))
    os.system(
        'ffmpeg -sseof -1 -i "{0}.mp4" -update 1 -vframes 1 "{0}l.png"'.format(workdir.joinpath(str(num))))
    if time_greater_than(start_moment, item[1]):
        start_moment = item[1]
    if time_greater_than(time_add_sub(item[1], item[2]), end_moment):
        end_moment = time_add_sub(item[1], item[2])
    num += 1
num = 0
for item in audios:
    os.system('ffmpeg -i "{0}.flv" "{1}.mp3"'.format(
        path.joinpath(item[0]), workdir.joinpath(str(num))))
    if time_greater_than(start_moment, item[1]):
        start_moment = item[1]
    if time_greater_than(time_add_sub(item[1], item[2]), end_moment):
        end_moment = time_add_sub(item[1], item[2])
    num += 1

video_count = 0
concat_input = ''
if time_greater_than(videos[0][1], start_moment):
    os.system('ffmpeg -loop 1 -framerate 6 -i "{0}f.png" -c:v libx264 -t {1} "{0}f.mp4"'.format(
        workdir.joinpath('0'), time_get_seconds(time_add_sub(videos[0][1], start_moment, True))))
    concat_input += '-i "' + str(workdir.joinpath('0f.mp4')) + '"'
    video_count += 1

i = 0
while i < len(videos) - 1:
    os.system('ffmpeg -loop 1 -framerate 6 -i "{0}l.png" -c:v libx264 -t {1} "{0}l.mp4"'.format(workdir.joinpath(
        str(i)), time_get_seconds(time_add_sub(videos[i + 1][1], time_add_sub(videos[i][1], videos[i][2]), True))))
    concat_input += ' -i "' + str(workdir.joinpath(str(i) + '.mp4')) + '"'
    if time_greater_than(videos[i + 1][1], time_add_sub(videos[i][1], videos[i][2])):
        concat_input += ' -i "' + str(workdir.joinpath(str(i) + 'l.mp4')) + '"'
        video_count += 1
    video_count += 1
    i += 1

concat_input += ' -i "' + str(workdir.joinpath(str(i) + '.mp4')) + '"'
video_count += 1
if time_greater_than(end_moment, time_add_sub(videos[-1][1], videos[-1][2])):
    os.system('ffmpeg -loop 1 -framerate 6 -i "{0}l.png" -c:v libx264 -t {1} "{0}l.mp4"'.format(workdir.joinpath(
        str(i)), time_get_seconds(time_add_sub(end_moment, time_add_sub(videos[i][1], videos[i][2]), True))))
    concat_input += ' -i "' + str(workdir.joinpath(str(i) + 'l.mp4')) + '"'
    video_count += 1
i += 1

concat_channels = ''
for j in range(video_count):
    concat_channels += '[' + str(j) + ':v]'
os.system('ffmpeg {0} -filter_complex "{1} concat=n={2}:v=1 [outv]" -map "[outv]" "{3}"'.format(
    concat_input, concat_channels, str(video_count), workdir.joinpath('vid.mp4')))

audio_input = ''
audio_map = ''

for i in range(len(audios)):
    audio_input += ' -itsoffset '
    audio_input += str(time_add_sub(audios[i][1], start_moment, True))
    audio_input += ' -i "'
    audio_input += str(workdir.joinpath(str(i)))
    audio_input += '.mp3"'
    audio_map += ' -map {0}:a'.format(i + 1)

os.system('ffmpeg -i "{0}"{1} -filter_complex amix=inputs={2} -map 0:v{3} -c:v copy -c:a aac -async 1 "{4}"'.format(workdir.joinpath('vid.mp4'), audio_input, len(audios), audio_map, path.joinpath(workdir.name + '.mp4')))

for file in workdir.iterdir():
    os.remove(file)

workdir.rmdir()

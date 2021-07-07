#!/usr/bin/python3

import time
import subprocess
import os

def get_actual_video_indexes():
  output = subprocess.check_output('ls /dev/video*', shell=True)
  devs = output.decode().split()
  return devs
  #idxs = [int(x[-1]) for x in devs]
  #return idxs

def get_nontegra_cameras():
  onboard_cam_driver = 'tegra-video'
  nontegra_cameras = []
  idxs = get_actual_video_indexes()
  for idx in idxs:
    #output=subprocess.check_output(['v4l2-ctl', '-d', '/dev/video%d' % idx, '--sleep=0'])
    output=subprocess.check_output(['v4l2-ctl', '-d', idx, '--sleep=0'])
    if onboard_cam_driver not in output.decode():
      nontegra_cameras.append(idx)
  return nontegra_cameras

def run_script():
  idxs = get_nontegra_cameras()
  processes = []
  prefix = ''
  command =  "ffmpeg -hide_banner -loglevel error -nostdin -video_size 640x480 -input_format yuyv422 -i %s -c:v libx264 -preset veryfast -crf 22 -r 15 -f segment -segment_time 3600 -strftime 1 -reset_timestamps 1 '%sdevice%d-%%Y.%%m.%%d.%%H.%%M.mp4'"
  for idx in idxs:
    num = int(idx[-1])
    com = command % (idx,prefix,num)
    print("COMMAND FOR %s: %s" % (idx, com))
    p=subprocess.Popen(com, shell=True)
    processes.append(p)
  for p in processes:
    p.wait()

#let's sleep 60 seconds because of automount issues at boot time
time.sleep(60)
run_script()

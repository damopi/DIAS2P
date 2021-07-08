#!/usr/bin/python3

import time
import subprocess
import os
import datetime

isdaemon = "DAEMONIZE_ME" in os.environ and os.environ["DAEMONIZE_ME"] in ["on", "1", "true"]

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
  timestamp = datetime.datetime.now().strftime("%Y.%m.%d.%H.%M")
  prefix = prefix+timestamp+"/"
  #os.makedirs(prefix, exist_ok=True)
  os.mkdir(prefix)
  command = "gst-launch-1.0 v4l2src device=%s ! 'video/x-raw, width=(int)640, height=(int)480, format=YUY2' ! videoconvert ! 'video/x-raw,format=(string)NV12,width=640,height=480,framerate=(fraction)30/1' ! queue ! x264enc pass=5 quantizer=22 speed-preset=3 ! splitmuxsink max-size-time=60000000000 async-finalize=true location=%sdevice%d_%s_%%05d.mp4"
  #command =  "ffmpeg -hide_banner -loglevel error -nostdin -video_size 640x480 -input_format yuyv422 -i %s -c:v libx264 -preset veryfast -crf 22 -r 15 -f segment -segment_time 60 -strftime 1 -reset_timestamps 1 '%sdevice%d-%%Y.%%m.%%d.%%H.%%M.mp4'"
  for idx in idxs:
    num = int(idx[-1])
    com = command % (idx,prefix,num, timestamp)
    print("COMMAND FOR %s: %s" % (idx, com))
    p=subprocess.Popen(com, shell=True)
    processes.append(p)
  print("All children launched")
  if isdaemon:
    numFiles1 = len(os.listdir(prefix))
    while True:
      time.sleep(600)
      numFiles2 = len(os.listdir(prefix))
      if numFiles1==numFiles2:
        os.system('sudo reboot')
      numFiles1 = numFiles2
  for p in processes:
    print("Start Waiting for one process")
    p.wait()
    print("End Waiting for one process")
  print("Ending script")

#let's sleep 60 seconds because of automount issues at boot time
time.sleep(60)
run_script()

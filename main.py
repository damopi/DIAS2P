#!/usr/bin/python3

import jetson.inference
import jetson.utils
import cv2
import sys
import os
import os.path
import time
from threading import Timer
from utils import utils, classes, gpios, cameras, info, tracking, contour, backend
from trackers.bboxssd import BBox
import platform
import numpy as np
import signal
import datetime

gpio_pin = 18 # this must be in accordance with the physical GPIO pin used in the board
gpio = gpios.PinController(output_pin=gpio_pin)

# check if running on jetson
is_jetson = utils.is_jetson_platform()

def finalize_jetson(sgn, frame):
  gpio.warning_OFF()
  gpio.deactivate_jetson_board()
  print("Ending process because of signal %d" % sgn)
  sys.exit(0)

def finalize_process(sgn, frame):
  print("Ending process because of signal %d" % sgn)
  sys.exit(0)

def make_handler(sgn, is_jetson):
  handler = finalize_jetson if is_jetson else finalize_process
  signal.signal(sgn, handler)

isdaemon = "DAEMONIZE_ME" in os.environ and os.environ["DAEMONIZE_ME"] in ["on", "1", "true"]

if isdaemon:
  import systemd.daemon
  make_handler(signal.SIGABRT, is_jetson)
#else:
#  make_handler(signal.SIGINT, is_jetson)

# do "touch /home/username/Desktop/DIAS2P/gimmeit" to get snapshots from both cameras
saveFilesOnDemand = is_jetson
saveFileThisTime  = False

recordAllFrames = False
prefixFrames = ''
numRecordsToFragment = 5000

recordDetections = False
recordThisTime = False
detectionsLog = prefixFrames+'detections.log'

recordCountsByMinute = True
recordCountsByHour   = True
recordCountsByDay    = True
projName             = "dias2p"
# DO NOT SAVE TO GIT THE CREDENTIALS FILE!!!!!
# THIS FILE WAS GENERATED FROM THIS PAGE: https://console.firebase.google.com/u/1/project/dias2p/settings/serviceaccounts/databasesecrets
credsFile            = 'DIAS2P_credentials.json'
counters             = backend.RecordCounters(
  recordCountsByMinute, recordCountsByHour, recordCountsByDay,
  projName, credsFile)

prefixOneOffSnapshots    = prefixFrames+'snapshot/'
prefixDetectionSnapshots = prefixFrames+'detect/'

useTrackerForWarnings = True

if __name__ == "__main__":

    # ---------------------------------------
    #
    #      PARAMETER INITIALIZATION
    #
    # ---------------------------------------

    # Show live results
    # when production set this to False as it consume resources
    SHOW_IF_NOT_JETSON = False # True
    VIDEO = False
    SHOW_INPUTS_IF_JETSON = True
    # tell the script if it can spawn windows to show images
    RUNNING_ON_DESKTOP = False #True
    # right now, this only works in *NIX, so set to False if you're on Windows/MAC
    CHECK_IF_RUNNING_ON_DESKTOP = False
    # the setup is interactive by default
    INTERACTIVE_SETUP = False #True
    # IF YOU HAVE PROBLEMS OPENING VIDEO, VIDEO DEVICE FILES MIGHT HAVE NONCONVENTIONAL INDEXES!
    # IN THAT CASE, CHECK THE OUTPUT OF ls /dev/video* AND ADJUST THESE INDEXES ACCORDINGLY!!!!
    videoConfig = {
      'nonInteractive':       not INTERACTIVE_SETUP,
      'byIndexRoad':          2,
      'byIndexCrosswalk':     1,
      'byIndexOnboardCamera': 0,
      'tryByPath':            True,
      'byPathRoad':      '/dev/v4l/by-path/platform-3530000.xhci-usb-0:2.3:1.0-video-index0',
      'byPathCrosswalk': '/dev/v4l/by-path/platform-3530000.xhci-usb-0:2.2:1.0-video-index0'
    }
    videoConfig['byIndexAllCams'] = [videoConfig['byIndexOnboardCamera'], videoConfig['byIndexRoad'], videoConfig['byIndexCrosswalk']]

    if not recordDetections:
      recordAllFrames = False
    if recordDetections:
      detectfile = open(detectionsLog, 'at')
      if recordAllFrames:
        currentFile = 0
        currentSubFolder = 0
        currentFolder = 0
        parentFolder = prefixFrames+datetime.datetime.now().strftime("%Y.%m.%d.%H.%M")
        os.mkdir(parentFolder)
        os.mkdir("%s/%04d" % (parentFolder, currentFolder))
        currentFolderStr = "%s/%04d/%04d/" % (parentFolder, currentFolder, currentSubFolder)
        os.mkdir(currentFolderStr)

    # load the object detection network
    accelerated_gstreamer = True
    arch = "ssd-mobilenet-v2"
    overlay = "box,labels,conf"
    threshold = 0.7
    W, H = (640, 480)
    net = jetson.inference.detectNet(arch, sys.argv+["--log-level=error"], threshold)

    if CHECK_IF_RUNNING_ON_DESKTOP:
      RUNNING_ON_DESKTOP = ('DISPLAY' in os.environ) and (os.environ['DISPLAY']!='')
      if not RUNNING_ON_DESKTOP:
        SHOW_INPUTS_IF_JETSON = False
        SHOW_IF_NOT_JETSON = False
        INTERACTIVE_SETUP = False

    # Start printing console
    consoleConfig = info.ConsoleParams()
    consoleConfig.system = platform.system()

    # Get array of classes detected by the net
    classes = classes.classesDict
    # List to filter detections
    pedestrian_classes = [
        "person",
        "bicycle"
    ]
    vehicle_classes = [
        "car",
        "motorcycle",
        "bus",
        "truck",
    ]

    # Initialize Trackers
    ped_tracker = tracking.Tracker(200, 10, 200*100)
    veh_tracker = tracking.Tracker(200, 15, 200*100)
    peds_tracked = tracking.PedestrianTracking()
    vehs_tracked = tracking.VehicleTracking()

    # Activate Board
    if is_jetson: gpio.activate_jetson_board()

    # Initialize Warning scheduler
    DELAY_TIME = 5
    if is_jetson:
        # if in Jetson Platform schedule GPIOs power off
        scheduler = Timer(DELAY_TIME, gpio.warning_OFF, ())
    else:
        # if not Jetson Platform schedule dummy GPIOs power off
        scheduler = Timer(DELAY_TIME, gpio.security_OFF, ())

    # ---------------------------------------
    #
    #      VIDEO CAPTURE INITIALIZATION
    #
    # ---------------------------------------

    VIDEO_PATH = "video/cross_uma_02.webm"
    VIDEO_PATH2 = "video/car_uma_01.webm"

    # Get two Video Input Resources
    # Rather from VIDEO file (testing) or CAMERA file

    if VIDEO:
        print('[*] Starting video...')
        crosswalkCam = cv2.VideoCapture(VIDEO_PATH)
        roadCam = cv2.VideoCapture(VIDEO_PATH2)
        # Override initial width and height
        W = int(crosswalkCam.get(3))  # float
        H = int(crosswalkCam.get(4))  # float

    elif is_jetson and accelerated_gstreamer:
        # If in jetson platform initialize Cameras from CUDA (faster inferences)
        print("Is jetson")
        print('[*] Starting camera...')
        # Select Road and Crosswalk cameras
        road_idx, crosswalk_idx = cameras.get_road_and_crosswalk_devices(videoConfig)
        #print('STARTING CROSSWALK CAMERA')
        crosswalkCam = jetson.utils.gstCamera(W, H, crosswalk_idx)
        #print('STARTING ROAD CAMERA')
        roadCam = jetson.utils.gstCamera(W, H, road_idx)
        #print('FINISHED STARTING CAMERAS')

    else:
        # If NOT in jetson platform initialize Cameras from cv2 (slower inferences)
        # Set video source from camera
        print('[*] Starting camera...')

        # Select Road and Crosswalk cameras
        road_idx, crosswalk_idx = cameras.get_road_and_crosswalk_devices(videoConfig)
        crosswalkCam = cv2.VideoCapture(crosswalk_idx)
        roadCam = cv2.VideoCapture(road_idx)
        # Override initial width and height
        W = int(crosswalkCam.get(3))  # float
        H = int(crosswalkCam.get(4))  # float

    # Get ROIs from cross and road cam
    crossContourUp   = contour.select_points_in_frame(crosswalkCam, 'crossContourUp',   is_jetson=is_jetson, is_interactive=INTERACTIVE_SETUP)
    crossContourDown = contour.select_points_in_frame(crosswalkCam, 'crossContourDown', is_jetson=is_jetson, is_interactive=INTERACTIVE_SETUP)
    roadContour      = contour.select_points_in_frame(     roadCam, 'roadContour',      is_jetson=is_jetson, is_interactive=INTERACTIVE_SETUP,
point_nb=6)

    # ---------------------------------------
    #
    #      VIDEO PROCESSING MAIN LOOP
    #
    # ---------------------------------------

    if isdaemon:
      systemd.daemon.notify('READY=1')
      timestart = datetime.datetime.now()
      minute_count = -1

    while True:

        start_time = time.time()  # start time of the loop

        if saveFilesOnDemand and os.path.isfile('gimmeit'):
          try:
            os.remove('gimmeit')
          except:
            pass
          saveFileThisTime = True


        # ---------------------------------------
        #
        #              DETECTION
        #
        # ---------------------------------------

        # if we are on Jetson use jetson inference
        if is_jetson:
            doZeroCopy = recordDetections or SHOW_INPUTS_IF_JETSON or saveFileThisTime
            # get frame from crosswalk and detect
            #print('CAPTURING SNAPSHOT FROM CROSSWALK CAMERA')
            crosswalkMalloc, _, _ = crosswalkCam.CaptureRGBA(zeroCopy=doZeroCopy)
            # get frame from road and detect
            #print('CAPTURING SNAPSHOT FROM ROAD CAMERA')
            roadMalloc, _, _ = roadCam.CaptureRGBA(zeroCopy=doZeroCopy)
            #print('FINISHED CAPTURING SNAPSHOTS')

            if doZeroCopy:
                jetson.utils.cudaDeviceSynchronize()
                crosswalk_numpy_img = jetson.utils.cudaToNumpy(crosswalkMalloc, W, H, 4)
                road_numpy_img = jetson.utils.cudaToNumpy(roadMalloc, W, H, 4)
                crosswalk_numpy_img = cv2.cvtColor(crosswalk_numpy_img.astype(np.uint8), cv2.COLOR_RGBA2BGR)
                road_numpy_img = cv2.cvtColor(road_numpy_img.astype(np.uint8), cv2.COLOR_RGBA2BGR)
                # show images here only for debug purposes
                #if SHOW_INPUTS_IF_JETSON:
                #  cv2.imshow("crosswalk", crosswalk_numpy_img)
                #  cv2.imshow("road", road_numpy_img)
                if saveFileThisTime:
                  saveFileThisTime = False
                  stamp = datetime.datetime.now().strftime("%Y.%m.%d.%H.%M")
                  cv2.imwrite('%scrosswalk.%s.jpg' % (prefixOneOffSnapshots, stamp), crosswalk_numpy_img)
                  cv2.imwrite('%sroad.%s.jpg'      % (prefixOneOffSnapshots, stamp), road_numpy_img)

            #print('DETECTING PEDESTRIANS')
            pedestrianDetections = net.Detect(crosswalkMalloc, W, H, overlay)
            #print('DETECTING VEHICLES')
            vehicleDetections = net.Detect(roadMalloc, W, H, overlay)
            #print('FINISHED DETECTING VEHICLES')

        # If we are NOT on jetson use CV2
        else:
            # Check if more frames are available
            if crosswalkCam.grab() and roadCam.grab():
                # capture the image
                _, crosswalkFrame = crosswalkCam.read()
                _, roadFrame = roadCam.read()
            else:
                print("no more frames")
                break

            # Synchronize system
            jetson.utils.cudaDeviceSynchronize()

            # Get Cuda Malloc to be used by the net
            # Get processes frame to fit Cuda Malloc Size
            crosswalkFrame, crosswalkMalloc = utils.frameToCuda(crosswalkFrame, W, H)
            roadFrame, roadMalloc = utils.frameToCuda(roadFrame, W, H)

            # Get detections Detectnet.Detection Object
            pedestrianDetections = net.Detect(crosswalkMalloc, W, H, overlay)
            vehicleDetections = net.Detect(roadMalloc, W, H, overlay)

        # ---------------------------------------
        #
        #               TRACKING
        #
        # ---------------------------------------

        # Initialize bounding boxes lists
        ped_up_bboxes = []
        ped_down_bboxes = []
        veh_bboxes = []
        ped_up_idxs = []
        ped_down_idxs = []
        veh_idxs = []

        # Convert Crosswalk Detections to Bbox object
        # filter detections if recognised as pedestrians
        # add to pedestrian list of bboxes
        ped_idx = 0
        for detection in pedestrianDetections:
            bbox = BBox(detection)
            if bbox.name in pedestrian_classes:
                recordThisTime = recordDetections
                if tracking.is_point_in_contour(crossContourUp, bbox.center):
                    ped_up_bboxes.append(bbox)
                    ped_up_idxs.append(ped_idx)
                if tracking.is_point_in_contour(crossContourDown, bbox.center):
                    ped_down_bboxes.append(bbox)
                    ped_down_idxs.append(ped_idx)
            ped_idx += 1

        # Convert Road Detections to Bbox object
        # filter detections if recognised as vehicles
        # add to vehicle list of bboxes
        vec_idx = 0
        for detection in vehicleDetections:
            bbox = BBox(detection)
            is_bbox_in_contour = tracking.is_point_in_contour(roadContour, bbox.center)
            if bbox.name in vehicle_classes and is_bbox_in_contour:
                recordThisTime = recordDetections
                veh_bboxes.append(bbox)
                veh_idxs.append(vec_idx)
            vec_idx += 1


        if recordThisTime or recordAllFrames:
          detectTimestamp = datetime.datetime.now().strftime("%Y.%m.%d.%H.%M.%S.%f")
        if recordAllFrames:
          cv2.imwrite('%scrosswalk.%s.jpg' % (currentFolderStr, detectTimestamp), crosswalk_numpy_img)
          cv2.imwrite('%sroad.%s.jpg' % (currentFolderStr, detectTimestamp), road_numpy_img)
          currentFile += 1
          if currentFile >= numRecordsToFragment:
            currentFile = 0
            currentSubFolder += 1
            if currentSubFolder >= numRecordsToFragment:
              currentSubFolder = 0
              currentFolder += 1
              os.mkdir("%s/%04d" % (parentFolder, currentFolder))
            currentFolderStr = "%s/%04d/%04d/" % (parentFolder, currentFolder, currentSubFolder)
            os.mkdir(currentFolderStr)
        if recordThisTime and not recordAllFrames:
          cv2.imwrite('%sdetect.crosswalk.%s.jpg' % (prefixDetectionSnapshots, detectTimestamp), crosswalk_numpy_img)
          cv2.imwrite('%sdetect.road.%s.jpg'      % (prefixDetectionSnapshots, detectTimestamp), road_numpy_img)
        if recordThisTime:
          detectfile.write("\n----------\n-- RAW DETECTIONS AT %s: %d pedestrians, %d vehicles\n" % (detectTimestamp, len(pedestrianDetections), len(vehicleDetections)))
          for d in pedestrianDetections:
            detectfile.write("%s\n" % str(d))
          for d in vehicleDetections:
            detectfile.write("%s\n" % str(d))
          try:
            detectfile.write("-- PED UP   (INDEXES IN PEDESTRIAN DETECTIONS): %s\n" % str(ped_up_idxs))
            detectfile.write("-- PED DOWN (INDEXES IN PEDESTRIAN DETECTIONS): %s\n" % str(ped_down_idxs))
            detectfile.write("-- VEH      (INDEXES IN PEDESTRIAN DETECTIONS): %s\n" % str(veh_idxs))
          except:
            pass

        # Relate previous detections to new ones
        # updating trackers
        vehicle_idxs, removed_vehicle_idxs       = veh_tracker.assign_incomming_positions(np.array([x.center for x in veh_bboxes]))
        pedestrian_idxs, removed_pedestrian_idxs = ped_tracker.assign_incomming_positions(np.array([x.center for x in ped_up_bboxes + ped_down_bboxes]))
        # going_up, going_down is to keep track of pedestrians who have been detected to cross the crosswalk
        going_up, going_down = peds_tracked.update_pos(removed_pedestrian_idxs, pedestrian_idxs[:len(ped_up_bboxes)], ped_up_bboxes, pedestrian_idxs[len(ped_up_bboxes):], ped_down_bboxes)
        new_vehicle_idxs     = vehs_tracked.update_pos(removed_vehicle_idxs, vehicle_idxs, veh_bboxes)

        # count vehicles and pedestrian and post regular counts to the backend
        counters.add(new_vehicle_idxs, going_up, going_down)

        # ---------------------------------------
        #
        #         MANAGING SECURITY
        #
        # ---------------------------------------

        if useTrackerForWarnings:
          activateWarnings = vehs_tracked.any_currently_tracked() and peds_tracked.any_currently_tracked()
        else:
          activateWarnings = veh_bboxes and (ped_up_bboxes or ped_down_bboxes)

        if activateWarnings:
            # Security actions Here
            if is_jetson:
                # Activate Warnings
                gpio.warning_ON()
                print("ACTIVATE WARNINGS!!!!!")
                if recordDetections:
                  recordThisTime = True
                  detectfile.write("\n  -- WARNING ACTIVATED!!!!  --\n")
                # Deactivate Warnings after DELAY_TIME
                scheduler.cancel()
                scheduler = Timer(DELAY_TIME, gpio.warning_OFF, ())
                scheduler.start()

            else:

                # Deactivate Warnings after DELAY_TIME
                scheduler.cancel()  # Cancel every possible Scheduler Thread
                scheduler = Timer(DELAY_TIME, gpio.security_OFF, ())  # Restart
                scheduler.start()

        if recordThisTime:
          recordThisTime = False
          detectfile.flush()
        # ---------------------------------------
        #
        #           SHOWING PROGRAM INFO
        #
        # ---------------------------------------

        consoleConfig.fps = 1.0 / (time.time() - start_time)
        consoleConfig.warnings = scheduler.is_alive()  # if True warnings are still ON

        if (not accelerated_gstreamer or doZeroCopy) and SHOW_INPUTS_IF_JETSON:
            contour.drawContour(road_numpy_img, roadContour)
            contour.drawContour(crosswalk_numpy_img, crossContourUp)
            contour.drawContour(crosswalk_numpy_img, crossContourDown)
            if useTrackerForWarnings:
              crosswalk_numpy_img = info.print_items_to_frame(crosswalk_numpy_img, peds_tracked.get_tracked_bboxes())
              road_numpy_img      = info.print_items_to_frame(road_numpy_img, vehs_tracked.get_tracked_bboxes())
            else:
              crosswalk_numpy_img = info.print_bboxes_to_frame(crosswalk_numpy_img, ped_up_bboxes)
              crosswalk_numpy_img = info.print_bboxes_to_frame(crosswalk_numpy_img, ped_down_bboxes)
              road_numpy_img      = info.print_bboxes_to_frame(road_numpy_img, veh_bboxes)
            cv2.imshow("crosswalk", crosswalk_numpy_img)
            cv2.imshow("road", road_numpy_img)

        # ----------------------------------
        #
        #           PROGRAM END
        #
        # ----------------------------------

        if isdaemon:
          time_delta = datetime.datetime.now() - timestart
          #print(time_delta)
          systemd.daemon.notify('WATCHDOG=1')
          delta_minutes = time_delta.seconds // 60
          if delta_minutes!=minute_count:
            info.print_console(consoleConfig)
            minute_count = delta_minutes
        else:
          # SHOW DATA IN CONSOLE
          info.print_console(consoleConfig)
          # Quit program pressing 'q'
          key = cv2.waitKey(1) & 0xFF
          if key == ord("q"):
              if recordDetections:
                detectfile.close()
              # free GPIOs before quit
              if is_jetson:
                  gpio.warning_OFF()
                  gpio.deactivate_jetson_board()
              # close any open windows
              cv2.destroyAllWindows()
              break

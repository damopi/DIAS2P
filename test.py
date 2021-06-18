import jetson.inference
import jetson.utils
import cv2
import sys
import time
from threading import Timer
import platform
import curses
import numpy as np


if __name__ == "__main__":
    W, H = (640, 480)
    cam1 = jetson.utils.gstCamera(W, H, "/dev/video0")
    imgFromCamera, width, height = cam1.CaptureRGBA(zeroCopy=1)
    jetson.utils.cudaDeviceSynchronize()
    img = jetson.utils.cudaToNumpy(imgFromCamera, width, height, 4)
    print(img)
    img = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGBA2BGR)
    cv2.imshow("image", img)
    cv2.waitKey(0)
    print(img)

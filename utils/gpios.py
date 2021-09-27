#!/usr/bin/env python3

from utils.utils import is_jetson_platform
import time

if is_jetson_platform():
    # if loading this fails, try this (or equivalent) before launching python:
    #     export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1
    import Jetson.GPIO as GPIO  # prevents GPIO to be imported on non jetson devices


class PinController:
  def __init__(self, output_pin=18):
    self.output_pin = output_pin

  def activate_jetson_board(self):

    """
    Activates jetson GPIO 18
    """

    # Board pin-numbering scheme
    GPIO.setmode(GPIO.BCM)
    # set pin as an output pin with optional initial state of LOW
    GPIO.setup(self.output_pin, GPIO.OUT, initial=GPIO.LOW)


  def deactivate_jetson_board(self):

    """
    deactivates jetson GPIOs
    """

    GPIO.cleanup()


  def security_OFF(self):
    """
    dummy function mimic GPIO OFF in Jetson devices
    """
    # print("SECURITY OFF")
    pass


  def security_ON(self):
    """
    dummy function mimic GPIO ON in Jetson devices
    """
    # print("SECURITY ON")
    pass


  def warning_ON(self):

    """
    turns selected GPIO ON
    :param output_pin: int, GPIO position
    """

    print("WARNING GOING ON")
    GPIO.output(self.output_pin, GPIO.HIGH)


  def warning_OFF(self):

    """
    turns selected GPIO OFF
    :param output_pin: int, GPIO position
    """

    print("WARNING GOING OFF")
    GPIO.output(self.output_pin, GPIO.LOW)


if __name__ == '__main__':

    """
    Quick check of GPIO 18
    """

    controller = PinController()
    controller.activate_jetson_board()
    try:
        while True:
            print('warnings activated')
            controller.warning_ON()
            time.sleep(2)
            print('warnings OFF')
            controller.warning_OFF()
            time.sleep(2)
    finally:
        controller.deactivate_jetson_board()


def testit(output_pin, tsleep):
  p = PinController(output_pin=output_pin)
  p.activate_jetson_board()
  p.warning_ON()
  time.sleep(tsleep)
  p.warning_OFF()
  p.deactivate_jetson_board()



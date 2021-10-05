from utils import classes
from collections import deque


class BBox:

        def __init__(self, detection):

                self.detection = detection
                self.name = classes.classesDict[detection.ClassID]
                self.start_point = (int(detection.Left), int(detection.Top))
                self.end_point = (int(detection.Right), int(detection.Bottom))
                self.center = tuple(map(int, detection.Center))

                # Colors for known classes
                self.colors = {
                        'person': (255, 0, 0),
                        'car': (0, 255, 0),
                        'bicycle': (0, 0, 255),
                        'motorcycle': (255, 255, 0),
                        'bus': (0, 255, 255),
                        'truck': (255, 0, 255),
                        'unknown': (255, 255, 255)
                }

                # Set color only to known classes
                self.color = self.colors[self.name] if self.name in self.colors.keys() else self.colors['unknown']










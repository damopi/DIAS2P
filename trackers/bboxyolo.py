from collections import deque
from utils import classes_yolo

class BBox_yolo:

        def __init__(self, detection):

                self.detection=detection
                self.name = classes_yolo.classesDict[int(detection[1])]
                self.start_point = (int(detection[0][0]), int(detection[0][1]))
                self.end_point = (int(detection[0][2]), int(detection[0][3]))
                self.center = tuple(round(sum(x)/2) for x in zip(self.start_point, self.end_point))

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
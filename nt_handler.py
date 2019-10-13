from datetime import datetime

from networktables import NetworkTables
from grip import GripPipeline
import cv2
from threading import Thread
import subprocess

im = None
capturing = True

WIDTH = 320
HEIGHT = 180


def update_image():
    global im
    global capturing
    nt = NetworkTables.getTable("ImageProcessing")
    last_id = cam_id = int(nt.getNumber("currentCamera", defaultValue=0))
    cam = create_camera(cam_id)
    try:
        while capturing:
            cam_id = int(nt.getNumber("currentCamera", defaultValue=0))
            if last_id != cam_id:
                cam.release()
                cam = create_camera(cam_id)
            last_id = cam_id
            success, im = cam.read()
    finally:
        cam.release()
        print("Thread's done!")


def set_camera_exposure(camera_id: int, exposure: int) -> int:
    return subprocess.call("v4l2-ctl --device=/dev/video{} -c exposure_auto=1 exposure_absolute={}"
                           .format(camera_id, exposure))

def create_camera(cam_id: int) -> cv2.VideoCapture:
    cam = cv2.VideoCapture(cam_id)
    set_camera_resolution(cam, WIDTH, HEIGHT)
    return cam

def set_camera_resolution(camera: cv2.VideoCapture, width: int, height: int):
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)


if __name__ == "__main__":
    print("Starting Vision Script")
    NetworkTables.initialize("10.22.12.2")  # The ip of the roboRIO
    print("Successfully Connected To roboRIO")
    if set_camera_exposure(0, 5) == 0:
        print("Exposure Was Successfully Set For /dev/video0")
    if set_camera_exposure(1, 5) == 0:
        print("Exposure Was Successfully Set For /dev/video1")

    t = Thread(target=update_image)
    t.start()
    pipeline = GripPipeline()
    networkTableImageProcessing = NetworkTables.getTable("ImageProcessing")
    contour_count = 2
    try:
        while im == None or not NetworkTables.isConnected():
            pass
            print("NT connection: %r" % NetworkTables.isConnected())
        [networkTableImageProcessing.delete(s) for s in networkTableImageProcessing.getKeys()]
        while True:
            print("Processing...")
            pipeline.process(im)
            contours = sorted(pipeline.convex_hulls_output, key=cv2.contourArea, reverse=True)
            contour_count = max(contour_count, len(contours))
            #            print "contours: ", len(contours)
            for i, c in enumerate(contours):
                networkTableImageProcessing.putNumber('contourArea%d' % i, cv2.contourArea(c))
                print('contourArea%d' % i, cv2.contourArea(c))
                x, y, w, h = cv2.boundingRect(c)
                networkTableImageProcessing.putNumber('width%d' % i, w)
                # print 'width%d' % i, w
                networkTableImageProcessing.putNumber('height%d' % i, h)  # CR: typo lol
                # print 'height%d' % i, h
                networkTableImageProcessing.putNumber('x%d' % i, x)
                # print 'x%d' % i, x
                networkTableImageProcessing.putNumber('y%d' % i, y)
                # print 'y%d' % i, y
                networkTableImageProcessing.putBoolean('isUpdated%d' % i, True)
                print("isUpdated%d" % i, True)
            for i in range(len(contours), contour_count):
                networkTableImageProcessing.putBoolean('isUpdated%d' % i, False)
    finally:
        capturing = False
        print("Job's done!")

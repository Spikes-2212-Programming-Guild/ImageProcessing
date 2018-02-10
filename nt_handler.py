from datetime import datetime

from networktables import NetworkTable
from grip import GripPipeline
import cv2
from threading import Thread
from os import system

im = None
capturing = True


def update_image():
    global im
    global capturing
    nt = NetworkTable.getTable("ImageProcessing")
    last_id = cam_id = int(nt.getNumber("currentCamera", defaultValue=0))
    cam = cv2.VideoCapture(cam_id)
    try:
        while capturing:
            cam_id = int(nt.getNumber("currentCamera", defaultValue=0))
            if last_id != cam_id:
                cam.release()
                cam = cv2.VideoCapture(cam_id)
            last_id = cam_id
            success, im = cam.read()
    finally:
        cam.release()
        print "Thread's done!"


if __name__ == "__main__":
    print "Starting"
    system("v4l2-ctl --device=/dev/video0 -c exposure_auto=1 -c exposure_absolute=5")
    system("v4l2-ctl --device=/dev/video1 -c exposure_auto=1 -c exposure_absolute=5")
    NetworkTable.setClientMode()
    NetworkTable.setIPAddress("10.22.12.2") # The ip of the roboRIO
    NetworkTable.initialize()
    t = Thread(target=update_image)
    t.start()
    pipeline = GripPipeline()
    networkTableImageProcessing = NetworkTable.getTable("ImageProcessing")
    contour_count = 2
    try:
        while im == None or not networkTableImageProcessing.isConnected():
            pass
	    print "NT connection: %r" %networkTableImageProcessing.isConnected()
        [networkTableImageProcessing.delete(s) for s in networkTableImageProcessing.getKeys()]
        while True:
            print "Processing..."
            pipeline.process(im)
            contours = sorted(pipeline.filter_contours_output, key=cv2.contourArea, reverse=True)
            contour_count = max(contour_count, len(contours))
#            print "contours: ", len(contours)
            for i, c in enumerate(contours):
                networkTableImageProcessing.putNumber('contourArea%d' % i, cv2.contourArea(c))
                print 'contourArea%d' % i, cv2.contourArea(c)
                x, y, w, h = cv2.boundingRect(c)
                networkTableImageProcessing.putNumber('width%d' % i, w)
                # print 'width%d' % i, w
                networkTableImageProcessing.putNumber('hight%d' % i, h)  # CR: typo lol
                # print 'height%d' % i, h
                networkTableImageProcessing.putNumber('x%d' % i, x)
                # print 'x%d' % i, x
                networkTableImageProcessing.putNumber('y%d' % i, y)
                # print 'y%d' % i, y
                networkTableImageProcessing.putBoolean('isUpdated%d' % i, True)
                print "isUpdated%d" % i, True
            for i in range(len(contours), contour_count):
                networkTableImageProcessing.putBoolean('isUpdated%d' % i, False)
    finally:
        capturing = False
        print "Job's done!"
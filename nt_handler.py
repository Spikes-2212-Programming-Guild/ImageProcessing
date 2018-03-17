from datetime import datetime

from networktables import NetworkTables
import cv2
import reflectives_pipeline
import powercube_pipeline
from threading import Thread
from subprocess import call

im = None
capturing = True
pipeline = None
nt = None
cam_id = 0


def set_exposure_for_cameras(exposure, *ids):
    for camera_id in ids:
        call('v4l2-ctl --device=/dev/video{} -c exposure_auto=1 -c exposure_absolute={}'.format(camera_id, exposure),
             shell=True)


def init_nt():
    global nt
    nt = NetworkTables.getTable("ImageProcessing")


def update_pipeline():
    global capturing
    global nt
    global pipeline
    global cam_id
    last_name = ""
    pipe_name = nt.getString("pipelineName", defaultValue="power-cube")
    try:
        while capturing:
            pipe_name = nt.getString("pipelineName", defaultValue="power-cube")
            print "pipeline name is " + pipe_name
            if pipe_name is not last_name:
                if pipe_name == "ref":
                    print "switching to reflective"
                    pipeline = reflectives_pipeline.GripPipeline()
                    set_exposure_for_cameras(5, cam_id)
                if pipe_name == "power-cube":
                    print "switching to power cube"
                    pipeline = powercube_pipeline.GripPipeline()
                    set_exposure_for_cameras(9, cam_id)

            last_name = pipe_name
    finally:
        print('Update pipeline is done')


def update_image():
    global im
    global capturing
    global nt
    global cam_id
    last_id = cam_id = int(nt.getNumber("currentCamera", defaultValue=0))
    cam = cv2.VideoCapture(cam_id)
    print "cam id is " + str(cam_id)
    try:
        while capturing:
            try:
                # print "capturing image"
                cam_id = int(nt.getNumber("currentCamera", defaultValue=0))
                if last_id != cam_id:
                    cam.release()
                    cam = cv2.VideoCapture(cam_id)
                last_id = cam_id
                success, im = cam.read()
            except Exception:
                print "Exception"
                continue
    finally:
        cam.release()
        print "Update Image Is Done"


if __name__ == "__main__":
    print "Starting"
    set_exposure_for_cameras(5, 0, 1)
    NetworkTables.initialize("10.22.12.2")  # The ip of the roboRIO
    init_nt()
    t_update_image = Thread(target=update_image)
    t_update_image.start()
    # init_nt()
    t_update_pipeline = Thread(target=update_pipeline)
    t_update_pipeline.start()
    contour_count = 2
    try:
        while im == None or not NetworkTables.isConnected():
            pass
            #        print "NT connection: %r" % NetworkTables.isConnected()
        [nt.delete(s) for s in nt.getKeys()]
        print "starting processing"
        while True:
            # print "Processing..."
            if pipeline is not None:
                print "has pipeline"
                try:
                    pipeline.process(im)
                    contours = sorted(pipeline.filter_contours_output, key=cv2.contourArea, reverse=True)
                    contour_count = max(contour_count, len(contours))
                    # print "contours: ", len(contours)
                    for i, c in enumerate(contours):
                        nt.putNumber('contourArea%d' % i, cv2.contourArea(c))
                        print 'contourArea%d' % i, cv2.contourArea(c)
                        x, y, w, h = cv2.boundingRect(c)
                        nt.putNumber('width%d' % i, w)
                        # print 'width%d' % i, w
                        nt.putNumber('hight%d' % i, h)  # CR: typo lol
                        #	 print 'height%d' % i, h
                        nt.putNumber('x%d' % i, x)
                        # print 'x%d' % i, x
                        nt.putNumber('y%d' % i, y)
                        # print 'y%d' % i, y
                        nt.putBoolean('isUpdated%d' % i, True)
                        nt.putNumber('numberOfContours', len(contours))
                        print "isUpdated%d" % i, True
                    for i in range(len(contours), contour_count):
                        nt.putBoolean('isUpdated%d' % i, False)
                except Exception:
                    continue
    finally:
        capturing = False
        print "Job's done!"

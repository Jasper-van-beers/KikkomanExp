#========================= IMPORTS =========================#
# External libraries
from psychopy import core, visual, event, logging
from pylsl import StreamInfo, StreamOutlet
import os
import glob
import numpy as np

#========================= DEFINITIONS =========================#

def GetRefreshRateWindows():
    import win32api
    device = win32api.EnumDisplayDevices()
    settings = win32api.EnumDisplaySettings(device.DeviceName, -1)
    return getattr(settings, 'DisplayFrequency')


def GetImages(FolderPath):
    imgs_path = glob.glob(FolderPath)
    return imgs_path


def ShowImage(Window, ImagePath, RefreshRate, Duration, ImScale = (1, 1)):
    Image = visual.ImageStim(Window, image = ImagePath, size = ImScale)
    Frames = int(RefreshRate*Duration)
    for frame in range(Frames):
        Image.draw()
        Window.flip()
        pass


def ShowText(Window, Text, RefreshRate, Duration):
    Frames = int(RefreshRate*Duration)
    Stim = visual.TextStim(Window, text=Text)
    for frame in range(Frames):
        Stim.draw()
        Window.flip()
        pass

def ShowMovie(Window, MoviePath):
    Movie = visual.MovieStim3(Window, MoviePath, flipVert=False)
    while Movie.status != visual.FINISHED:
        Movie.draw()
        Window.flip()
        pass


def FrameWait(Window, RefreshRate, Duration):
    Frames = int(RefreshRate*Duration)
    for frame in range(Frames):
        Window.flip()


#========================= PROGRAM =========================#
# # Easiest timing to implement is core.wait(t), but least accurate
# # Can use core.Clock() which can be accurate to 1ms, but it excutes with code order, irrespective
# # of Frame Rate. Therefore, timings are precise to the nearest frame, but can be inconsistent
# # The most consistent and accurate way to measure time is then to tie the timings to the frame rate
# # However, this assumes that no frames will be dropped, as this will affect the timing.
# # NOTE: Some GPUs (esp. integrated) do not support frame syncing
# # We can detect dropped frames following:
# #   https://www.psychopy.org/general/timing/detectingFrameDrops.html

# Some examples for PyLSL: 
# https://github.com/labstreaminglayer/liblsl-Python/blob/master/pylsl/examples

RefreshRate = GetRefreshRateWindows() # FPS

Images = GetImages("{}/Images/*.jpg".format(os.getcwd()))

markers = {'Test' : [0],
           'Text' : [1],
           'Image' : [2],
           'Video' : [3]}

# counter = np.max(list(markers.values()))
# # Add image markers
# for i in range(len(Images)):
#     markers.update({'Image_{}'.format(i):counter})
#     counter += 1

# Initialize LSL stream
<<<<<<< HEAD
info = StreamInfo(name='LSL_Stream', type = 'Markers', channel_count = 1,
=======
info = StreamInfo(name='Stream', type = 'Markers', channel_count = 1, 
>>>>>>> 8256bfab4b09497b0d4a7567b4265e24af557c7e
                  channel_format='int32', source_id='LSL_Stream_001')
outlet = StreamOutlet(info)

# Test comms
for _ in range(4):
    outlet.push_sample(markers['Test'])
    core.wait(0.5)

Win = visual.Window(size=(800, 600))

Win.recordFrameIntervals = True

Win.refreshThreshold = 1/RefreshRate + 0.1/1000.

logging.console.setLevel(logging.WARNING)

for Image in Images[0:3]:
    outlet.push_sample(markers['Image'])
    ShowImage(Win, Image, RefreshRate, 2)
    outlet.push_sample(markers['Text'])
    ShowText(Win, 'Wait for next image', RefreshRate, 1)

Movies = GetImages("{}/Movies/*.mp4".format(os.getcwd()))

for Movie in Movies:
    outlet.push_sample(markers['Video'])
    ShowMovie(Win, Movie)

Win.close()
# core.quit()

print('Dropped Frames were {}'.format(Win.nDroppedFrames))


# gabor = visual.GratingStim(Win, tex='sin', mask='gauss', sf=5,
#     name='gabor', autoLog=False)
# fixation = visual.GratingStim(Win, tex=None, mask='gauss', sf=0, size=0.02,
#     name='fixation', autoLog=False)

# ExpTime = 5 # Seconds

# for frameN in range(int(ExpTime*RefreshRate)):
#     if int(RefreshRate*1) <= frameN < int(RefreshRate*4):  # Present fixation for a subset of frames
#         fixation.draw()
#     if int(RefreshRate*2) <= frameN < int(RefreshRate*3):  # Present stim for a different subset
#         gabor.phase += 0.1  # Increment by 10th of cycle
#         gabor.draw()
#     Win.flip()

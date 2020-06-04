#========================= IMPORTS =========================#
# External libraries
from psychopy import core, visual, event, logging
import os
import glob


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

RefreshRate = GetRefreshRateWindows() # FPS

Win = visual.Window(size=(800, 600))

Win.recordFrameIntervals = True

Win.refreshThreshold = 1/RefreshRate + 0.1/1000.

logging.console.setLevel(logging.WARNING)

Images = GetImages("{}/Images/*.jpg".format(os.getcwd()))

for Image in Images:
    ShowImage(Win, Image, RefreshRate, 2)
    ShowText(Win, 'Wait for next image', RefreshRate, 1)

print('Dropped Frames were {}'.format(Win.nDroppedFrames))

Win.close()

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
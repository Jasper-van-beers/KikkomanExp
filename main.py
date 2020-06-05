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


# Should record participant condition as well
# -> In 'engaged' or 'disenganged'
#    -> Should this be done a priori? 
#    -> If total amount of participants known
#       -> I can make a script which pre-assigns participants'
#          group, based on their participant ID
def GetParticipantInfo(List_of_completed_participants):
    ExistingIDs = np.genfromtxt(List_of_completed_participants, comments='#')
    if ExistingIDs.size > 1:
        ParticipantID = int(ExistingIDs[-1] + 1)
    else:
        ParticipantID = 1
    
    return ParticipantID


def RecordParticipantIDs(List_of_completed_participants, ParticipantID):
    filename = List_of_completed_participants.split('\\')[-1]
    ExistingIDs = np.genfromtxt(List_of_completed_participants, comments='#')
    if ExistingIDs.size > 1:
        ExistingIDs = np.append(ExistingIDs, ParticipantID)
    else:
        ExistingIDs = np.array([0, ParticipantID])
    ExistingIDs = ExistingIDs.astype(int)
    np.savetxt(filename, ExistingIDs, fmt='%i')
    return None


def GetImages(FolderPath):
    imgs_path = glob.glob(FolderPath)
    return imgs_path


# Assume ImageList contains lists of images of each stimulus category
# Each index in ImageList corresponds to a different stimulus category
# For each category, there is a list of images (more precisely, filepaths
# to images) which will be first randomized. 
def RandomizeImageOrder(ImageList, seed = 0):
    RandImageList = []
    RandomizedImageOrder = []
    np.random.seed(seed)
    # Randomize Image order within each category
    for Images in ImageList:
        N = len(Images)
        RandImageIndices = np.arange(0, N, 1)
        np.random.shuffle(RandImageIndices)
        RandImages = [Images[i] for i in RandImageIndices]
        RandImageList.append(RandImages)
        RandomizedImageOrder.append(RandImageIndices)

    CatOrder = np.zeros((N, len(ImageList)))
    CatOrder[:, 1] = 1
    CatOrder[:, 2] = 2

    [np.random.shuffle(i) for i in CatOrder]

    return RandImageList, RandomizedImageOrder, CatOrder


def ShowImage(Window, ImagePath, RefreshRate, Duration, ImScale = (1, 1)):
    Image = visual.ImageStim(Window, image = ImagePath, size = ImScale)
    Frames = int(RefreshRate*Duration)
    for frame in range(Frames):
        CheckQuitWindow(Window)
        Image.draw()
        Window.flip()
        pass


def ShowText(Window, Text, RefreshRate, Duration):
    Frames = int(RefreshRate*Duration)
    Stim = visual.TextStim(Window, text=Text)
    for frame in range(Frames):
        CheckQuitWindow(Window)
        Stim.draw()
        Window.flip()
        pass


def ShowMovie(Window, MoviePath):
    Movie = visual.MovieStim3(Window, MoviePath, flipVert=False)
    while Movie.status != visual.FINISHED:
        CheckQuitWindow(Window)
        Movie.draw()
        Window.flip()
        pass


def FrameWait(Window, RefreshRate, Duration):
    Frames = int(RefreshRate*Duration)
    for frame in range(Frames):
        Window.flip()


def CheckQuitWindow(Window):
    keys = event.getKeys()
    for key in keys:
        if 'esc' in key:
            Window.close()
            core.quit()
    return None


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
# Some examples for PsychoPy and PyLSL
# https://github.com/kaczmarj/psychopy-lsl

print('Welcome!')

print('Generating Participant ID')
# Get path to list of (completed) participants. Program will automatically keep track of participants
# through this file. It can be edited by the user if necessary.
# Participant '0' does not exist. They are there to avoid warnings arising from importing an empty file
Path2LoP = "{}\LoP.txt".format(os.getcwd())
ParticipantID = GetParticipantInfo(Path2LoP)

print('\tParticipant ID = {}'.format(ParticipantID))

RefreshRate = GetRefreshRateWindows() # FPS

# These are the subfolder names of the images located in the 
# folder 'Images'.
CategoryNames = ['Faces', 'Flowers', 'Grey']

Images = []

for cat in CategoryNames:
    imgs = GetImages("{}/Images/{}/*.jpg".format(os.getcwd(), cat))
    Images.append(imgs)

# So that each participant has a different order of images, we use their participantID
# as the seed for the RNG. 
RandImages, ImageOrder, CategoryOrder = RandomizeImageOrder(Images, seed=ParticipantID)
NumCategories = len(RandImages)

# Split the image sets into before and after
# NOTE: int() rounds down to the nearest integer, so int(4.9) = 4
# We want to round down such that we can split the image stimuli in 
# two equal portions; one for Phase 1 and another for Phase 3
NPhaseStim = int(len(RandImages[0])/2)
P1Imgs, P1ImgOrder, P1CatOrder = RandImages[:][0:NPhaseStim], ImageOrder[:][0:NPhaseStim], CategoryOrder[:][0:NPhaseStim]
P3Imgs, P3ImgOrder, P3CatOrder = RandImages[:][NPhaseStim:(2*NPhaseStim)], ImageOrder[:][NPhaseStim:(2*NPhaseStim)], CategoryOrder[:][NPhaseStim:(2*NPhaseStim)]

Movies = GetImages("{}/Movies/*.mp4".format(os.getcwd()))

# Define default Marker Labels
MarkerLabels = ['Test', 'Text', 'Play', 'Pause', 'Start', 'End', 'Movie']

# Generate Stimuli Marker Labels
for cat in CategoryNames:
    MarkerLabels.append("Image_{}".format(cat))

# Generate a dictionary for the markers
markers = {}
for m in range(len(MarkerLabels)):
    markers.update({MarkerLabels[m] : [m]})

# Initialize LSL stream
<<<<<<< HEAD
info = StreamInfo(name='LSL_Stream', type = 'Markers', channel_count = 1,
=======
info = StreamInfo(name='Stream', type = 'Markers', channel_count = 1, 
>>>>>>> 8256bfab4b09497b0d4a7567b4265e24af557c7e
                  channel_format='int32', source_id='LSL_Stream_001')
outlet = StreamOutlet(info)


# Set up PyschoPy window parameters
Win = visual.Window(size=(800, 600))
Win.recordFrameIntervals = True
Win.refreshThreshold = 1/RefreshRate + 1/1000.
logging.console.setLevel(logging.WARNING)


# Once ready, hit spacebar to begin experiment
print('[PHASE 1] - Press the spacebar to begin')
event.waitKeys(keyList=['space'])

# Once spacebar has been hit, broadcast a start marker
outlet.push_sample(markers['Start'])

#======================================================
# PHASE 1
#======================================================

# Present Image Stimuli
for i in range(NPhaseStim):
    for c in range(NumCategories):
        category = int(P1CatOrder[i][c])
        Image = P1Imgs[category][i]
        CheckQuitWindow(Win)
        outlet.push_sample(markers['Image_{}'.format(CategoryNames[category])])
        ShowImage(Win, Image, RefreshRate, 2)
        outlet.push_sample(markers['Text'])
        ShowText(Win, '+', RefreshRate, 1)

# Send Pause marker to indicate start of AAT session, 
# and pause of the monitor stimuli presentation 
outlet.push_sample(markers['Pause'])
# Begin (pre) AAT session
ShowText(Win, 'Mobile AAT Phase', RefreshRate, 1)
print('[PHASE 1] - END')

#======================================================
# PHASE 2
#======================================================
# Press spacebar once AAT is completed, and participants
# are ready to watch the movie
print('\n[PHASE 2] - Press the spacebar to begin the movie')
event.waitKeys(keyList=['space'])
# Send a play marker to indicate beginning of movie 
# presentation
outlet.push_sample(markers['Play'])

# For each movie file
for Movie in Movies:
    # Push a movie marker
    outlet.push_sample(markers['Movie'])
    # Show the movie
    ShowMovie(Win, Movie)

# Send pause marker to indicate end of movie
outlet.push_sample(markers['Pause'])
print('[Phase 2] - END')


#======================================================
# PHASE 3
#======================================================
# Once participants are ready, press spacebar to 
# begin phase 3 
print('[Phase 3]  - Press the spacebar to begin')
event.waitKeys(keyList=['space'])
# Send play marker to indicate beginning of phase 3
outlet.push_sample(markers['Play'])

# Present Image Stimuli
for i in range(NPhaseStim):
    for c in range(NumCategories):
        category = int(P3CatOrder[i][c])
        Image = P3Imgs[category][i]
        CheckQuitWindow(Win)
        outlet.push_sample(markers['Image_{}'.format(CategoryNames[category])])
        ShowImage(Win, Image, RefreshRate, 2)
        outlet.push_sample(markers['Text'])
        ShowText(Win, '+', RefreshRate, 1)

# Broadcast Pause marker to indicate start of AAT
outlet.push_sample(markers['Pause'])
# Begin (post) AAT session
ShowText(Win, 'Mobile AAT Phase', RefreshRate, 1)
print('[PHASE 3] - END')
print('Experiment end, press esc to close.')
CheckQuitWindow(Win)

RecordParticipantIDs(Path2LoP, ParticipantID)

# Print number of dropped frames 
# print('Dropped Frames were {}'.format(Win.nDroppedFrames))
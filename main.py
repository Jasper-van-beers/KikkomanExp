# NOTE: Should set up experiment such that experiment works
# on two monitors, one for the researcher (from which they
# will control the experiment) and one for the participant
# (where the stimulus will be shown)
# Which monitor the various windows open on can be selected
# when intializing their respective objects.
# This way we can show participants only what we want them 
# to see.

#========================= IMPORTS =========================#
# External libraries
from psychopy import core, visual, event, logging, gui
from pylsl import StreamInfo, StreamOutlet
import os
import glob
import numpy as np
import pandas as pd

#========================= DEFINITIONS =========================#

def GetRefreshRateWindows():
    import win32api
    device = win32api.EnumDisplayDevices()
    settings = win32api.EnumDisplaySettings(device.DeviceName, -1)
    return getattr(settings, 'DisplayFrequency')


def AssignGroups(Num_Participants, seed = 0):
    Participants_Array = np.arange(1, Num_Participants + 1, 1)
    GroupAssign = np.zeros((1, (Num_Participants + 1)))[0]
    np.random.seed(seed)
    # Randomize Participants Order
    np.random.shuffle(Participants_Array)
    HalfN = int(Num_Participants/2)

    if Num_Participants % 2 == 0:
        # Take the first half of the random participant IDs and
        # assign them to group 1
        GroupAssign[Participants_Array[0:(HalfN)]] = 1
    else:
        # If the number of participants is odd, randomly assign
        # the remaining participant to one of the groups
        Prob = np.random.randint(100)
        if Prob <= 50:
            GroupAssign[Participants_Array[0:(HalfN)]] = 1
        else:
            GroupAssign[Participants_Array[0:(HalfN + 1)]] = 1

    return GroupAssign


# Should record participant condition as well
# -> In 'engaged' or 'disenganged'
#    -> Should this be done a priori? 
#    -> If total amount of participants known
#       -> I can make a script which pre-assigns participants'
#          group, based on their participant ID
# This function is used to record general participant data
#   It prompts the researcher with a dialog box which they
#   can fill out with the relevant information.
#   Some fields, such as participant ID, are fixed and are
#   not changable in the dialogbox itself
# This function returns:
#   - Dlg_data = Data entered in the dialogbox
#   - RunExp = Boolean to continue with the experiment, or cancel
#   - AllFields = List of the dialog box fields (e.g. Participant ID)
#       which shares the same indices as the Dlg_data 
def GetParticipantInfo(List_of_completed_participants, GroupAssignment, Developer=False):
    ExistingIDs = np.genfromtxt(List_of_completed_participants, comments='#')
    if ExistingIDs.size > 1:
        ParticipantID = int(ExistingIDs[-1] + 1)
    else:
        if not Developer:
            ParticipantID = 1
        else:
            ParticipantID = 0

    # Map group to word (0 = Engaged, 1 = Disengaged)
    if GroupAssignment[ParticipantID-1] == 0:
        Group = 'Engaged'
    else:
        Group = 'Disengaged'

    FixedFieldDict = {'Participant ID':ParticipantID, 
                      'Group':Group}

    VariableFieldDict = {'Age':[], 
                         'Gender':['Male', 'Female'],
                         'Height [cm]':[],
                         'Weight [kg]':[],
                         'Time since last meal [hours]':[]}

    AllFields = []

    DlgBx = gui.Dlg(title='Participant Information')
    for field in FixedFieldDict.keys():
        DlgBx.addFixedField('{}:'.format(field), FixedFieldDict[field])
        AllFields.append(field)
    for field in VariableFieldDict.keys():
        if len(VariableFieldDict[field]) > 0:
            DlgBx.addField('{}:'.format(field), choices=VariableFieldDict[field])
        else:
            DlgBx.addField('{}:'.format(field))
        AllFields.append(field)

    Dlg_data = DlgBx.show()
    if DlgBx.OK:
        RunExp = True
    else:
        RunExp = False

    return Dlg_data, RunExp, AllFields


def GenSavePath(ParticipantID, DataFolder = 'ExpData'):
    cwd = os.getcwd()
    ListDir = cwd.split('\\')[:-1]
    separator = '\\'
    TopDir = separator.join(ListDir)
    SaveFolder = DataFolder
    SavePath = "{}\\{}".format(TopDir, SaveFolder)
    if not os.path.isdir(SavePath):
        os.chdir(TopDir)
        os.mkdir(SaveFolder)
        os.chdir(cwd)
    
    ParticipantFolder = 'Participant_{}'.format(ParticipantID)
    ParticipantPath = "{}\\{}".format(SavePath, ParticipantFolder)
    if not os.path.isdir(ParticipantPath):
        os.chdir(SavePath)
        os.mkdir(ParticipantFolder)
        os.chdir(cwd)

    return ParticipantPath

# Function to save (general) participant data. 
def Save2ColCSV(Filename, Fields, Data, ParticipantID, DataCautious = True):
    ParticipantPath = GenSavePath(ParticipantID)

    DF = pd.DataFrame(data = {"Fields":Fields, "Data":Data})

    # Check if such a file exists already
    csvfile = "{}\\{}_{}.csv".format(ParticipantPath, ParticipantID, Filename)
    if os.path.isfile(csvfile) and DataCautious:
        print('[WARNING] - {} already exists. To keep data, I will save the current file under a different name.'.format(csvfile.split('\\')[-1]))
        # Create a unique tag based on current time
        import time
        np.random.seed(int(time.time()))
        Tag = np.random.randint(1000)
        NewName = "{}\\{}_{}_ID{}.csv".format(ParticipantPath, ParticipantID, Filename, Tag)
        DF.to_csv(NewName, sep=',', index=False)
        print('[INFO] - I have made a file called: {} with the current data'.format(NewName.split('\\')[-1]))
    else:
        DF.to_csv(csvfile, sep=',', index=False)

    return None



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



# Prompts the participant with a VAS with 'Question'
# Returns the participant response along the VAS ranging from [-1, 1]
# with 0 being neutral, -1 extreme disagreement and 1 extreme agreement
# with the supplied VASLabels. VASLabels is a list of the two extremes
# of the VAS; with the first element corresponding to the left-most 
# extreme
def ShowVAS(Window, Question, VASLabels, RefreshRate, TickLims = [-15, 15]):
    Slider = visual.Slider(Window, ticks = TickLims, 
                           labels = VASLabels,
                           granularity = 0,
                           style='triangleMarker',
                           pos = (0, -0.25))
    Text = visual.TextStim(Window, text = Question, pos = (0, 0.55), bold = True, height = 0.15)
    Instruction = visual.TextStim(Window, text = 'Please click the location on the line below which best describes how you feel',
                                 pos = (0, 0.2), 
                                 italic = True, height = 0.05)
    Waiting = True
    while Waiting:
        CheckQuitWindow(Window)
        Slider.draw()
        Text.draw()
        Instruction.draw()
        Window.flip()
        Res = Slider.getRating()
        if Res != None:
            Waiting = False
            for frame in range(int(RefreshRate*0.5)):
                Slider.draw()
                Text.draw()
                Window.flip()

    Slider.reset()
    Window.flip()

    return Res/TickLims[1]



def ShowSlider(Window, Question, Labels, Ticks, RefreshRate):
    Slider = visual.Slider(Window, ticks = Ticks, labels = Labels, pos = (0, -0.25), granularity = 1)
    Text = visual.TextStim(Window, text = Question, pos = (0, 0.55), bold = True, height = 0.15)
    Instruction = visual.TextStim(Window, text = 'Please indicate your agreement with the above statement on the scale below',
                                  pos = (0, 0.2), italic = True, height = 0.05)
    
    Waiting = True
    while Waiting:
        CheckQuitWindow(Window)
        Slider.draw()
        Text.draw()
        Instruction.draw()
        Window.flip()
        Res = Slider.getRating()
        if Res != None:
            Waiting = False
            for frame in range(int(RefreshRate*0.5)):
                Slider.draw()
                Text.draw()
                Window.flip()

    Slider.reset()
    Window.flip()

    return Res



def AskFoodNeophobia(Window, RefreshRate):
    # Food Neophobia questions
    Questions = {"I am constantly sampling new and different foods." : 1,
                 "I don't trust new foods." : 0,
                 "If I don't know what is in a food, I won't try it." : 0,
                 "I like foods from different countries." : 1,
                 "Ethnic food looks too weird to eat." : 0,
                 "At dinner parties, I will try a new food." : 1,
                 "I am afraid to eat things I have never had before." : 0,
                 "I am very particular about the foods I will eat." : 0,
                 "I will eat almost anything." : 1,
                 "I like to try new ethnic restaurants." : 1}

    Answers = np.zeros((1, len(Questions)))[0]

    SliderLabels = ['Strongly disagree', 'Strongly agree']
    SliderTickMarkers = [-3, -2, -1, 0, 1, 2, 3]

    i = 0
    for question in Questions.keys():
        Rating = ShowSlider(Window, question, SliderLabels, SliderTickMarkers, RefreshRate)
        # Check if rating should be reversed
        if Questions[question]:
            Rating = -1 * Rating
        Score = Rating + 4
        Answers[i] = Score
        i += 1

    return list(Questions.keys()), Answers



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



def ShowImage(Window, ImagePath, RefreshRate, Duration, Scale = 1):
    Image = visual.ImageStim(Window, image = ImagePath, units='pix')

    # Maintain Image Aspect Ratio, based on smallest Window dimension
    WinSize = Window.size
    ImSize = Image.size
    RelaSize = WinSize/ImSize
    ImScale = np.min(RelaSize * Scale)
    Image.setSize(ImSize*ImScale)

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


def ShowMovie(Window, MoviePath, Scale = 1):
    Window.setColor([-1, -1, -1])
    Movie = visual.MovieStim3(Window, MoviePath, flipVert=False, units='pix')
    
    # Maintain Movie Aspect Ratio, based on smallest Window dimension
    WinSize = Window.size
    MovSize = Movie.size
    RelaSize = WinSize/MovSize
    MovScale = np.min(RelaSize * Scale)
    Movie.setSize(MovSize*MovScale)

    while Movie.status != visual.FINISHED:
        CheckQuitWindow(Window)
        Movie.draw()
        Window.flip()
        
    Window.setColor(bgcolor)


# Function to show EmojiGrid image and record response location
# Returns the location of the click on the grid, where:
#       PosOnGrid = [1, 1] is the top right
#       PosOnGrid = [-1, 1] is the top left
#       PosOnGrid = [-1, -1] is bottom left
#       PosOnGrid = [1, -1] is the bottom right
def ShowEmojiGrid(Window, RefreshRate, Scale = 1):
    # Get outer image of EmojiGrid (Emojis)
    EmojiGrid_Path = "{}/Images/EmojiGrid/EmojiGrid_outside.jpg".format(os.getcwd())
    EmojiGrid = visual.ImageStim(Window, image = EmojiGrid_Path, units = 'pix')

    # Maintain Image Aspect Ratio, based on smallest Window dimension
    WinSize = Window.size
    ImSize = EmojiGrid.size
    RelaSize = WinSize/ImSize
    ImScale = np.min(RelaSize * Scale)
    EmojiGrid.setSize(ImSize*ImScale)

    # Get inner image of EmojiGrid (Grid)
    Grid_EmojiGrid_Path = "{}/Images/EmojiGrid/EmojiGrid_inside.jpg".format(os.getcwd())
    GridBox = visual.ImageStim(Window, image = Grid_EmojiGrid_Path, units = 'pix')
    GridSize = GridBox.size
    # Ratio of EmojiGrid_outside to EmojiGrid_inside
    Ratio = np.min(ImSize/GridSize)
    GridBox.setSize(EmojiGrid.size/Ratio)

    # Initialize mouse object
    mouse = event.Mouse()

    WaitingInput = True
    while WaitingInput:
        # Check if esc has been hit, if so, quit
        CheckQuitWindow(Window)

        # Draw EmojiGrid
        EmojiGrid.draw()
        GridBox.draw()
        Window.flip()

        # Get clicks from mouse
        Clicks = mouse.getPressed()
        # If left mouse button is clicked, and this click occured 
        # within the region of the grid, then store mouse position
        # and end loop
        if Clicks[0] and mouse.isPressedIn(GridBox):
            MPos = mouse.getPos()
            WaitingInput = False
    
    # Provide some user feedback of click location with a red cross. 
    ClickLoc = visual.TextStim(Window, text='+', color = (1, 0, 0), pos=MPos)
    # Show click location for half a second
    for frame in range(int(RefreshRate*0.5)):
        EmojiGrid.draw()
        GridBox.draw()
        ClickLoc.draw()
        Window.flip()

    # GridSize is experssed w.r.t WinSize
    # Since the image is centered around zero, the image spans 
    # half the total number of pixels in each direction from
    # the origin
    SectorSize = GridSize*WinSize/2
    # Mouse position is also given w.r.t WinSize
    MPosPix = MPos*WinSize

    # Get position on grid, ranging from [-1, 1] in x and y, with 
    # origin at [0, 0]
    PosOnGrid = MPosPix/SectorSize

    return PosOnGrid


def SaveImageResponseData(Filename, ImgList, Data, ParticipantID, ColNames = [], DataCautious = True):
    SavePath = GenSavePath(ParticipantID)

    if ColNames:
        df_data = {'Image ID': ImgList}
        for col in range(len(ColNames)):
            df_data.update({'{}'.format(ColNames[col]):Data[:, col]})
    else:
        df_data = {'Image ID': ImgList}
        for col in range(len(Data[0])):
            df_data.update({'Col_{}'.format(col):Data[:, col]})
            
    DF = pd.DataFrame(data = df_data)

    # Check if such a file exists already
    csvfile = "{}\\{}_{}.csv".format(SavePath, ParticipantID, Filename)
    if os.path.isfile(csvfile) and DataCautious:
        print('[WARNING] - {} already exists. To keep data, I will save the current file under a different name.'.format(csvfile.split('\\')[-1]))
        # Create a unique tag based on current time
        import time
        np.random.seed(int(time.time()))
        Tag = np.random.randint(1000)
        NewName = "{}\\{}_{}_ID{}.csv".format(SavePath, ParticipantID, Filename, Tag)
        DF.to_csv(NewName, sep=',', index=False)
        print('[INFO] - I have made a file called: {} with the current data'.format(NewName.split('\\')[-1]))
    else:
        DF.to_csv(csvfile, sep=',', index=False)

    return None


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

# Set to true to test script and avoid saving over participant data.
Developer = True

# Assign participants to a (pre-allocated) group 
# Here, 0 = Engaged Group, 1 = Disengaged group
GenerateGroupAssignments = False
if GenerateGroupAssignments:
    Groups = AssignGroups(40, seed = 0)
    np.savetxt('Groups.txt', Groups)
else:
    Groups = np.genfromtxt('Groups.txt')


print('Welcome!')

# Get path to list of (completed) participants. Program will automatically keep track of participants
# through this file. It can be edited by the user if necessary.
# Participant '0' does not exist. They are there to avoid warnings arising from importing an empty file
Path2LoP = "{}\\LoP.txt".format(os.getcwd())
ParticipantINFO, RunExperiment, AllFields = GetParticipantInfo(Path2LoP, Groups, Developer=Developer)

if RunExperiment:
    if Developer:
        print('[INFO] - RUNNING IN DEVELOPER MODE, DEFAULTING TO PARTICIPANT ID = 0')

    ParticipantID = int(ParticipantINFO[0])

    print('[INFO] Running experiment for ParticipantID = {}'.format(ParticipantID))

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
    MarkerLabels = ['Test', 
                    'General Questions', 
                    'Neophobia', 
                    'Practice', 
                    'Text', 
                    'Play', 
                    'Pause', 
                    'Start', 
                    'End', 
                    'Movie']

    # Generate Stimuli Marker Labels
    for cat in CategoryNames:
        MarkerLabels.append("Image_{}".format(cat))

    # Generate a dictionary for the markers
    markers = {}
    for m in range(len(MarkerLabels)):
        markers.update({MarkerLabels[m] : [m]})

    # Initialize LSL stream
    info = StreamInfo(name='LSL_Stream', type = 'Markers', channel_count = 1,
                    channel_format='int32', source_id='LSL_Stream_001')
    outlet = StreamOutlet(info)


    # Set up PyschoPy window parameters
    WinH = 900
    WinW = 1600
    bgcolor = [0.1, 0.1, 0.1]
    Win = visual.Window(size=(WinW, WinH), units='norm', color = bgcolor)
    Win.recordFrameIntervals = True
    Win.refreshThreshold = 1/RefreshRate + 1/1000.
    logging.console.setLevel(logging.WARNING)

    # General questions
    GenQuestions = {'How hungry are you right now?':['Not at all','Extremely'],
                    'How full do you feel right now?':['Not at all','Extremely'],
                    'How familiar are you with Asian food?':['Not at all','Extremely']}

    print('\n[GENERAL QUESTIONS] - Press the spacebar to begin general questions')
    event.waitKeys(keyList=['space'])
    outlet.push_sample(markers['General Questions'])

    for question in GenQuestions.keys():
        AllFields.append(question)
        Response = ShowVAS(Win, question, GenQuestions[question], RefreshRate)
        ParticipantINFO.append(Response)

    # Save participant information and general question responses
    # NOTE: CHANGE DataCautious = True for final version
    Save2ColCSV('General_Data', AllFields, ParticipantINFO, ParticipantINFO[0], DataCautious=False)

    print('\n[NEOPHOBIA SURVEY] - Press the spacebar to begin Food Neophobia Survey')
    event.waitKeys(keyList=['space'])
    outlet.push_sample(markers['Neophobia'])

    FNSQuestions, FNSAnswers = AskFoodNeophobia(Win, RefreshRate)

    for entry in range(len(FNSQuestions)):
        AllFields.append(FNSQuestions[entry])
        ParticipantINFO.append(FNSAnswers[entry])

    # Save participant information and general question responses
    # NOTE: CHANGE DataCautious = True for final version
    Save2ColCSV('Neophobia', FNSQuestions, FNSAnswers, ParticipantINFO[0], DataCautious=False)

    print('\n[PRACTICE] - Press the spacebar to begin practice trials')
    event.waitKeys(keyList=['space'])
    outlet.push_sample(markers['Practice'])

    # TODO: Practice trials

    #======================================================
    # PHASE 1
    #======================================================
    # Once ready, hit spacebar to begin experiment
    print('\n[PHASE 1] - Press the spacebar to begin experiment')
    event.waitKeys(keyList=['space'])

    # Initialize data arrays before sending markers, to minimize differences
    # in processing time between participants
    P1EmojiGridResponses = np.zeros((int(NPhaseStim*NumCategories), 2))
    P1PresentedImageList = []

    # Once spacebar has been hit, broadcast a start marker
    outlet.push_sample(markers['Start'])

    # Present Image Stimuli
    idx = 0
    for i in range(NPhaseStim):
        for c in range(NumCategories):
            category = int(P1CatOrder[i][c])
            Image = P1Imgs[category][i]
            CheckQuitWindow(Win)
            outlet.push_sample(markers['Text'])
            ShowText(Win, '+', RefreshRate, 2)
            outlet.push_sample(markers['Image_{}'.format(CategoryNames[category])])
            ShowImage(Win, Image, RefreshRate, 2)
            MousePos = ShowEmojiGrid(Win, RefreshRate)
            P1EmojiGridResponses[idx] = MousePos
            P1PresentedImageList.append("{}_{}".format(CategoryNames[category], Image.split('\\')[-1][:-4]))
            idx += 1

    # Send Pause marker to indicate start of AAT session, 
    # and pause of the monitor stimuli presentation 
    outlet.push_sample(markers['Pause'])

    # Save EmojiGrid data
    SaveImageResponseData('P1_EmojiGrid', P1PresentedImageList, P1EmojiGridResponses, ParticipantINFO[0], 
                            ColNames = ['Valence', 'Arousal'], DataCautious=False)

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

    # Add participant ID to completed list of participants
    if not Developer:
        RecordParticipantIDs(Path2LoP, ParticipantID)

    # Print number of dropped frames 
    # print('Dropped Frames were {}'.format(Win.nDroppedFrames))


else:
    print('[INFO] - User cancelled - Experiment aborted')
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
# Need to import prefs before importing other psychopy modules
from psychopy import prefs
prefs.hardware['audioLib'] = ['pyo']
from psychopy import core, visual, event, logging, gui, sound
from pylsl import StreamInfo, StreamOutlet
import os
import glob
import numpy as np
import pandas as pd
import time

#========================= DEFINITIONS =========================#
# For documentation on the definitions, see Documentation file.
# Filename: 'Kikkoman Expansion Experiment Documentation.docx'


def GetRefreshRateWindows():
    import win32api
    device = win32api.EnumDisplayDevices()
    settings = win32api.EnumDisplaySettings(device.DeviceName, -1)
    return getattr(settings, 'DisplayFrequency')



def SetColorPalette(color, ManualAssign = []):
    # If user inputted colors manually, and all colors are specified, set
    # color palette to user input.
    if len(ManualAssign) == 4:
        Background, Text, Slider, Marker = ManualAssign

    else:
        # Define color dictionary
        colorDict = {'default':['Grey', 'White', 'LightGrey', 'DarkRed'],
                     'grey':['Grey', 'White', 'LightGrey', 'DimGrey'],
                     'slate':['SlateGrey', 'White', 'LightGrey', 'DarkSlateGrey'],
                     'beige':['PapayaWhip', 'Black', 'Peru', 'Sienna'],
                     'white':['SeaShell', 'Black', 'Silver', 'DimGrey'],
                     'red':['MistyRose', 'Black', 'IndianRed', 'DarkRed'],
                     'blue':['LightSteelBlue', 'DarkSlateGrey', 'LightSlateGrey', 'DarkCyan']}
        # If user inputted dominat color is a known color palette, then set colors
        if color.lower() in colorDict.keys():
            Background, Text, Slider, Marker = colorDict[color.lower()]
        # If user input is unknown, use default color.
        else:
            Background, Text, Slider, Marker = colorDict['default']

    return Background, Text, Slider, Marker



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



def GetParticipantInfo(Path2ListOfParticipants, GroupAssignment, Developer=False):
    # Get completed participants, and assign new participant ID
    ExistingIDs = np.genfromtxt(Path2ListOfParticipants, comments='#')
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

    # Fixed fields (i.e. unchangable in dialog box)
    FixedFieldDict = {'Participant ID':ParticipantID,
                      'Group':Group}

    # Fields which require user input
    VariableFieldDict = {'Age':[],
                         'Gender':['Male', 'Female'],
                         'Height [cm]':[],
                         'Weight [kg]':[],
                         'Time since last meal [hours]':[]}

    AllFields = []

    # Build Dialog box based on above fields
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

    # Show dialog box and wait for 'OK'
    Dlg_data = DlgBx.show()
    if DlgBx.OK:
        RunExp = True
    else:
        RunExp = False

    return Dlg_data, RunExp, AllFields



def GenSavePath(ParticipantID, DataFolder = 'ExpData'):
    cwd = os.getcwd()
    # Move one directory level 'up'
    ListDir = cwd.split('\\')[:-1]
    separator = '\\'
    TopDir = separator.join(ListDir)
    SaveFolder = DataFolder
    SavePath = "{}\\{}".format(TopDir, SaveFolder)
    # Check if 'DataFolder' exists, otherwise create it
    if not os.path.isdir(SavePath):
        os.chdir(TopDir)
        os.mkdir(SaveFolder)
        os.chdir(cwd)

    # Check if Participant folder exists, otherwise create it
    ParticipantFolder = 'Participant_{}'.format(ParticipantID)
    ParticipantPath = "{}\\{}".format(SavePath, ParticipantFolder)
    if not os.path.isdir(ParticipantPath):
        os.chdir(SavePath)
        os.mkdir(ParticipantFolder)
        os.chdir(cwd)

    return ParticipantPath



def Save2ColCSV(Filename, Fields, Data, ParticipantID, DataCautious = True):
    # Generate the unique save path for the participant
    ParticipantPath = GenSavePath(ParticipantID)

    # Create data array to save
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



def RecordParticipantIDs(Path2ListOfParticipants, ParticipantID):
    # Find file containing the list of completed participants and open it
    filename = Path2ListOfParticipants.split('\\')[-1]
    ExistingIDs = np.genfromtxt(Path2ListOfParticipants, comments='#')
    # Add current participant ID to this list
    if ExistingIDs.size > 1:
        ExistingIDs = np.append(ExistingIDs, ParticipantID)
    else:
        ExistingIDs = np.array([0, ParticipantID])
    # Save the file
    ExistingIDs = ExistingIDs.astype(int)
    np.savetxt(filename, ExistingIDs, fmt='%i')
    return None



def ShowVAS(Window, Question, VASLabels, RefreshRate, TickLims = [-15, 0, 15], MarkerColor = 'DarkSlateGrey', TextColor = 'White', SliderColor = 'LightGrey'):
    # Create slider object
    Slider = visual.Slider(Window, ticks = TickLims,
                           labels = VASLabels,
                           granularity = 0,
                           style='triangleMarker',
                           pos = (0, -0.25),
                           color = SliderColor)
    # Create text object, which displays 'Question'
    Text = visual.TextStim(Window, text = Question, pos = (0, 0.55), bold = True, height = 0.15, color = TextColor, alignText="center")
    # Create instruction object, below 'Question'
    Instruction = visual.TextStim(Window, text = 'Please click the location on the line below which best describes how you feel',
                                 pos = (0, 0.2),
                                 italic = True, height = 0.05, color = TextColor)
    # Set slider bar color
    Slider.marker.color = MarkerColor

    # While waiting for a response, show slider, question and instruction
    Waiting = True
    while Waiting:
        # Check if 'esc' has been hit
        CheckQuitWindow(Window)
        Slider.draw()
        Text.draw()
        Instruction.draw()
        Window.flip()
        # Retrieve response, if any
        Res = Slider.getRating()
        # Once response is received, stop loop and show visual feedback of response
        # for 0.3 seconds
        if Res != None:
            Waiting = False
            for frame in range(int(RefreshRate*0.3)):
                Slider.draw()
                Text.draw()
                Window.flip()

    # Reset slider position
    Slider.reset()
    Window.flip()

    return Res/TickLims[-1]



def ShowSlider(Window, Question, Labels, Ticks, RefreshRate, Style = 'rating', Size = (1.2, 0.1), MarkerColor = 'DarkSlateGrey', TextColor = 'White', SliderColor = 'LightGrey'):
    # Create slider object
    Slider = visual.Slider(Window, ticks = Ticks, labels = Labels, pos = (0, -0.25), granularity = 1,
                            style=Style, size = Size, labelHeight = 0.07, color = SliderColor)
    # Create text object, which displays 'Question'
    Text = visual.TextStim(Window, text = Question, pos = (0, 0.55), bold = True, height = 0.15, color = TextColor)
    # Create instruction object, below 'Question'
    Instruction = visual.TextStim(Window, text = 'Please indicate your agreement with the above statement on the scale below',
                                  pos = (0, 0.2), italic = True, height = 0.05, color = TextColor)
    #Set slider bar color
    Slider.marker.color = MarkerColor

    # While waiting for a response, show slider, question and instruction
    Waiting = True
    while Waiting:
        # Check if 'esc' has been hit
        CheckQuitWindow(Window)
        Slider.draw()
        Text.draw()
        Instruction.draw()
        Window.flip()
        # Retrieve response, if any
        Res = Slider.getRating()
        # Once response is received, stop loop and show visual feedback of response
        # for 0.3 seconds
        if Res != None:
            Waiting = False
            for frame in range(int(RefreshRate*0.3)):
                Slider.draw()
                Text.draw()
                Window.flip()

    # Reset slider position
    Slider.reset()
    Window.flip()

    return Res



def AskFoodNeophobia(Window, RefreshRate, MarkerColor = 'DarkSlateGrey', TextColor = 'White', SliderColor = 'LightGrey'):
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
    # Preallocate answer array
    Answers = np.zeros((1, len(Questions)))[0]

    # Define Neophobia scale labels
    SliderLabels = ['Strongly disagree', 'Strongly agree']
    # Assign marker scores
    SliderTickMarkers = [-3, -2, -1, 0, 1, 2, 3]

    i = 0
    # For each question
    for question in Questions.keys():
        Rating = ShowSlider(Window, question, SliderLabels, SliderTickMarkers, RefreshRate, Style=['radio'],
                            Size = (1.1, 0.1), MarkerColor = MarkerColor, SliderColor = SliderColor, TextColor = TextColor)
        # Check if rating should be reversed
        if Questions[question]:
            Rating = -1 * Rating
        # Convert score to scale 1 - 7
        Score = Rating + 4
        # Store answers
        Answers[i] = Score
        # Move to next answer index
        i += 1

    return list(Questions.keys()), Answers



def GetImages(FolderPath):
    imgs_path = glob.glob(FolderPath)
    return imgs_path



def RandomizeImageOrder(ImageList, seed = 0):
    # Preallocate
    RandImageList = []
    RandomizedImageOrder = []
    np.random.seed(seed)
    # Randomize Image order within each category
    for Images in ImageList:
        N = len(Images)
        # Get image indices
        RandImageIndices = np.arange(0, N, 1)
        # Shuffle indices
        np.random.shuffle(RandImageIndices)
        # Shuffle images based on shuffled indices
        RandImages = [Images[i] for i in RandImageIndices]
        # Store outcomes of shuffling
        RandImageList.append(RandImages)
        RandomizedImageOrder.append(RandImageIndices)

    # Create an array representing the category order presentation
    CatOrder = np.zeros((N, len(ImageList)))
    CatOrder[:, 1] = 1
    CatOrder[:, 2] = 2

    # Shuffle order row-wise
    [np.random.shuffle(i) for i in CatOrder]

    return np.array(RandImageList), np.array(RandomizedImageOrder), np.array(CatOrder)



def ShowImage(Window, ImagePath, RefreshRate, Duration, Scale = 1):
    # Create image object
    Image = visual.ImageStim(Window, image = ImagePath, units='pix')

    # Maintain Image Aspect Ratio, based on smallest Window dimension
    WinSize = Window.size
    ImSize = Image.size
    RelaSize = WinSize/ImSize
    # Scale image, while maintaining aspect ratio
    ImScale = np.min(RelaSize * Scale)
    Image.setSize(ImSize*ImScale)

    # Show image for specified duration, as controlled by the number of frames
    Frames = int(RefreshRate*Duration)
    for frame in range(Frames):
        CheckQuitWindow(Window)
        Image.draw()
        Window.flip()

    return None



def ShowText(Window, Text, RefreshRate, Duration, Position=(0,0), Height=0.15, TextColor = 'White'):
    # Create text object
    Stim = visual.TextStim(Window, text=Text, pos=Position, height=Height, color=TextColor, alignText="center")
    # Define duration of text presentation, in frames
    Frames = int(RefreshRate*Duration)
    for frame in range(Frames):
        CheckQuitWindow(Window)
        Stim.draw()
        Window.flip()

    return None



def ShowMovie(Window, MoviePath, Scale = 1):
    bgcolor = Window.color
    # Set window background color to black.
    Window.setColor([-1, -1, -1])
    # Create movie object
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

    # Return background color to the original color
    Window.setColor(bgcolor)

    return None



def ShowEmojiGrid(Window, RefreshRate, Scale = 1, Position = (0, 0)):
    WinSize = Window.size

    # Get outer image of EmojiGrid (Emojis)
    EmojiGrid_Path = "{}/Images/EmojiGrid/EmojiGrid_outside.jpg".format(os.getcwd())
    EmojiGrid = visual.ImageStim(Window, image = EmojiGrid_Path, units = 'pix', pos = Position)

    # Maintain Image Aspect Ratio, based on smallest Window dimension
    ImSize = EmojiGrid.size
    RelaSize = WinSize/ImSize
    ImScale = np.min(RelaSize * Scale)
    EmojiGrid.setSize(ImSize*ImScale)

    # Get inner image of EmojiGrid (Grid)
    Grid_EmojiGrid_Path = "{}/Images/EmojiGrid/EmojiGrid_inside.jpg".format(os.getcwd())
    GridBox = visual.ImageStim(Window, image = Grid_EmojiGrid_Path, units = 'pix', pos = Position)
    GridSize = GridBox.size
    # Ratio of EmojiGrid_outside to EmojiGrid_inside
    Ratio = np.min(ImSize/GridSize)
    GridBox.setSize(EmojiGrid.size/Ratio)

    # Initialize mouse object
    mouse = event.Mouse()

    WaitingInput = True
    # Measure current time to get reaction time
    t_start = time.perf_counter()
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
    
    # Record reaction time
    RT = time.perf_counter() - t_start

    # Provide some user feedback of click location with a red cross.
    ClickLoc = visual.TextStim(Window, text='+', color = (1, 0, 0), pos=MPos)
    # Show click location for half a second
    for frame in range(int(RefreshRate*0.5)):
        EmojiGrid.draw()
        GridBox.draw()
        ClickLoc.draw()
        Window.flip()

    # Get the top left hand vertex of the EmojiGrid Grid box and multiply it by 2 to get the size
    # of the EmojiGrid in the window, in pixels.
    NormGridSize = (GridBox.verticesPix[-1])*2

    # Mouse position is also given w.r.t WinSize, convert this ratio into pixels
    MPosPix = MPos*WinSize

    # Express Mouse position w.r.t EmojiGrid, ranging from [-1, 1] in x and y, with
    # origin at [0, 0]
    #       PosOnGrid = [1, 1] is the top right
    #       PosOnGrid = [-1, 1] is the top left
    #       PosOnGrid = [-1, -1] is bottom left
    #       PosOnGrid = [1, -1] is the bottom right
    PosOnGrid = MPosPix/NormGridSize

    return PosOnGrid, RT



def SaveImageResponseData(Filename, ImgList, Data, ParticipantID, ColNames = [], DataCautious = True):
    # Create unique save path for each participant's data
    SavePath = GenSavePath(ParticipantID)

    # If the user provides column names, use those
    if ColNames:
        # Insert image names into the first column of the dataframe
        df_data = {'Image ID': ImgList}
        # Fill in the rest of the columns with data
        for col in range(len(ColNames)):
            df_data.update({'{}'.format(ColNames[col]):Data[:, col]})
    # If no column names are provided, use Col_1, Col_2, ..., Col_N
    else:
        # Insert image names into the first column of the dataframe
        df_data = {'Image ID': ImgList}
        # Fill in the rest of the columns with data
        for col in range(len(Data[0])):
            df_data.update({'Col_{}'.format(col):Data[:, col]})

    # Create dataframe for saving
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



def ShowEmoGrInstruction(Window, Instructions, RefreshRate, Scale = 1.5, TextColor = 'White'):
    # Dictionary to store instructions from 'Instructions'
    TextStimDict = {}

    NumIn = len(Instructions)
    # Resolution  (spacing) between entries from 'Instructions'
    Res = 0.28

    # Generate the text objects for Instructions. Place them appropriately in the
    # window
    for line in range(NumIn):
        # Update position of text object
        NewPos = (-0.48, (0.8-line*Res))
        # First line is the 'title', make it larger than the others
        if line == 0:
            H = 0.15
        else:
            H = 0.08
        TextStim = visual.TextStim(Window, text = Instructions[line], pos = NewPos, alignText='left', height = H, color = TextColor)
        # Update dictionary with text objects
        DictEntry = {'{}'.format(line):TextStim}
        TextStimDict.update(DictEntry)

    # Halve the window size
    WinSize = Window.size/2

    # Compute the position, in pixels, where the EmojiGrid will be centered.
    Position = (0.5*Window.size[0]/2, 0)

    # Get outer image of EmojiGrid (Emojis)
    EmojiGrid_Path = "{}/Images/EmojiGrid/EmojiGrid_outside.jpg".format(os.getcwd())
    EmojiGrid = visual.ImageStim(Window, image = EmojiGrid_Path, units = 'pix', pos = Position)

    # Maintain Image Aspect Ratio, based on smallest Window dimension
    ImSize = EmojiGrid.size
    RelaSize = WinSize/ImSize
    ImScale = np.min(RelaSize * Scale)
    EmojiGrid.setSize(ImSize*ImScale)

    # Get inner image of EmojiGrid (Grid)
    Grid_EmojiGrid_Path = "{}/Images/EmojiGrid/EmojiGrid_inside.jpg".format(os.getcwd())
    GridBox = visual.ImageStim(Window, image = Grid_EmojiGrid_Path, units = 'pix', pos = Position)
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

        # Draw instrucitons
        for line in range(NumIn):
            TextStimDict['{}'.format(line)].draw()

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

        # Draw instrucitons
        for line in range(NumIn):
            TextStimDict['{}'.format(line)].draw()

        EmojiGrid.draw()
        GridBox.draw()
        ClickLoc.draw()
        Window.flip()

    # Get the top left hand vertex of the EmojiGrid Grid box and multiply it by 2 to get the size
    # of the EmojiGrid in the window, in pixels.
    NormGridSize = (GridBox.verticesPix[-1])*2

    # Mouse position is also given w.r.t WinSize, convert this ratio into pixels
    MPosPix = MPos*WinSize

    # Express Mouse position w.r.t EmojiGrid, ranging from [-1, 1] in x and y, with
    # origin at [0, 0]
    PosOnGrid = MPosPix/NormGridSize

    return PosOnGrid



def ShowImInstruction(Window, Instructions, ImagePath, RefreshRate, Scale = 1, TextColor = 'White'):
    # Dictionary to store instructions from 'Instructions'
    TextStimDict = {}

    NumIn = len(Instructions)
    # Resolution  (spacing) between entries from 'Instructions'
    Res = 0.28

    # Generate the text objects for Instructions. Place them appropriately in the
    # window
    for line in range(NumIn):
        # Update position of text object
        NewPos = (-0.48, (0.8-line*Res))
        # First line is the 'title', make it larger than the others
        if line == 0:
            H = 0.15
        else:
            H = 0.08
        TextStim = visual.TextStim(Window, text = Instructions[line], pos = NewPos, alignText='left', height = H, color = TextColor)
        # Update dictionary with text objects
        DictEntry = {'{}'.format(line):TextStim}
        TextStimDict.update(DictEntry)

    # Halve the window size
    WinSize = Window.size/2

    # Compute the position, in pixels, where the EmojiGrid will be centered.
    Position = (0.5*Window.size[0]/2, 0)

    # Create image object
    Image = visual.ImageStim(Window, image = ImagePath, units = 'pix', pos = Position)
    # Scale image to appropriate size on RHS of the screen
    ImSize = Image.size
    RelaSize = WinSize/ImSize
    ImScale = np.min(RelaSize*Scale)
    Image.setSize(ImSize*ImScale)

    # Initialize mouse object
    mouse = event.Mouse()

    # Create a Next 'button' (Text object, but has a bounding box which can be clicked)
    NextBox = visual.TextStim(Window, text = 'Next', pos = (0.9, -0.9), alignText='center', height = H, color = TextColor)

    # While waiting for user to click 'next' show instructions and image
    WaitingInput = True
    while WaitingInput:
        # Check if esc has been hit, if so, quit
        CheckQuitWindow(Window)

        # Draw instrucitons
        for line in range(NumIn):
            TextStimDict['{}'.format(line)].draw()

        # Draw Image and Next 'button'
        Image.draw()
        NextBox.draw()
        Window.flip()

        # Get clicks from mouse
        Clicks = mouse.getPressed()
        # If left mouse button is clicked, and this click occured
        # within the region of the Next 'button', then end the loop
        if Clicks[0] and mouse.isPressedIn(NextBox):
            MPos = mouse.getPos()
            WaitingInput = False

    return None



def FrameWait(Window, RefreshRate, Duration):
    Frames = int(RefreshRate*Duration)
    for frame in range(Frames):
        Window.flip()
    return None



def CheckQuitWindow(Window):
    keys = event.getKeys()
    for key in keys:
        if 'esc' in key:
            Window.close()
            core.quit()
    return None



def CheckNumStim(ImageSets):
    N = len(ImageSets[0][0])
    IsEqual = True
    for ImageSet in ImageSets:
        for category in ImageSet:
            if len(category) != N:
                IsEqual = False
                print('[ERROR] Number of Image stimuli is not equal between phases and/or between image categories.')
                break
        if not IsEqual:
            break
    return N*IsEqual


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
# If GenerateGroupAssignments = True, then the script will
# assign groups, otherwise it will import these from 'Group.txt'
GenerateGroupAssignments = False
if GenerateGroupAssignments:
    Groups = AssignGroups(40, seed = 0)
    np.savetxt('Groups.txt', Groups)
else:
    Groups = np.genfromtxt('Groups.txt')


print('Welcome!')

# Get path to list of (completed) participants. Program will automatically keep track of participants
# through this file. It can be edited by the user if necessary.
# Participant '0' does is the developer. They are there to avoid warnings arising from importing an empty file
Path2LoP = "{}\\LoP.txt".format(os.getcwd())
ParticipantINFO, RunExperiment, AllFields = GetParticipantInfo(Path2LoP, Groups, Developer=Developer)

# If Dialog box used to fill in participant info was not cancelled
if RunExperiment:
    #======================================================
    # DATA IMPORTING
    #======================================================
    # Indicate in the terminal if the script is being run in developer mode.
    if Developer:
        print('[INFO] - RUNNING IN DEVELOPER MODE, DEFAULTING TO PARTICIPANT ID = 0')

    # Print participant number in terminal
    ParticipantID = int(ParticipantINFO[0])
    print('[INFO] Running experiment for ParticipantID = {}'.format(ParticipantID))

    # in Hz
    RefreshRate = GetRefreshRateWindows()

    # Get practice images, import all images in Practice folder
    PracticeImages = GetImages("{}/Images/Practice/*.jpg".format(os.getcwd()))

    # These are the subfolder names of the images located in the
    # folder 'Images'.
    CategoryNames = ['Asian', 'Dutch', 'Molded']
    NumCategories = len(CategoryNames)

    # NOTE: Change for final experiment
    ############
    LimIMGs = 3
    ############

    # Create N x M array where
    # N = Number of Categories and M = Number of images per category
    Phase1Images = []
    for cat in CategoryNames:
        imgs = GetImages("{}/Images/Phase1/{}/*.jpg".format(os.getcwd(), cat))
        Phase1Images.append(imgs[0:LimIMGs])
        # Phase1Images.append(imgs)

    # So that each participant has a different order of images, we use their participantID
    # as the seed for the RNG.
    P1Imgs, P1ImgOrder, P1CatOrder = RandomizeImageOrder(Phase1Images, seed=ParticipantID)

    # Create N x M array where
    # N = Number of Categories and M = Number of images per category
    Phase3Images = []
    for cat in CategoryNames:
        imgs = GetImages("{}/Images/Phase3/{}/*.jpg".format(os.getcwd(), cat))
        Phase3Images.append(imgs[LimIMGs:(2*LimIMGs)])
        # Phase1Images.append(imgs)

    # So that each participant has a different order of images, we use their participantID
    # as the seed for the RNG. Note, this seed should be different from that of Phase 1
    # otherwise the randomization is the same. In this case we add a large number (greater than
    # the number of participants)
    P3Imgs, P3ImgOrder, P3CatOrder = RandomizeImageOrder(Phase3Images, seed=int(1000 + ParticipantID))

    NPhaseStim = CheckNumStim([P1Imgs, P3Imgs])
    if NPhaseStim == 0:
        print('[ERROR] Number of Image stimuli is not equal between phases and/or between image categories.')

    # Get Movie file path
    Movies = GetImages("{}/Movies/*.mp4".format(os.getcwd()))



    #======================================================
    # LSL STREAM PARAMETERS
    #======================================================
    # Define default Marker Labels
    # NOTE: SAVE MARKERS TO CSV SO THAT WE CAN IMPORT LATER
    MarkerLabels = ['Test',
                    'General Questions',
                    'Neophobia',
                    'Practice',
                    'Text',
                    'Fixation',
                    'Play',
                    'Pause',
                    'Start',
                    'End',
                    'Sound',
                    'Movie']

    # Generate Image Stimuli Marker Labels
    for cat in CategoryNames:
        MarkerLabels.append("Image_{}".format(cat))

    # Generate a dictionary for the markers (i.e. number the markers)
    markers = {}
    for m in range(len(MarkerLabels)):
        markers.update({MarkerLabels[m] : [m]})

    # Initialize LSL stream
    info = StreamInfo(name='Marker_Stream', type = 'Markers', channel_count = 1,
                    channel_format='int32', source_id='Marker_Stream_001')
    outlet = StreamOutlet(info)

    # Set sound lib
    mySound = sound.Sound('C', secs = 0.1)
    outlet.push_sample(markers['Sound'])
    mySound.play()



    #======================================================
    # PSYCHOPY WINDOW PARAMETERS
    #======================================================
    # Set up PyschoPy window parameters
    WinH = 900
    WinW = 1600
    # Set color palette for experiment
    bgcolor , textColor, sliderColor, sliderMarkerColor = SetColorPalette('beige')
    # Define window object
    Win = visual.Window(size=(WinW, WinH), units='norm', color = bgcolor)
    Win.recordFrameIntervals = True
    Win.refreshThreshold = 1/RefreshRate + 1/1000.
    # logging.console.setLevel(logging.WARNING)


    #======================================================
    # VAS & GENERAL QUESTIONS
    #======================================================
    # Write general questions here, along with a list of VAS extremes from left to right
    GenQuestions = {'How hungry are you right now?':['Not at all','Extremely'],
                    'How full do you feel right now?':['Not at all','Extremely'],
                    'How familiar are you with Asian food?':['Not at all','Extremely']}

    # Run General questions when spacebar is pressed
    print('\n[GENERAL QUESTIONS] - Press the spacebar to begin general questions')
    event.waitKeys(keyList=['space'])
    outlet.push_sample(markers['General Questions'])

    outlet.push_sample(markers['Sound'])
    mySound.play()

    # Ask the general questions, and record VAS responses to participant INFO
    for question in GenQuestions.keys():
        AllFields.append(question)
        Response = ShowVAS(Win, question, GenQuestions[question], RefreshRate, MarkerColor = sliderMarkerColor, TextColor=textColor, SliderColor=sliderColor)
        ParticipantINFO.append(Response)

    # Save the participant INFO (dialog box and general questions)
    # NOTE: CHANGE DataCautious = True for final version
    Save2ColCSV('General_Data', AllFields, ParticipantINFO, ParticipantINFO[0], DataCautious=False)



    #======================================================
    # FOOD NEOPHOBIA SCALE (FNS)
    #======================================================
    # Run FNS survey when spacebar is pressed
    print('\n[NEOPHOBIA SURVEY] - Press the spacebar to begin Food Neophobia Survey')
    event.waitKeys(keyList=['space'])
    outlet.push_sample(markers['Neophobia'])

    # Ask FNS
    FNSQuestions, FNSAnswers = AskFoodNeophobia(Win, RefreshRate, MarkerColor = sliderMarkerColor, TextColor=textColor, SliderColor=sliderColor)

    # Record FNS questions and answers
    for entry in range(len(FNSQuestions)):
        AllFields.append(FNSQuestions[entry])
        ParticipantINFO.append(FNSAnswers[entry])

    # Save participant information and general question responses
    # NOTE: CHANGE DataCautious = True for final version
    Save2ColCSV('Neophobia', FNSQuestions, FNSAnswers, ParticipantINFO[0], DataCautious=False)



    #======================================================
    # PRACTICE AND EMOJIGRID INSTRUCTIONS
    #======================================================
    # Run EmojiGrid practice trials once the spacebar is pressed
    print('\n[PRACTICE] - Press the spacebar to begin practice trials')
    ShowText(Win, 'Instructions', RefreshRate, 0.1, TextColor = textColor)
    event.waitKeys(keyList=['space'])

    # Write the instructions for EmojiGrid usage below, first entry is the title
    # Subsequent entries indicate instructions on different lines
    Instructions_1 = ['EmojiGrid Response Tool',
                    'On your right is the EmojiGrid',
                    'For parts of this experiment, we will ask you to rate images using this tool',
                    'Simply click a location on the grid which best represents how you feel about the images',
                    'Do not think too much about it and go with your initial feeling!',
                    'To proceed, use the EmojiGrid to describe how you feel right now']

    # Show the EmojiGrid tool and ask users to rate how they currently feel (tool familiarization)
    _DummyPos = ShowEmoGrInstruction(Win, Instructions_1, RefreshRate, TextColor = textColor)

    # Get cwd path
    EgImgPath = "{}\Images\IMG_0019.JPG".format(os.getcwd())

    # Instructions for how image presentation works
    Instructions_2 = ['EmojiGrid Rating Process',
                      'First, you will be presented with an Image',
                      'After some time the image will disappear and then the EmojiGrid will appear',
                      'Use the EmojiGrid to rate how the image made you feel, remember there are no wrong answers!',
                      'Click "Next" to start the practice trials']

    ShowImInstruction(Win, Instructions_2, EgImgPath, RefreshRate, TextColor = textColor)

    # Preallocate practice arrays to store practice data
    # 3 Columns for EmojiGrid X, Y and Reaction time
    PracticeEmojiGridResponses = np.zeros((int(len(PracticeImages)), 3))
    PracticePresentedImageList = []

    # Inform participants that practice trials will begin shortly
    ShowText(Win, 'The Practice trials will begin shortly...', RefreshRate, 2, Height = 0.08, TextColor = textColor)

    outlet.push_sample(markers['Practice'])

    # Run EmojiGrid practice trials with practice images
    idx = 0
    for img in PracticeImages:
        CheckQuitWindow(Win)
        ShowText(Win, '+', RefreshRate, 0.2, TextColor = textColor)
        ShowImage(Win, img, RefreshRate, 3)
        MousePos, RT = ShowEmojiGrid(Win, RefreshRate)
        PracticeEmojiGridResponses[idx, 0:2] = MousePos
        PracticeEmojiGridResponses[idx, 2] = RT
        PracticePresentedImageList.append("Practice_{}".format(img.split('\\')[-1][:-4]))
        idx += 1

    # Save practice trial data (to check if tool is being used appropriately)
    SaveImageResponseData('Practice_EmojiGrid', PracticePresentedImageList, PracticeEmojiGridResponses, ParticipantINFO[0],
                        ColNames = ['Valence', 'Arousal', 'Reaction Time [s]'], DataCautious=False)

    # Indicate end of practice trials
    ShowText(Win, 'End of practice. The experiment will begin shortly...', RefreshRate, 0.1, Height = 0.08, TextColor = textColor)



    #======================================================
    # PHASE 1
    #======================================================
    # Once ready, hit spacebar to begin experiment
    print('\n[PHASE 1] - Press the spacebar to begin experiment')
    event.waitKeys(keyList=['space'])

    # Initialize data arrays before sending markers, to minimize differences
    # in processing time between participants. 
    # 3 Columns for EmojiGrid X, Y and Reaction time
    P1EmojiGridResponses = np.zeros((int(NPhaseStim*NumCategories), 3))
    P1PresentedImageList = []

    # Once spacebar has been hit, broadcast a start marker
    outlet.push_sample(markers['Start'])

    # Present Phase 1 Image Stimuli
    idx = 0
    for i in range(NPhaseStim):
        for c in range(NumCategories):
            category = int(P1CatOrder[i][c])
            Image = P1Imgs[category][i]
            CheckQuitWindow(Win)
            outlet.push_sample(markers['Fixation'])
            ShowText(Win, '+', RefreshRate, 0.2, TextColor = textColor)
            outlet.push_sample(markers['Image_{}'.format(CategoryNames[category])])
            ShowImage(Win, Image, RefreshRate, 3)
            MousePos, RT = ShowEmojiGrid(Win, RefreshRate)
            P1EmojiGridResponses[idx, 0:2] = MousePos
            P1EmojiGridResponses[idx, 2] = RT
            P1PresentedImageList.append("{}_{}".format(CategoryNames[category], Image.split('\\')[-1][:-4]))
            idx += 1

    # Send Pause marker to indicate start of AAT session,
    # and pause of the monitor stimuli presentation
    outlet.push_sample(markers['Pause'])

    # Save Phase 1 EmojiGrid data
    SaveImageResponseData('P1_EmojiGrid', P1PresentedImageList, P1EmojiGridResponses, ParticipantINFO[0],
                            ColNames = ['Valence', 'Arousal', 'Reaction Time [s]'], DataCautious=False)

    # Begin (pre) AAT session
    # Indicate that participants should now do the AAT section of phase 1
    ShowText(Win, 'Mobile AAT Phase', RefreshRate, 1, TextColor = textColor)
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

    # Initialize data arrays before sending markers, to minimize differences
    # in processing time between participants
    # 3 Columns for EmojiGrid X, Y and Reaction time
    P3EmojiGridResponses = np.zeros((int(NPhaseStim*NumCategories), 3))
    P3PresentedImageList = []

    # Send play marker to indicate beginning of phase 3
    outlet.push_sample(markers['Play'])

    idx = 0
    # Present Image Stimuli
    for i in range(NPhaseStim):
        for c in range(NumCategories):
            category = int(P3CatOrder[i][c])
            Image = P3Imgs[category][i]
            CheckQuitWindow(Win)
            outlet.push_sample(markers['Fixation'])
            ShowText(Win, '+', RefreshRate, 0.2, TextColor = textColor)
            outlet.push_sample(markers['Image_{}'.format(CategoryNames[category])])
            ShowImage(Win, Image, RefreshRate, 3)
            MousePos, RT = ShowEmojiGrid(Win, RefreshRate)
            P3EmojiGridResponses[idx, 0:2] = MousePos
            P3EmojiGridResponses[idx, 2] = RT
            P3PresentedImageList.append("{}_{}".format(CategoryNames[category], Image.split('\\')[-1][:-4]))
            idx += 1

    # Broadcast Pause marker to indicate start of AAT
    outlet.push_sample(markers['Pause'])

    # Save EmojiGrid data
    SaveImageResponseData('P3_EmojiGrid', P3PresentedImageList, P3EmojiGridResponses, ParticipantINFO[0],
                            ColNames = ['Valence', 'Arousal', 'Reaction Time [s]'], DataCautious=False)

    # Begin (post) AAT session
    ShowText(Win, 'Mobile AAT Phase', RefreshRate, 1, TextColor = textColor)
    print('[PHASE 3] - END')

    # Add participant ID to completed list of participants
    if not Developer:
        RecordParticipantIDs(Path2LoP, ParticipantID)

    # Print number of dropped frames
    print('Dropped Frames were {}'.format(Win.nDroppedFrames))

    print('Experiment end, press esc to close.')
    event.waitKeys(keyList=['escape'])

else:
    print('[INFO] - User cancelled - Experiment aborted')

from distutils.log import debug
from pynput.keyboard import Key, Controller, Listener, GlobalHotKeys
from pynput.mouse import Button, Controller as mController
import time
import mido
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from tkinter import messagebox
import os
import os.path
import threading
from enum import Enum
import musicbox


class status(Enum):
    '''
    status
    ----------
    used to handle states
    '''

    STOP = 1
    LISTEN = 2
    PLAY = 3


class Main:
    '''
    Main
    -------------
    main method, but as a class. A little odd, but it works lol
    This is mainly used to easily call any function from anywhere
    '''

    def __init__(self):
        self.root = tk.Tk()

        # the program's status as the user selects options
        self.status = status.STOP

        self.musicbox = musicbox.Musicbox(self)

        # used to keep track of the threads when they are spun up.
        # - we have to use threads in order to
        self.musicThread = None
        self.listenThread = None
        self.killListenThread = False

        # used for key listener cmds
        self.isShiftPressed = False

        # pynput controllers
        self.keyboard = Controller()
        self.mouse = mController()

        # ...
        self.populateTKUI()

        # generate the last used folder
        file_path = self.readSettings('playlistFolder')
        if(file_path != ''):
            self.findFolder(file_path)

        # handler for when user closes tkinter window
        self.root.protocol("WM_DELETE_WINDOW", self.onTKClose)

        # start tkinter
        tk.mainloop()

    def populateTKUI(self):
        '''
        -populate tkinter interface
        '''

        # tkinter window configs
        self.root.title('Marauder\'s JukeBox')
        self.root.geometry("650x350")

        # Main Settings and the main section that the user will interact with
        # --------------------------
        mainFrame = tk.LabelFrame(
            self.root, text="Main Settings", padx=15, pady=15)
        mainFrame.grid(row=0, column=0)

        # Version Number
        versionLabel = tk.Label(mainFrame, text="Version 1.0")
        versionLabel.grid(row=0, column=0, columnspan=2)

        # Playlist Directory (on click, opens file dialog to pick directory)
        self.playlistDirectory = tk.StringVar()
        self.playlistDirectory.set("Choose Folder...")
        pdLabel = tk.Label(mainFrame, text="Playlist Directory")
        pdLabel.grid(row=1, column=0)
        pdButton = tk.Button(mainFrame, textvariable=self.playlistDirectory,
                             command=self.findFolder)
        pdButton.grid(row=1, column=1)

        # Music Selection Combobox (auto update results on input enter | on select update debug settings)
        msLabel = tk.Label(mainFrame, text="Current Song").grid(row=2)
        self.lst = []
        self.msCombobox = ttk.Combobox(mainFrame)
        self.msCombobox.grid(row=2, column=1)
        self.msCombobox['values'] = self.lst
        self.msCombobox.bind('<KeyRelease>', self.checkInput)
        self.msCombobox.bind('<<ComboboxSelected>>',
                             self.on_msCombobox_click)

        # The Button to start and stop the listener/music
        self.formButtonText = tk.StringVar()
        self.formButtonText.set('Start')
        formButton = tk.Button(
            mainFrame, width=25, textvariable=self.formButtonText, command=self.formButtonPressed)
        formButton.grid(row=3, columnspan=2)

        # Extra settings that are available just in case the automated system messes it up and for debugging purposes
        # --------------------------
        debugFrame = tk.LabelFrame(
            self.root, text="Debug Settings", padx=15, pady=15)
        debugFrame.grid(row=1, column=0)

        # set tempo, and also update's the musicbox's tempo
        tempoLabel = tk.Label(debugFrame, text="Tempo")
        tempoLabel.grid(row=0, column=0)
        self.tempoText = tk.StringVar()
        self.tempoText.trace('w', lambda name, index, mode,
                             sv=self.tempoText: self.handleDebugEntries('tempo', self.tempoText))
        tempoEntry = tk.Entry(debugFrame, textvariable=self.tempoText)
        tempoEntry.grid(row=0, column=1)
        # self.tempoText.set(mido.tempo2bpm(self.musicbox.tempo))
        self.tempoText.set(0)

        # generate a list of valid octaves
        octaves = []
        for i in range(12, 128):
            if(i % 12 == 0):
                octaves.append(i)
        octaveLabel = tk.Label(debugFrame, text="Octave Start")
        octaveLabel.grid(row=1, column=0)
        self.octaveText = tk.StringVar()
        octaveDropDown = tk.OptionMenu(debugFrame, self.octaveText, *octaves)
        octaveDropDown.grid(row=1, column=1)
        self.octaveText.trace('w', lambda name, index, mode,
                              sv=self.octaveText: self.handleDebugEntries('octave', self.octaveText))
        # self.octaveText.set(self.musicbox.octaveStart)
        self.octaveText.set(12)

        # Field for inner key delay
        ikdLabel = tk.Label(debugFrame, text="Inner Key Delay")
        ikdLabel.grid(row=2, column=0)
        self.ikdText = tk.StringVar()
        self.ikdText.trace('w', lambda name, index, mode,
                           sv=self.ikdText: self.handleDebugEntries('ikd', self.ikdText))
        ikdEntry = tk.Entry(debugFrame, textvariable=self.ikdText)
        ikdEntry.grid(row=2, column=1)
        self.ikdText.set(self.musicbox.innerKeyDelay)

        # Field for outer key delay
        okdLabel = tk.Label(debugFrame, text="Outer Key Delay")
        okdLabel.grid(row=3, column=0)
        self.okdText = tk.StringVar()
        self.okdText.trace('w', lambda name, index, mode,
                           sv=self.okdText: self.handleDebugEntries('okd', self.okdText))
        okdEntry = tk.Entry(debugFrame, textvariable=self.okdText)
        okdEntry.grid(row=3, column=1)
        self.okdText.set(self.musicbox.outerKeyDelay)

        # Field for enabling the simulation of key/mouse presses
        self.keysInt = tk.IntVar()
        self.keysInt.trace('w', lambda name, index, mode,
                           sv=self.keysInt: self.handleDebugEntries('keys', self.keysInt))
        keysCB = tk.Checkbutton(
            debugFrame, text="Enable Keys", variable=self.keysInt)
        keysCB.grid(row=4, column=0)
        self.keysInt.set(1 if self.musicbox.enableKeys else 0)

        # Field for enabling rests and sustains
        self.sleepInt = tk.IntVar()
        self.sleepInt.trace('w', lambda name, index, mode,
                            sv=self.sleepInt: self.handleDebugEntries('sleep', self.sleepInt))
        sleepCB = tk.Checkbutton(
            debugFrame, text="Enable Sleep", variable=self.sleepInt)
        sleepCB.grid(row=4, column=1)
        self.sleepInt.set(1 if self.musicbox.enableSleep else 0)

        # Field for enabling organ resets
        self.resetOrganInt = tk.IntVar()
        self.resetOrganInt.trace('w', lambda name, index, mode,
                                 sv=self.resetOrganInt: self.handleDebugEntries('reset', self.resetOrganInt))
        resetOrganCB = tk.Checkbutton(
            debugFrame, text="Reset Organ", variable=self.resetOrganInt)
        resetOrganCB.grid(row=5, column=0)
        self.resetOrganInt.set(1 if self.musicbox.resetOrgan else 0)

        # Instructions
        # --------------------------
        instructionsFrame = tk.LabelFrame(
            self.root, text="Instructions", padx=15, pady=15)
        instructionsFrame.grid(row=0, column=1, rowspan=2, sticky='n')

        iText = 'How to Use\n'
        iText += '1. Navigate to a playlist directory\n'
        iText += '2. Select a song\n'
        iText += '3. Click the \'Start\' button in the \'Main Settings\'\n'
        iText += '4. Press \'Shift+v\' to start playing\n'
        iText += '5. To stop playing, press \'Shift+c\'\n'
        iText += '6. To quit the application, press \'Shift+z\'\n'
        iText += '\n'
        iText += 'Debug Tips\n'
        iText += '- \'Tempo\' and \'Octave Start\' update on song selection\n'
        iText += '\t- change them after song selection\n'
        iText += '- The delays help SoT register key presses\n'
        iText += '- Adjust \'Octave Start\' if song is on the wrong octave\n'
        iText += '- You can stop the odd pause by unchecking \'Reset Organ\'\n'
        iText += '\t- Just make sure to hit your interact key twice'

        instructionsLabel = tk.Label(
            instructionsFrame, text=iText, justify='left')
        instructionsLabel.grid(row=0, column=0)

    def handleDebugEntries(self, option, sv):
        '''
        used to help handle the extra options

        args:
        -option (str): the field the user is changing
        -sv (tk.StringVar): the stringvar that is used to keep the value for each field
        '''

        value = sv.get()
        match(option):
            case 'tempo':
                self.musicbox.tempo = mido.bpm2tempo(float(value))
            case 'octave':
                self.musicbox.octaveStart = int(value)
            case 'ikd':
                self.musicbox.innerKeyDelay = float(value)
            case 'okd':
                self.musicbox.outerKeyDelay = float(value)
            case 'keys':
                self.musicbox.enableKeys = (True if value == 1 else False)
            case 'sleep':
                self.musicbox.enableSleep = (True if value == 1 else False)
            case 'reset':
                self.musicbox.resetOrgan = (True if value == 1 else False)

    def findFolder(self, file_path=None):
        '''
        Takes a folder pathing, and updates it in the tkinter window and the musicbox

        args:
        -file_path (str): the folder path for the playlist.
        '''

        if(file_path is None):
            file_path = filedialog.askdirectory()

        # set song selection array to empty
        self.lst = []

        # set the stringvar 'playlistDirectory'
        if(file_path == ''):
            self.playlistDirectory.set('No Folder Selected')
        else:
            self.playlistDirectory.set(file_path)
            self.modifySettings('playlistFolder', file_path)

            # update lst with list of .mid files
            for x in os.listdir(file_path):
                if(x.endswith('.mid')):
                    self.lst.append(x)

        # update song selection combobox
        self.msCombobox['values'] = self.lst
        self.msCombobox.current(0)

        # if actual values, update musicbox with first midi file
        if(file_path != '' and self.msCombobox.get() != ''):
            self.musicbox.updateMidiFile(
                self.playlistDirectory.get()+'/'+self.msCombobox.get())

    def formButtonPressed(self):
        '''
        handles the tkinter form button
        '''

        if(self.formButtonText.get() == 'Start'):
            self.formButtonText.set('Stop')
            self.handleStateChange('listen')
        else:
            self.formButtonText.set('Start')
            self.handleStateChange('stop')

    def checkInput(self, e):
        '''
        handles the song selection combobox and updates the current selection based on what people type

        args:
        -e (event?): the keyrelease event //honestly not to sure about this one lmao
        '''

        value = e.widget.get()
        if(value == ''):
            self.msCombobox['values'] = self.lst
        else:
            data = []
            for item in self.lst:
                if(value.lower() in item.lower()):
                    data.append(item)
            self.msCombobox['values'] = data

    def on_msCombobox_click(self, e):
        '''
        when the user selects an option from the combobox

        args:
        -e (event?): the comboboxselected event?
        '''

        value = e.widget.get()
        self.musicbox.updateMidiFile(self.playlistDirectory.get()+'/'+value)

    def onTKClose(self):
        '''
        handles when the user closes out of the tkinter window
        '''

        if(messagebox.askokcancel("Quit", "Do you want to quit?")):

            # kill the music and listener thread before killing the tkinter window
            self.handleStateChange('stop')
            while((self.listenThread and self.listenThread.is_alive()) or (self.musicThread and self.musicThread.is_alive())):
                s = ''
                if(self.listenThread and self.listenThread.is_alive()):
                    s += 'LT | '
                if(self.musicThread and self.musicThread.is_alive()):
                    s += 'MT | '
                pass
            # self.root.destroy() this is apparently automatic

    def handleSettingsFile(self):
        '''
        check to see if settings.txt file exists
        '''

        if(not os.path.exists('settings.txt')):
            with open('settings.txt', 'w') as w:
                w.write('playlistFolder:\n')

    def modifySettings(self, key, val):
        '''
        given a key (atm just the playlistDirectory), set a value

        args:
        -key (str): the setting we are trying to save
        -val (str): the value of the setting we are trying to save

        notes:
        -this entire thing can probably be done better, but it's what I thought of doing, so yeah
        '''

        lines = []

        # check if settings file exists
        self.handleSettingsFile()

        # go through settings file and update the line with the key
        with open('settings.txt', 'r') as r:
            lines = r.readlines()
        for i in range(len(lines)):
            line = lines[i]
            colonIdx = line.find(':')
            r = [line[0:colonIdx], line[colonIdx+1:]]
            if(r[0] == key):
                s = r[0]+":"+val+"\n"
                lines[i] = s
                break

        # overwrite settings file
        with open('settings.txt', 'w') as w:
            w.writelines(lines)
            w.close()

    def readSettings(self, key):
        '''
        read the value of a setting

        args:
        -key (str): the setting we are looking for

        return:
        -(str or int): if it finds a value, it'll be a string. Otherwise it'll be a -1
        '''

        # check if settings.txt exists
        self.handleSettingsFile()

        # go through file and find key, and return the value
        with open('settings.txt', 'r') as r:
            lines = r.readlines()
            for line in lines:
                line = line.rstrip()
                colonIdx = line.find(':')
                r = [line[0:colonIdx], line[colonIdx+1:]]
                if(r[0] == key):
                    return r[1]
        return -1

    def handleStateChange(self, newStatus):
        '''
        Other than the name, this handles the killing and spawning of threats

        args:
        -newStatus (str): the new status imposed on the program
        '''

        if(newStatus == 'stop'):

            if(self.status == status.STOP):
                pass
            else:
                # kill either thread if it is alive
                if(self.musicThread and self.musicThread.is_alive() and self.musicbox.activeSong):
                    self.musicbox.killMusicThread = True
                if(self.listenThread and self.listenThread.is_alive()):
                    self.killListenThread = True
                    self.stopListenerThread()

            self.status = status.STOP
            while(self.musicbox.killMusicThread or self.killListenThread):
                time.sleep(.1)
            self.root.destroy()

        elif(newStatus == 'listen'):
            # if status is already the status then kill it
            if(self.status == status.LISTEN):
                self.killListenThread = True
                self.stopListenerThread()
            else:
                # kill music thread if it already exists
                if(self.musicThread and self.musicThread.is_alive() and self.musicbox.activeSong):
                    self.musicbox.killMusicThread = True

            self.startListenerThread()
            self.status = status.LISTEN

        elif(newStatus == 'halt'):
            # just kill the music if it's alive
            if(self.musicThread and self.musicThread.is_alive() and self.musicbox.activeSong):
                self.musicbox.killMusicThread = True
            self.status = status.LISTEN

        elif(newStatus == 'play'):
            if(self.status == status.PLAY):
                self.musicbox.killMusicThread = True
            self.startMusicThread()
            self.status = status.PLAY

    def startMusicThread(self):
        if(not self.musicbox.activeSong):
            self.musicThread = threading.Thread(
                target=self.musicThreadHandler, args=())
            self.musicThread.start()

    def musicThreadHandler(self):
        '''
        just a helper method for playing music. idk if it's necessary to be separate, but it works
        '''

        self.musicbox.activeSong = True
        while(self.musicbox.activeSong):
            self.musicbox.playMusic()

    def startListenerThread(self):
        self.listenThread = threading.Thread(
            target=self.keylistener, args=())
        self.listenThread.start()

    def stopListenerThread(self):
        self.listener.stop
        self.killListenThread = False

    def handleHotKeyPress(self, newStatus, str_status):
        '''
        helper method to handle the results of hotkey presses
        '''

        if(self.status == status.PLAY and newStatus == status.PLAY):
            self.handleStateChange('halt')
        if(self.status != newStatus):
            self.handleStateChange(str_status)

    def keylistener(self):
        '''
        Listeners for a select keyboard shortcuts.

        NOTE: If you have the program running and you press these hotkeys, then it will activate even if SoT is not running.
        '''

        self.listener = GlobalHotKeys({
            '<alt>+b': lambda status=status.PLAY, str_status='play': self.handleHotKeyPress(status, str_status),
            '<alt>+v': lambda status=status.LISTEN, str_status='halt': self.handleHotKeyPress(status, str_status),
            '<alt>+x': lambda status=status.STOP, str_status='stop': self.handleHotKeyPress(status, str_status)
        })
        self.listener.start()


if __name__ == '__main__':
    Main()

from re import L
import time
import mido
import os
import sys
from pynput.keyboard import Controller
from pynput.mouse import Button, Controller as mController


class Musicbox:
    '''
    Musicbox
    ----------
    The music player of the program
    '''

    def __init__(self, mainObj):
        self.mainObj = mainObj

        self.file_path = ''
        self.midi_file = ''
        self.killMusicThread = False

        self.activeSong = False

        self.keyboard = Controller()
        self.mouse = mController()

        # if these values are too small, then the inputs don't always register
        self.innerKeyDelay = .03
        self.outerKeyDelay = .035

        # tempo is ticks as provided by Mido
        self.tempo = 0

        # mod 12 for octaves
        self.octaveStart = 36

        self.enableDebug = False
        self.enableKeys = True
        self.enableSleep = True
        self.resetOrgan = True

        self.white_midi = []
        self.white_notes = ["C", "D", "E", "F", "G", "A",
                            "B", "C", "D", "E", "F", "G", "A", "B"]
        self.black_midi = []
        self.black_notes = ["C#/Db", "D#/Eb", "F#/Gb", "G#/Ab",
                            "A#/Bb", "C#/Db", "D#/Eb", "F#/Gb", "G#/Ab", "A#/Bb"]

    def updateMidiFile(self, fp=None):
        '''
        updates the self.midi_file variable when the user changes the song

        args
        -fp (str): path of midi file 
        '''

        if(fp == None):
            self.midi_file = mido.MidiFile(self.file_path)
        else:
            self.file_path = fp
            self.midi_file = mido.MidiFile(fp)
        self.genDefaultValues()

    def genDefaultValues(self):
        '''
        generates the default values of a song when it's updated
        '''

        # useful for some calculations
        self.ticksPerBeat = self.midi_file.ticks_per_beat

        # either separate the first for two
        # or use the first two (if there are muore than two tracks, it will only grab the first two)
        infoTrack = self.midi_file.tracks[0]
        if(len(self.midi_file.tracks) == 1):
            track = self.midi_file.tracks[0]
        else:
            track = self.midi_file.tracks[1]

        # setting a default (120 bpm) tempo
        self.tempo = 500000

        # loop thorugh events in the infoTrack to find the tempo
        for msg in infoTrack:
            if(msg.is_meta and hasattr(msg, 'tempo')):
                self.tempo = msg.tempo
                break
        self.mainObj.tempoText.set(mido.tempo2bpm(self.tempo))

        # Since the organ only has a range of two octaves, we need to determine how to place the notes most efficiently
        #   Get the count of every note
        noteRange = {}
        minNote = 99999999
        maxNote = 0
        for msg in track:
            if((msg.type == 'note_on' and msg.velocity == 0) or msg.type == 'note_off'):
                if(msg.note not in noteRange):
                    noteRange[msg.note] = 1
                else:
                    noteRange[msg.note] += 1
                if(msg.note < minNote):
                    minNote = msg.note
                if(msg.note > maxNote):
                    maxNote = msg.note

        # loop through the base note of each range and determine what provides the smallest octave jumps (outside of a min/max value based on i)
        estimatedStart = 0
        estimatedOutside = 9999999999999999
        for i in range(12, 128, 12):
            if(i-12 > maxNote):
                break
            if(i+12 < minNote):
                continue
            outside = 0
            for k in noteRange:
                if(k < i):
                    outside += noteRange[k]
                elif(k+24 > i):
                    outside += noteRange[k]
            if(outside < estimatedOutside):
                estimatedOutside = outside
                estimatedStart = i

        # set actual midi_song values
        self.octaveStart = estimatedStart
        self.mainObj.octaveText.set(estimatedStart)

    def genMidiRays(self):
        '''
        The midi note values for each note generated based on what the self.octaveStart. This will end up the respective colored notes from the range self.octaveStart to (self.octaveStart + 12)
        '''

        self.white_midi = []
        self.black_midi = []
        for k in range(2):
            flag = True
            for i in range(12):
                if(i == 5):
                    flag = False
                if(i % 2 == (0 if flag else 1)):
                    self.white_midi.append((i+(k*12)) + self.octaveStart)
                else:
                    self.black_midi.append((i+(k*12)) + self.octaveStart)

    def moveDirection(self, dir):
        '''
        simulates a key press based on the provided direction

        args
        -dir (char): a direction
        '''

        key = ''
        match(dir):
            case 'up':
                key = 'w'
            case 'left':
                key = 'a'
            case 'right':
                key = 'd'
            case 'down':
                key = 's'
        if(self.enableKeys):
            self.keyboard.press(key)
        if(self.enableSleep):
            time.sleep(self.innerKeyDelay)
        if(self.enableKeys):
            self.keyboard.release(key)
        if(self.enableSleep):
            time.sleep(self.outerKeyDelay)

    def nextAvailableNote(self, idx, track):
        '''
        helper method

        args:
        -idx (int): starting index
        -track (tracklist): the track

        return:
        -(int): the index that the next note is at
        '''

        for i in range(idx, len(track)):
            if((track[i].type == 'note_on' and track[i].velocity == 0) or track[i].type == 'note_off'):
                return i
        return -1

    def getModNote(self, note):
        '''
        given a note, get what octave it lies in

        args:
        -note (int): midi note value

        return:
        -(int): altered midi note value
        '''

        if(note < (self.octaveStart+12)):
            note = (note % 12) + self.octaveStart
        else:
            note = (note % 12) + self.octaveStart + 12
        return note

    def playMusic(self):
        '''
        helper method to play music
        '''

        self.genMidiRays()

        # quality of life for those who don't want to double tap the interact key lmao
        if(self.resetOrgan):
            self.moveDirection('down')
            for x in range(14):
                self.moveDirection('left')

        self.simulatePlaying()

    def simulatePlaying(self):
        '''
        reads the midi track and simulates the keypresses/mouseclicks
        '''

        self.activeSong = True
        curIdx = 0
        note = self.octaveStart
        newNoteIdx = 0
        idx = 0
        newNote = 0
        curEventIsRest = True
        totalRestTime = 0
        nextNoteEvent = 0
        noteCount = 0

        track = self.midi_file.tracks[1]

        for i in range(len(track)):

            # break out if music thread needs to die
            if(self.killMusicThread):
                break

            msg = track[i]

            # filters out the non-note messages
            if(msg.type == 'note_on' or msg.type == 'note_off'):

                # technically the upcoming note
                newNote = msg.note

                # if note is rest
                if((msg.type == 'note_on' and msg.velocity > 0)):

                    # if this and prev note is a rest, then just skip this note
                    if(curEventIsRest):
                        continue

                    # get the rest time before the next note
                    nextNoteEvent = self.nextAvailableNote(i, track)
                    if(not curEventIsRest):
                        curEventIsRest = True
                        totalRestTime = 0
                        for k in range(i, nextNoteEvent):
                            totalRestTime += track[k].time
                else:
                    curEventIsRest = False

                # helper var just to simplify things
                om = self.innerKeyDelay + self.outerKeyDelay

                # time used simulating ntoes
                timeused = 0

                # if note is active
                if((msg.type == 'note_on' and msg.velocity == 0) or msg.type == 'note_off'):
                    newNote = self.getModNote(msg.note)
                else:
                    newNote = self.getModNote(track[nextNoteEvent].note)

                if(note != newNote):
                    isNoteBlack = False

                    # if last note is black, go down to white keys
                    if(note in self.black_midi):
                        self.moveDirection('down')
                        note -= 1
                        timeused += om
                        isNoteBlack = True

                    isNewNoteBlack = False

                    # if new note is black, mark that we will need to go up to black arriving at the white key below the black key
                    if(newNote in self.black_midi):
                        isNewNoteBlack = True
                        newNote -= 1

                    # get the last note's and the new note's white_midi index
                    curIdx = self.white_midi.index(note)
                    newNoteIdx = self.white_midi.index(newNote)

                    # simulate movements until the two indexes equal each other
                    while(curIdx != newNoteIdx):
                        if(self.killMusicThread):
                            break
                        if(curIdx < newNoteIdx):
                            self.moveDirection('right')
                            curIdx += 1
                        elif(curIdx > newNoteIdx):
                            self.moveDirection('left')
                            curIdx -= 1
                        note = self.white_midi[curIdx]
                        timeused += om
                    if(self.killMusicThread):
                        break

                    # if new note was determined black from earlier, move up so that we are correct
                    if(isNewNoteBlack):
                        self.moveDirection('up')
                        note += 1
                        timeused += om

                if(self.killMusicThread):
                    break

                # if active note, simulate mouse
                if((msg.type == 'note_on' and msg.velocity == 0) or msg.type == 'note_off'):
                    if(self.enableKeys):
                        self.mouse.press(Button.left)
                    if(self.enableSleep):
                        sustain = mido.tick2second(
                            msg.time, self.ticksPerBeat, self.tempo)
                        sustain = sustain if self.innerKeyDelay < sustain else self.innerKeyDelay
                        time.sleep(sustain)
                    if(self.enableKeys):
                        self.mouse.release(Button.left)
                # sleep remaining rest time
                else:
                    if(self.enableSleep):
                        v = mido.tick2second(
                            totalRestTime, self.ticksPerBeat, self.tempo)
                        time.sleep(v-timeused if v-timeused > 0 else 0)
        self.activeSong = False
        self.killMusicThread = False

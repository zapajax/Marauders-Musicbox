# Marauder's Musicbox

## Description
This application allows you to play any song through a selection of midi files provided by the user. The midi file must have one note play at a time, otherwise timing will be incredibly off.

## How to Run/Install
To run the application, you can either run it from the executable, or python.

### - Executable
 1. Go to the 'Releases' page and download the executable
 2. Double click to run

### - Python
 1. Either clone this repository or download the source code in the 'Releases' page
 2. Make sure that you have Python 3.10, otherwise you'll need to revise each section that has a 'match' statement.
 3. Install the following packages:
    ```
    pynput, mido, tkinter
    ```
 4. Then run 'main.py'

## Options
### - Main Settings
 - Playlist Directory: choose the directory where the midi files are located.
 - Selected Song: The current song, click the drop down in order to change it.
 - Button: Starts the listener to wait for shortcut commands
### - Extra Settings
 - Tempo: When a song is selected, it updates the tempo. The user can modify this value, thus modifying the speed of the song. But if they select another song, it will overwrite the value in the field.
 - Start Octave: Same as above, expect this modifys how the notes are distributed among the two octaves of the organ. If the song seems to be playing in the wrong octave, go up or down one value in the dropdown.
 - Inner Key Delay: time in seconds between keydown and keyup
 - Outer Key Delay: time in seconds between keyup and keydown
 - Enable Keys: If disabled, no keyboard or mouse events will be simulated. Nothing will look like it is happening. This in primarily for debugging purposes.
 - Enable Sleep: If disabled, there will be no delays and no pauses for notes and rests
 - Reset Organ: If disabled, you have to use your interact key to get off the organ and to get back on. The program will always start as if it in the bottom left note.

## How to Use
 1. Choose your playlist directory and select a song
 2. Click the button labeled 'Start' at the bottom of the 'Main Settings'.
    1. This starts a listener to wait for specific key shortcuts
 3. To start playing the current song, press 'alt+b'
 4. To stop playing the current song, press 'alt+v'
 5. To stop the program, press 'alt+x'

 NOTE: This program is dumb as rocks. It will not know when you get off the organ and will continue. If you need to move, you'll have to stop the song or the program.

## Logic
This is kind of the logic used for the program
- When you hit start, it spawns a listenerThread for pynput to start a keylistener
- Shortcut that spawns a musicThread to play music
- Shortcut to kill musicThread (this stopping the music)
- Shortcut to stop the program (closes the program)
- The delays are necessary. Because if the key presses are too fast, then Sea of Thieves may not register it.
- Look-ahead logic had to be implemented to allow the program to move to the next note during rests (this is what makes the timings a lot better)
- MASSIVE NOTE: I kinda messed up and realised pretty late in development that I misunderstood how to utilize mido. I took the .time property and made it the length of the note instead of the time since the last message. This is probably one of the first things I'm going to fix, but I thought it would be important to note.

## License
At the moment, the below license applies to every user. Under no circumstance, can someone publish, or modify and publish, this code for commercial use. The only instance the license does not fully apply are in the case of entertainers/influencers/content creators. They are free to use/modify this application on their streams/videos despite the NonCommercial clause, but they cannot commercialize the distribution of the software (i.e. put my code, or any modifications fo the code, behind a paywall).

For credit, you only need to include a direct link to the github releases page.

License: https://creativecommons.org/licenses/by-nc-sa/4.0


## Other Notes
If you use a musicbox file that does not match one of my hashes, I am not responsible for it's actions. 
This program should not be considered hacking/cheating because it only simulates key presses and mouse button presses. Rare may have a different opinion on the matter. This statement will be updated if anything changes.
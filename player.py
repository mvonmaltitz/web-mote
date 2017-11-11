from subprocess import Popen, PIPE, call
from threading import Thread
from Queue import Queue
from Queue import Empty
import os
from os.path import abspath, dirname, join
import util, conf
from main import ServerStatus

############################################################
### MASSIVE AMOUNTS OF CONFIG (this should probably be in a DB somewhere)
############################################################
defaultPlayer = ["mplayer"]

### If `omxplayer` is available, use it for `mp4`s and `ogv`s (with audio output to the HDMI port)
### If not, use the default player for everything
play_youtube = abspath(join(dirname(__file__), 'play_youtube.sh'))
playerTable = {
        'm3u': ["mplayer", "-playlist"],
        'pls': ["mplayer", "-playlist"],
        'youtube': [play_youtube]
        }
try:
    call(["omxplayer"])
    playerTable.update({
        'mp4': ["omxplayer", "-o", "hdmi"],
        'ogv': ["omxplayer", "-o", "hdmi"],
        })
except:
    pass

commandTable = {
    play_youtube:
        {'step-backward': "\x1B[B", 'backward': "\x1B[D", 'forward': "\x1B[C", 'step-forward': "\x1B[A",
         ## down | left | right | up
         'volume-down': "9", 'volume-off': "m", 'volume-up': "0",
         'stop': "q", 'pause': " ", 'play': " "},
    'mplayer':
        {'step-backward': "\x1B[B", 'backward': "\x1B[D", 'forward': "\x1B[C", 'step-forward': "\x1B[A",
         ## down | left | right | up
         'volume-down': "9", 'volume-off': "m", 'volume-up': "0",
         'stop': "q", 'pause': " ", 'play': " "},
    'omxplayer':
        {'step-backward': "\x1B[B", 'backward': "\x1B[D", 'forward': "\x1B[C", 'step-forward': "\x1B[A",
         'volume-off': " ", #oxmplayer doesn't have a mute, so we pause instead
         'volume-down': "+", 'volume-up': "-",
         'stop': "q", 'pause': " ", 'play': " "}
    }
### END THE MASSIVE CONFIG
############################################################
try:
    commandQueue ## Global multi-process queue to accept player commands
    playQ        ## Global multi-process queue to accept files to play
except:
    commandQueue = Queue()
    playQ = Queue()

def listen():
    while True:
        aFile = playQ.get()
        if util.isInRoot(aFile):
            ServerStatus.send(util.nameToTitle(aFile), event='playing')
            playerCmd = __getPlayerCommand(aFile)
            cmdTable = commandTable[playerCmd[0]]
            playFile(playerCmd, aFile, cmdTable)
        elif(aFile.startswith("http")):
            ServerStatus.send(aFile, event='playing')
            playerCmd =  playerTable.get("youtube", defaultPlayer)
            cmdTable = commandTable[playerCmd[0]]
            playFile(playerCmd, aFile, cmdTable)


def playFile(playerCmd, fileName, cmdTable):
    __clearQueue(commandQueue)
    activePlayer = Popen(playerCmd + [fileName], stdin=PIPE)
    while activePlayer.poll() == None:
        try:
            res = commandQueue.get(timeout=1)
            activePlayer.stdin.write(cmdTable[res])
            if unicode(res) == unicode("stop"):
                try:
                  ServerStatus.send(util.nameToTitle(fileName), event="stopped")
                except:
                  pass
                __clearQueue(playQ)
                activePlayer.terminate()
                return False
        except Empty:
            None
    ServerStatus.send(util.nameToTitle(fileName), event="finished")
    return True

### Local Utility
def __getPlayerCommand(filename):
    global playerTable, defaultPlayer
    name, ext = os.path.splitext(filename)
    return playerTable.get(ext[1:], defaultPlayer)

def __clearQueue(q):
    while not q.empty():
        q.get()
    return True

### Start the player process
playerThread = Thread(target=listen, args=())
playerThread.daemon = True
playerThread.start()

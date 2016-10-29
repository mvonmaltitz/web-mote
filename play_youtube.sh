#!/bin/bash
BASH_PID=$$
youtube-dl -q -o- "$1" | mplayer -cache 8192  -novideo /dev/fd/3 3<&0 </proc/$BASH_PID/fd/0

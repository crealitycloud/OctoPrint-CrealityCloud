#!/bin/bash
DIR=`uname``getconf LONG_BIT`"_"`arch`
cd `dirname $0`/$DIR
./rtsp-simple-server
#ffmpeg -y -i /dev/video0 -s 640x480 -loglevel quiet -b:v 8000K -vcodec h264_omx -preset veryfast -f rtsp rtsp://127.0.0.1:554/ch0_0

#!/bin/bash
DIR=`dirname $0`"/"`uname``getconf LONG_BIT`"_"`arch`
if [ ! -d $DIR ];then
  cd `dirname $0`/Linux32_armv7l
else
  cd $DIR
fi
./rtsp-simple-server
#ffmpeg -y -i /dev/video0 -s 640x480 -loglevel quiet -b:v 8000K -vcodec h264_omx -preset veryfast -f rtsp rtsp://127.0.0.1:554/ch0_0

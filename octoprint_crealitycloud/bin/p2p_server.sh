#!/bin/bash
DIR=`dirname $0`"/"`uname``getconf LONG_BIT`"_"`arch`
if [ ! -d $DIR ];then
  cd `dirname $0`/Linux32_armv7l
else
  cd $DIR
fi
./p2pser_rtsp

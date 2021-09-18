#!/bin/bash
DIR=`uname``getconf LONG_BIT`"_"`arch`
cd `dirname $0`/$DIR
./GenerateIdentifier -a
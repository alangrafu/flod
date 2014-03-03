#!/bin/bash

##Meta installation script
##Author: Alvaro Graves <alvaro AT graves DOT cl>

GIT=$(which git)
FLOD_REPO=https://github.com/alangrafu/flod.git
FLOD_DIR=flod


if [ $GIT == "" ]; then
	echo "Please install git first"
	exit 1
fi

$GIT clone $FLOD_REPO

cd $FLOD_DIR
./installation/install.sh
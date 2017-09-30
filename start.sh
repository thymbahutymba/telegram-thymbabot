#!/bin/bash

/usr/bin/git fetch
/usr/bin/git reset —hard origin/master
cd ~/telegram-thymbabot
python3 __main__.py $@

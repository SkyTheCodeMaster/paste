#!/bin/bash
# We're assuming that python is already installed and on 3.11.3
python3.11 -m venv venv
source venv/bin/activate
python3.11 -m pip install -U pip
python3.11 -m pip install -r requirements.txt
# all done
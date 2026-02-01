#!/bin/bash

cd /home/jordan/source/repos/sleep-machine
source .venv/bin/activate
export ELEVENLABS_API_KEY=$(cat ELEVENLABS_API_KEY) EIGHTSLEEP_USERNAME=$(cat EIGHTSLEEP_USERNAME) EIGHTSLEEP_PASSWORD=$(cat EIGHTSLEEP_PASSWORD) GEMINI_API_KEY=$(cat GEMINI_API_KEY)
python main.py &> cron.log
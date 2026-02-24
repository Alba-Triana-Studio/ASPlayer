#!/bin/bash
export DISPLAY=:0
export KIVY_BCM_DISPMANX_ID=0
export KIVY_WINDOW=sdl2
export KIVY_GL_BACKEND=sdl2

echo "Starting ASPlayer..."
./venv/bin/python main.py

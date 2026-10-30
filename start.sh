#!/bin/bash
# Node.js server ko background me start karo
node server.js & 
# 3 second wait karo taaki server start ho jaye
sleep 3
# Python bot ko foreground me start karo
python3 WPSpread.py

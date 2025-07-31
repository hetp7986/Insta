#!/bin/bash

# Post-deploy setup
python -m playwright install --with-deps

# Start your server
python main.py

#!/bin/bash
git pull
./batch_process.py
jupyter nbconvert --to notebook --execute --inplace tidal_correction.ipynb linear_models.ipynb
git commit -am "auto update" --author="coastsat-bot <ubuntu@wave.storm-surge.cloud.edu.au>"
git push
#!/bin/bash
git pull
./batch_process.py || (echo "Batch process failed" && exit 1)
jupyter nbconvert --to notebook --execute --inplace tidal_correction.ipynb slope_estimation.ipynb linear_models.ipynb
git add .
git commit -am "auto update" --author="coastsat-bot <ubuntu@wave.storm-surge.cloud.edu.au>"
git push
TAG=$(date -u +"%Y-%m-%dT%H-%M-%SZ")
git tag $TAG
git push origin $TAG
gh release create $TAG --generate-notes

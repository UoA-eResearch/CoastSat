# CoastSat

This repository contains a [Leaflet.glify](https://github.com/robertleeplummerjr/Leaflet.glify) map ([`index.html`](index.html)) of shoreline change around the Pacific Rim. The user can click on a transect to view a plotly.js plot of change over time for that transect. The HTML and CSVs are hosted on GitHub Pages. It also contains code required to update data in New Zealand.

Installation: `pip install -r requirements.txt`

Everything in New Zealand was calculated by me ([@neon-ninja](https://github.com/neon-ninja)) using [CoastSat](https://github.com/kvos/CoastSat), everything outside New Zealand was calculated by [@kvos](https://github.com/kvos) and downloaded from this Zenodo link: https://zenodo.org/records/7758183. I used `batch_process.py` to automate CoastSat, as well as run multiple sites in parallel. This file uses a Google Earth Engine service account to download satellite imagery, to allow for automated processing. I used the [NIWA Tide API](https://developer.niwa.co.nz/docs/tide-api/1/overview) for tidal corrections. See `tidal_correction.ipynb` for specifics.

New Zealand results were calculated on the `wave.storm-surge.cloud.edu.au` NeCTAR VM (32 CPUs, 128GB RAM). The total size of the data folder is 1.3TB. The `.gitignore` is used to only track the *.csv results within this data folder with git, everything else in the data folder is gitignored.

Additionally, I've configured a cron job:

```bash
# m h  dom mon dow   command
  0 0  1   *   *     cd CoastSat && ./update.sh > update.log
```

On the above mentioned NeCTAR VM, which should, on the 1st of every month:
- Download any new Landsat satellite imagery
- Run CoastSat to classify these images, find the shorelines, and transect intersects
- Run tide correction
- Recalculate the linear trend
- Commit the new results to this repo
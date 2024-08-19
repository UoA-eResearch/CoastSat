#!/usr/bin/env python3

import os
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import pandas as pd
from coastsat import SDS_download, SDS_preprocess, SDS_shoreline, SDS_tools, SDS_transects
import geopandas as gpd
from tqdm.auto import tqdm
import ee
from shapely.ops import split
from datetime import datetime, timedelta
from shapely import line_merge
import time
from tqdm.contrib.concurrent import process_map

start = time.time()

CRS = 2193

# Earth engine service account
service_account = 'service-account@iron-dynamics-294100.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, '.private-key.json')
ee.Initialize(credentials)

print(f"{time.time() - start}: Logged into EE")

# These polygon bounding boxes define where to download imagery
poly = gpd.read_file("polygons.geojson")
poly = poly[poly.id.str.startswith("nzd")]
poly.set_index("id", inplace=True)

# These are reference shorelines
shorelines = gpd.read_file("shorelines.geojson")
shorelines = shorelines[shorelines.id.str.startswith("nzd")].to_crs(CRS)
shorelines.set_index("id", inplace=True)

# Transects, origin is landward
transects_gdf = gpd.read_file("transects.geojson").to_crs(CRS).drop_duplicates(subset="id")
transects_gdf.set_index("id", inplace=True)

print(f"{time.time() - start}: Reference polygons and shorelines loaded")

def process_site(sitename):
    print(f"Now processing {sitename}")

    df = pd.read_csv(f"data/{sitename}/transect_time_series.csv")
    df.set_index("Unnamed: 0", inplace=True)
    df.dates = pd.to_datetime(df.dates)

    inputs = {
        "polygon": list(poly.geometry[sitename].exterior.coords),
        "dates": [str(df.dates.max().date() + timedelta(days=1)), '2030-12-30'], # All available imagery
        "sat_list": ['L5','L7','L8','L9'],
        "sitename": sitename,
        "filepath": 'data',
        "landsat_collection": 'C02',
    }
    #result = SDS_download.check_images_available(inputs)
    metadata = SDS_download.retrieve_images(inputs)
    #metadata = SDS_download.get_metadata(inputs)

    # settings for the shoreline extraction
    settings = {
        # general parameters:
        'cloud_thresh': 0.1,        # threshold on maximum cloud cover
        'dist_clouds': 300,         # ditance around clouds where shoreline can't be mapped
        'output_epsg': CRS,       # epsg code of spatial reference system desired for the output
        # quality control:
        'check_detection': False,    # if True, shows each shoreline detection to the user for validation
        'adjust_detection': False,  # if True, allows user to adjust the postion of each shoreline by changing the threhold
        'save_figure': True,        # if True, saves a figure showing the mapped shoreline for each image
        # [ONLY FOR ADVANCED USERS] shoreline detection parameters:
        'min_beach_area': 1000,     # minimum area (in metres^2) for an object to be labelled as a beach
        'min_length_sl': 500,       # minimum length (in metres) of shoreline perimeter to be valid
        'cloud_mask_issue': False,  # switch this parameter to True if sand pixels are masked (in black) on many images
        'sand_color': 'default',    # 'default', 'latest', 'dark' (for grey/black sand beaches) or 'bright' (for white sand beaches)
        'pan_off': False,           # True to switch pansharpening off for Landsat 7/8/9 imagery
        's2cloudless_prob': 40,      # threshold to identify cloud pixels in the s2cloudless probability mask
        # add the inputs defined previously
        'inputs': inputs
    }

    # [OPTIONAL] preprocess images (cloud masking, pansharpening/down-sampling)
    #SDS_preprocess.save_jpg(metadata, settings, use_matplotlib=True)

    transects_at_site = transects_gdf[transects_gdf.site_id == sitename]
    transects = {}
    for transect_id in transects_at_site.index:
        transects[transect_id] = np.array(transects_at_site.geometry[transect_id].coords)

    ref_sl = np.array(line_merge(split(shorelines.geometry[sitename], transects_at_site.unary_union)).coords)

    settings["max_dist_ref"] = 100
    settings["reference_shoreline"] = np.flip(ref_sl)

    output = SDS_shoreline.extract_shorelines(metadata, settings)
    print(f"Have {len(output['shorelines'])} new shorelines for {sitename}")
    if not output["shorelines"]:
        return

    # Have to flip to get x,y?
    output['shorelines'] = [np.flip(s) for s in output['shorelines']]

    output = SDS_tools.remove_duplicates(output) # removes duplicates (images taken on the same date by the same satellite)
    output = SDS_tools.remove_inaccurate_georef(output, 10) # remove inaccurate georeferencing (set threshold to 10 m)

    settings_transects = { # parameters for computing intersections
                          'along_dist':          25,        # along-shore distance to use for computing the intersection
                          'min_points':          3,         # minimum number of shoreline points to calculate an intersection
                          'max_std':             15,        # max std for points around transect
                          'max_range':           30,        # max range for points around transect
                          'min_chainage':        -100,      # largest negative value along transect (landwards of transect origin)
                          'multiple_inter':      'auto',    # mode for removing outliers ('auto', 'nan', 'max')
                          'auto_prc':            0.1,       # percentage of the time that multiple intersects are present to use the max
                        }
    cross_distance = SDS_transects.compute_intersection_QC(output, transects, settings_transects) 

    # save a .csv file for Excel users
    out_dict = dict([])
    out_dict['dates'] = output['dates']
    for key in transects.keys():
        out_dict[key] = cross_distance[key]
        
    new_results = pd.DataFrame(out_dict)
    if len(new_results) == 0:
        return
    df = pd.concat([df, new_results], ignore_index=True)
    df.sort_values("dates", inplace=True)
    fn = os.path.join(settings['inputs']['filepath'],settings['inputs']['sitename'],
                      'transect_time_series.csv')
    df.to_csv(fn, sep=',')
    print(f'{sitename} is done! Time-series of the shoreline change along the transects saved as:{fn}')

process_map(process_site, poly.index, max_workers=32)
#!/usr/bin/env python3

import geopandas as gpd
import pandas as pd
from tqdm.auto import tqdm
from tqdm.contrib.concurrent import process_map
from shapely import line_interpolate_point

transects = gpd.read_file("transects_extended.geojson").drop_duplicates(subset="id")
transects.set_index("id", inplace=True)
transects = transects[transects.site_id.str.startswith("nzd")].copy()
transects["land_x"] = transects.geometry.apply(lambda x: x.coords[0][0])
transects["land_y"] = transects.geometry.apply(lambda x: x.coords[0][1])
transects["sea_x"] = transects.geometry.apply(lambda x: x.coords[-1][0])
transects["sea_y"] = transects.geometry.apply(lambda x: x.coords[-1][1])
transects["center_x"] = (transects["land_x"] + transects["sea_x"]) / 2
transects["center_y"] = (transects["land_y"] + transects["sea_y"]) / 2
transects.to_excel("transects.xlsx")

transects_2193 = transects.to_crs(2193)

def process_site(site_id):
  with pd.ExcelWriter(f'data/{site_id}/{site_id}.xlsx') as writer:
    intersects = pd.read_csv(f"data/{site_id}/transect_time_series_tidally_corrected.csv")
    intersects.set_index("dates", inplace=True)
    intersects.to_excel(writer, sheet_name="Intersects")
    tides = pd.read_csv(f"data/{site_id}/tides.csv")
    tides.to_excel(writer, sheet_name="Tides", index=False)
    transects_at_site = transects[transects.site_id == site_id]
    transects_at_site.to_excel(writer, sheet_name="Transects")
    transect_ids = list(transects_at_site.index)
    for transect_id in transect_ids:
      intersects[transect_id] = gpd.GeoSeries(line_interpolate_point(transects_2193.geometry[transect_id], intersects[transect_id]), crs=2193).to_crs(4326).apply(lambda p: f"{p.y},{p.x}" if p else None)
    intersects.to_excel(writer, sheet_name="Intersect points")

process_map(process_site, transects.site_id.unique(), max_workers=32)
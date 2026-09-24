"""Script to acquire authoritative ESA WorldCover 10m land cover data for Giaspura study area."""

import os
import rasterio
from rasterio.windows import from_bounds
from rasterio.crs import CRS

# Study area bounds around Giaspura, Ludhiana (EPSG:4326)
# Centered around lat 30.875625, lon 75.898481
LON_MIN, LAT_MIN = 75.75, 30.75
LON_MAX, LAT_MAX = 76.05, 31.00

ESA_WORLDCOVER_COG_URL = (
    "https://esa-worldcover.s3.amazonaws.com/v200/2021/map/"
    "ESA_WorldCover_10m_2021_v200_N30E075_Map.tif"
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "landcover")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "giaspura_landcover_esa.tif")


def acquire_landcover_extract(output_path: str = OUTPUT_FILE):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"Reading ESA WorldCover window from: {ESA_WORLDCOVER_COG_URL}")
    with rasterio.open(ESA_WORLDCOVER_COG_URL) as src:
        window = from_bounds(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, src.transform)
        # Snap window to integers
        window = window.round_lengths().round_offsets()
        data = src.read(1, window=window)
        win_transform = src.window_transform(window)
        
        meta = src.meta.copy()
        meta.update({
            "height": window.height,
            "width": window.width,
            "transform": win_transform,
            "crs": src.crs,
            "driver": "GTiff",
            "compress": "lzw"
        })
        
        with rasterio.open(output_path, "w", **meta) as dst:
            dst.write(data, 1)
            
    print(f"Successfully saved ESA WorldCover extract to: {output_path}")
    print(f"Dimensions: {data.shape}, file size: {os.path.getsize(output_path)} bytes")


if __name__ == "__main__":
    acquire_landcover_extract()

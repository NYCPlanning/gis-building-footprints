import geopandas as gpd
import os
import shutil
import datetime
import configparser
from pathlib import Path
import logging

start_time = datetime.datetime.now().replace(microsecond=0)

DATA_DIRECTORY = Path(__file__).parent.parent / "data"
CONFIG_FILE = Path(__file__).parent.parent / "ini" / "config.ini"


def initialize_logging(log_filename: str, log_level="INFO", log_path="log"):
    """Initialize logging, output to file and console.
    source: https://stackoverflow.com/a/46098711
    source: https://github.com/NYCPlanning/db-template-repo/blob/main/python/run_logging.py

    Args:
        log_filename (str): Log filename. Do not include containing path
        log_level (str, optional): Logging level. Defaults to "INFO"
        log_path (str, optional): Path to log file, can be rel or abs. Defaults to "log"
    """
    LOGGING_LEVEL_DEFAULT = log_level

    log_filename = Path(log_path, log_filename)

    logging.basicConfig(
        level=LOGGING_LEVEL_DEFAULT,
        format="%(asctime)s :: %(levelname)s :: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(log_filename), logging.StreamHandler()],
    )
    logging.info("{delim} Script Starting {delim}".format(delim="=" * 15))


def initialize_config(config_file_path: Path):
    """_summary_

    Args:
        config_file_path (Path): _description_

    Returns:
        _type_: _description_
    """
    logging.debug("Initializing configuration file")
    config = configparser.ConfigParser()
    config.read(config_file_path)

    STAGING_PATH = config.get("PATHS", "STAGING_PATH")
    BASE_URL = config.get("URLS", "BASE_URL")
    POLYGON_FOURFOUR = config.get("URLS", "POLYGON_FOURFOUR")
    POLYGON_SHAPEFILE = config.get("URLS", "POLYGON_SHAPEFILE")
    POINT_FOURFOUR = config.get("URLS", "POINT_FOURFOUR")
    POINT_SHAPEFILE = config.get("URLS", "POINT_SHAPEFILE")

    return (
        STAGING_PATH,
        BASE_URL,
        POLYGON_FOURFOUR,
        POLYGON_SHAPEFILE,
        POINT_FOURFOUR,
        POINT_SHAPEFILE,
    )


def deploy_staging_dirs(
    staging_root: Path,
    product_dir_name: str,
    version: Path = None,
    dir_list: list = ["csv", "gdb", "metadata", "shp", "web", "raw_data"],
) -> Path:
    """Create staging directory for script operations. Notably, destructs product path if exists already.
    Output directory in following format: {parent}\{product_name}\{version}

    Args:
        staging_root (Path): path of containing folder (i.e. {parent} in format ex. above)
        product_dir_name str: product name (i.e. {product_name} in format ex. above)
        version (Path): version (fmt: 23v2) (i.e. {product_name} in format ex. above)

    Returns:
        (Path): Path of newly created directory
    """
    product_path = Path(staging_root, product_dir_name)
    if version is not None:
        local_version_dir = Path(product_path, version)
    else:
        local_version_dir = product_path
    logging.info(f"Deploy staging dir: {local_version_dir}")

    if not Path.is_dir(staging_root):
        Path.mkdir(staging_root)
    if Path.is_dir(product_path):
        logging.debug(f"Deleting tree: {product_path}")
        shutil.rmtree(product_path)
    Path.mkdir(Path(product_path, local_version_dir), parents=True)
    for dir_name in dir_list:
        os.mkdir(os.path.join(local_version_dir, dir_name))

    return local_version_dir


try:
    initialize_logging(log_filename="bldg_footprint_pull.log", log_level="DEBUG")
    (
        STAGING_PATH,
        BASE_URL,
        POLYGON_FOURFOUR,
        POLYGON_SHAPEFILE,
        POINT_FOURFOUR,
        POINT_SHAPEFILE,
    ) = initialize_config(config_file_path=CONFIG_FILE)

except Exception:
    logging.exception()


# Delete previous directory and files within
try:
    deploy_staging_dirs(
        staging_root=DATA_DIRECTORY,
        product_dir_name="bldg_footprints",
        dir_list=[],
    )
except Exception:
    logging.exception()

limit = 2_000_000
file_type = ".geojson"
dtypes = {
    "name": "object",
    "base_bbl": "object",
    "heightroof": "object",
    "mpluto_bbl": "object",
    "cnstrct_yr": "object",
    "globalid": "object",
    "lststatype": "object",
    "feat_code": "object",
    "groundelev": "object",
    "geomsource": "object",
    "bin": "object",
    "lstmoddate": "object",
    "doitt_id": "object",
    "geometry": "geometry",
}

file_details = {
    "polygons": [POLYGON_FOURFOUR, POLYGON_SHAPEFILE],
    "points": [POINT_FOURFOUR, POINT_SHAPEFILE],
}

for geom_type, detail_list in file_details.items():
    fourfour, outname = detail_list

    url = f"{BASE_URL}/{fourfour}{file_type}?$limit={limit}"

    logging.info(f"Downloading the {geom_type} dataset")
    logging.info(f"From: {url}")

    gdf = gpd.read_file(filename=url, columns=list(dtypes.keys()))
    gdf = gdf.astype(dtypes)
    gdf.to_file(filename=DATA_DIRECTORY / "bldg_footprints" / f"{outname}")


end_time = datetime.datetime.now().replace(microsecond=0)
duration = end_time - start_time
logging.info("{delim} Runtime: {dur} {delim}\n\n".format(delim="=" * 15, dur=duration))

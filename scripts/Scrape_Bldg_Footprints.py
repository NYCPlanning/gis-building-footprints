'''
Script requires Python 3. All modules used are included within base Esri environment.
'''

import configparser
import datetime
import os
import shutil
import sys
import time
import traceback
import zipfile

import arcpy
import requests

try:

    # Set configuration file path
    config = configparser.ConfigParser()
    config.read(r'ini\config.ini')

    # Set log path
    log_path = config.get("PATHS", "scrape_log_path")
    log = open(log_path, "a")

    # Define zip, sde, and missing bbls text file paths
    zip_dir_path = config.get("PATHS", "zip_dir_path")
    zip_path = os.path.join(zip_dir_path, "Building_Footprints.zip")
    sde_path = config.get('PATHS', 'sde_path')
    bldg_url = config.get("URLS", "bldg_url")

    # Set start time
    StartTime = datetime.datetime.now().replace(microsecond=0)
    # Write start time to log
    log.write(str(StartTime) + "\t")

    # Re-generate temporary directories

    if arcpy.Exists(zip_dir_path):
        print("Old temporary directory still exists. Deleting now.")
        shutil.rmtree(zip_dir_path)
        print("Re-creating temporary directory")
        time.sleep(.01)
        os.mkdir(zip_dir_path)
    else:
        print("Temporary directory does not exist. Generating now.")
        os.mkdir(zip_dir_path)

    # Set proxy credentials for bypassing firewall

    print("Setting proxy credential info")
    proxies = {
        'http': config.get("PROXIES", "http_proxy"),
        'https': config.get("PROXIES", "https_proxy"),
    }
    print("Proxy creds set")

    # Begin downloading Building Footprints to temporary directory on C: drive

    print("Requesting Building Footprints shapefile")
    # Establish requests object for connection to download URL
    r = requests.get(bldg_url,
                     proxies=proxies,
                     allow_redirects=True,
                     verify=True
                     )
    r.raise_for_status()

    print("Request for Building Footprints returned status code: {}".format(r.status_code))

    # Write output to temporary zip file in C:\temp\building_footprints

    c = r.content
    print("Contents of request object below")
    print("Downloading shapefile from NYC Open Data Socrata platform")

    open(zip_path, 'wb').write(c)
    print("Shapefile downloaded")

    zip = zipfile.ZipFile(zip_path)

    # Extract zip to C:\temp\building_footprints directory

    print("Extracting zipped Building Footprint files")
    zip.extractall(zip_dir_path)
    print("Export complete")

    # Identify polygon shapefile for processing

    exported_shape_list = []
    print("Parsing exports for polygon shapefile")
    for f in os.listdir(zip_dir_path):
        if f.endswith(".shp"):
            file_name = f.split(".")[0]
            output_desc = arcpy.Describe(os.path.join(zip_dir_path, f))
            file_type = output_desc.shapeType
            if file_type == "Polygon" and f.endswith(".shp"):
                exported_shape_list.append(file_name)

    print(exported_shape_list[0])

    # Rename extracted files to match standardized naming convention

    for f in os.listdir(zip_dir_path):
        if "{}".format(exported_shape_list[0]) in f and "_p" not in f:
            print("Renaming {} to {}".format(os.path.join(zip_dir_path, f),
                                             os.path.join(zip_dir_path, f.replace(exported_shape_list[0],
                                                                                     "BUILDING_FOOTPRINTS_PLY"))))
            if os.path.exists(os.path.join(zip_dir_path, f.replace(exported_shape_list[0], "BUILDING_FOOTPRINTS_PLY"))):
                arcpy.Delete_management(os.path.join(zip_dir_path,
                                                          f.replace(exported_shape_list[0], "BUILDING_FOOTPRINTS_PLY")))
                os.rename(os.path.join(zip_dir_path, f),
                          os.path.join(zip_dir_path, f.replace(exported_shape_list[0],
                                                                  "BUILDING_FOOTPRINTS_PLY")))
            else:
                os.rename(os.path.join(zip_dir_path, f),
                          os.path.join(zip_dir_path, f.replace(exported_shape_list[0],
                                                                  "BUILDING_FOOTPRINTS_PLY")))

        if "{}_p".format(exported_shape_list[0]) in f:
            print("Renaming {} to {}".format(os.path.join(zip_dir_path, f),
                                             os.path.join(zip_dir_path, f.replace(exported_shape_list[0],
                                                                                     "BUILDING_FOOTPRINTS_PT"))))
            if os.path.exists(os.path.join(zip_dir_path,
                                           f.replace("{}_p".format(exported_shape_list[0]), "BUILDING_FOOTPRINTS_PT"))):
                arcpy.Delete_management(os.path.join(zip_dir_path,
                                                          f.replace("{}_p".format(exported_shape_list[0]),
                                                                       "BUILDING_FOOTPRINTS_PT")))
                os.rename(os.path.join(zip_dir_path, f),
                          os.path.join(zip_dir_path, f.replace("{}_p".format(exported_shape_list[0]),
                                                                  "BUILDING_FOOTPRINTS_PT")))
            else:
                os.rename(os.path.join(zip_dir_path, f),
                          os.path.join(zip_dir_path, f.replace("{}_p".format(exported_shape_list[0]),
                                                                  "BUILDING_FOOTPRINTS_PT")))

    EndTime = datetime.datetime.now().replace(microsecond=0)
    print("Script runtime: {}".format(EndTime - StartTime))

    log.write(str(EndTime) + "\t" + str(EndTime - StartTime) + "\n")
    log.close()

except:
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]

    pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
    msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages() + "\n"

    print(pymsg)
    print(msgs)

    log.write("" + pymsg + "\n")
    log.write("" + msgs + "")
    log.write("\n")
    log.close()
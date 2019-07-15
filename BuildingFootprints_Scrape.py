# Utilizes Python 2, but requires that the requests library is installed in the appropriate default Python2 installation
# path. If this custom Python distribution is not available and it is not possible to install the requests library
# must utilize version of Python 3 with requests library (ArcGIS Pro Python installation has this library)

import requests, os, shutil, zipfile, arcpy, datetime, sys, traceback, ConfigParser, xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

try:
    # Set configuration file path
    config = ConfigParser.ConfigParser()
    config.read(r'G:\SCRIPTS\Open_Data_Bldg_Footprints_Scrape\ini\BuildingFootprint_Scrape_config.ini')

    # Set log path
    log_path = config.get("PATHS", "log_path")
    log = open(log_path, "a")

    # Define zip and sde paths
    zip_dir_path = config.get("PATHS", "zip_dir_path")
    zip_path = os.path.join(zip_dir_path, "Building_Footprints.zip")
    sde_path = config.get("PATHS", "sde_path")
    lyr_dir_path = config.get("PATHS", 'lyr_dir_path')

    # Disconnect all users
    arcpy.AcceptConnections(sde_path, False)
    arcpy.DisconnectUser(sde_path, "ALL")

    # Set start time
    StartTime = datetime.datetime.now().replace(microsecond=0)

    # Set translator path for exporting metdata from SDE

    print("Setting arcdir")
    Arcdir = arcpy.GetInstallInfo("desktop")["InstallDir"]
    translator = Arcdir + "Metadata/Translator/ARCGIS2FGDC.xml"
    remove_geoprocess_xslt = Arcdir + "Metadata/Stylesheets/gpTools/remove geoprocessing history.xslt"
    remove_lcl_storage_xslt = Arcdir + "Metadata/Stylesheets/gpTools/remove local storage info.xslt"
    print("Arcdir set")

    # Re-generate temporary directory

    if arcpy.Exists(zip_dir_path):
        print("Old temporary directory still exists. Deleting now.")
        arcpy.Delete_management(zip_dir_path)
        print("Re-creating temporary directory")
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
    r = requests.get(config.get("URLS", "bldg_url"),
                     proxies=proxies,
                     allow_redirects=True,
                     verify=False)
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
    for file in os.listdir(zip_dir_path):
        if file.endswith(".shp"):
            file_name = file.split(".")[0]
            output_desc = arcpy.Describe(os.path.join(zip_dir_path, file))
            file_type = output_desc.shapeType
            if file_type == "Polygon" and file.endswith(".shp"):
                exported_shape_list.append(file_name)

    print(exported_shape_list[0])

    arcpy.env.workspace = zip_dir_path
    arcpy.env.overwriteOutput = True

    # Rename extracted files to match standardized naming convention

    for file in os.listdir(zip_dir_path):
        if "{}".format(exported_shape_list[0]) in file and "_p" not in file:
            print("Renaming {} to {}".format(os.path.join(zip_dir_path, file),
                                             os.path.join(zip_dir_path, file.replace(exported_shape_list[0],
                                                                                     "BUILDING_FOOTPRINTS_PLY"))))
            if os.path.exists(os.path.join(zip_dir_path, file.replace(exported_shape_list[0], "BUILDING_FOOTPRINTS_PLY"))):
                arcpy.Delete_management(os.path.join(zip_dir_path,
                                                          file.replace(exported_shape_list[0], "BUILDING_FOOTPRINTS_PLY")))
                os.rename(os.path.join(zip_dir_path, file),
                          os.path.join(zip_dir_path, file.replace(exported_shape_list[0],
                                                                  "BUILDING_FOOTPRINTS_PLY")))
            else:
                os.rename(os.path.join(zip_dir_path, file),
                          os.path.join(zip_dir_path, file.replace(exported_shape_list[0],
                                                                  "BUILDING_FOOTPRINTS_PLY")))

        if "{}_p".format(exported_shape_list[0]) in file:
            print("Renaming {} to {}".format(os.path.join(zip_dir_path, file),
                                             os.path.join(zip_dir_path, file.replace(exported_shape_list[0],
                                                                                     "BUILDING_FOOTPRINTS_PT"))))
            if os.path.exists(os.path.join(zip_dir_path,
                                           file.replace("{}_p".format(exported_shape_list[0]), "BUILDING_FOOTPRINTS_PT"))):
                arcpy.Delete_management(os.path.join(zip_dir_path,
                                                          file.replace("{}_p".format(exported_shape_list[0]),
                                                                       "BUILDING_FOOTPRINTS_PT")))
                os.rename(os.path.join(zip_dir_path, file),
                          os.path.join(zip_dir_path, file.replace("{}_p".format(exported_shape_list[0]),
                                                                  "BUILDING_FOOTPRINTS_PT")))
            else:
                os.rename(os.path.join(zip_dir_path, file),
                          os.path.join(zip_dir_path, file.replace("{}_p".format(exported_shape_list[0]),
                                                                  "BUILDING_FOOTPRINTS_PT")))

    # Scrape update dates from item description due to lack of publication date in metadata

    def extract_update(config_url_tag):
        # Establish connection to Open Data platform
        print("Establishing connection to ")
        r = requests.get(config.get('URLS', config_url_tag),
                         proxies=proxies,
                         allow_redirects=True,
                         verify=False)
        c = r.content
        soup = BeautifulSoup(c, 'html.parser')
        update_date = soup.find('span', 'aboutUpdateDate').getText()
        return(update_date)

    last_update_date = extract_update('update_url')
    last_update_date_dt = datetime.datetime.strptime(last_update_date, '%b %d %Y')
    last_update_date_str = datetime.datetime.strftime(last_update_date_dt, '%Y%m%d')

    today = datetime.datetime.today()
    today = datetime.datetime.strftime(today, '%b %d %Y')

    # Export renamed shapefiles to Production SDE

    arcpy.env.workspace = sde_path
    arcpy.env.overwriteOutput = True

    dir = arcpy.GetInstallInfo("desktop")["InstallDir"]
    xslt_geoprocess = dir + config.get("PATHS", "metadata_geoprocessing_path")
    xslt_storage = dir + config.get("PATHS", "metadata_storage_path")


    def export_featureclass(input_path, output_name):
        arcpy.env.workspace = sde_path
        arcpy.env.overwriteOutput = True
        print("Modifying last update date and download date within Metadata citations and summary")
        tree = ET.parse(os.path.join(zip_dir_path, '{}.xml'.format(input_path)))
        root = tree.getroot()
        for pubdate in root.iter('pubdate'):
            pubdate.text = last_update_date_str
        for pubdate in root.iter('pubDate'):
            pubdate.text = last_update_date_str
        for descrip in root.iter('abstract'):
            descrip.text = descrip.text + ' Dataset last updated: {}. Dataset last downloaded: {}'.format(last_update_date_dt, today)
        for descrip in root.iter('idAbs'):
            descrip.text = descrip.text + ' Dataset last updated: {}. Dataset last downloaded: {}'.format(
                last_update_date_dt, today)

        tree.write(os.path.join(zip_dir_path, "{}.xml".format(input_path)))
        print("Exporting shapefile to SDE PROD as {}".format(output_name))
        arcpy.FeatureClassToFeatureClass_conversion(os.path.join(zip_dir_path, input_path), sde_path, output_name)
        print("Removing local storage info")
        arcpy.XSLTransform_conversion(os.path.join(sde_path, output_name), xslt_storage, os.path.join(zip_dir_path, "{}_storage.xml".format(input_path)))
        print("Removing geoprocessing info")
        arcpy.XSLTransform_conversion(os.path.join(zip_dir_path, "{}_storage.xml".format(input_path)), xslt_geoprocess, os.path.join(zip_dir_path, "{}_geoprocess.xml".format(input_path)))
        print("Importing final metadata to SDE PROD")
        arcpy.MetadataImporter_conversion(os.path.join(zip_dir_path, "{}_geoprocess.xml".format(input_path)), os.path.join(sde_path, output_name))
        arcpy.UpgradeMetadata_conversion(os.path.join(sde_path, output_name), 'FGDC_TO_ARCGIS')


    bldg_footprint_poly_path = os.path.join(zip_dir_path, "BUILDING_FOOTPRINTS_PLY.shp")
    bldg_footprint_pt_path = os.path.join(zip_dir_path, "BUILDING_FOOTPRINTS_PT.shp")

    print("Exporting Building Footprints Polygon to Production SDE")
    export_featureclass(bldg_footprint_poly_path, "NYC_Building_Footprints_Poly")
    print("Exporting Building Footprints Points to Production SDE")
    export_featureclass(bldg_footprint_pt_path, "NYC_Building_Footprints_Points")


    # Export SDE Feature Classes as BIN only version for Building background and Building group layers

    def export_reduced_featureclass(input_path, output_name):
        print("Exporting Building Footprint - BIN only feature class to SDE PROD")
        if arcpy.Exists(input_path):
            print("Adding requisite fields to output feature class")
            fms = arcpy.FieldMappings()
            fm = arcpy.FieldMap()
            fm.addInputField(input_path, "BIN")
            fms.addFieldMap(fm)
            print("Requisite fields added to output feature class")
            print("Exporting reduced NYC Building Footprint Polygon feature class on SDE PROD")
            arcpy.FeatureClassToFeatureClass_conversion(input_path, sde_path, output_name, field_mapping=fms)
            print("Reduced NYC Building Footprint Polygon feature class exported to SDE PROD")
            print("Removing local storage info from imported feature class metadata")
            arcpy.XSLTransform_conversion(os.path.join(sde_path, output_name), xslt_storage,
                                          os.path.join(zip_dir_path, "{}_storage.xml".format(input_path.replace(".shp", ""))))
            print("Removing geoprocessing info from imported feature class metadata")
            arcpy.XSLTransform_conversion(os.path.join(zip_dir_path, "{}_storage.xml".format(input_path.replace(".shp", ""))),
                                          xslt_geoprocess,
                                          os.path.join(zip_dir_path, "{}_geoproc.xml".format(input_path.replace(".shp", ""))))
            arcpy.MetadataImporter_conversion(
                os.path.join(zip_dir_path, "{}_geoproc.xml".format(input_path.replace(".shp", ""))),
                os.path.join(sde_path, output_name))

    print("Exporting Building Footprints BIN Only to Production SDE")
    export_reduced_featureclass("NYC_Building_Footprints_Poly", "NYC_Building_Footprints_Poly_BIN_Only")


    # Generate layers and xml stand-alone files for Buildings and Lots

    print("Generating stand-alone layer and xml files for M:\GIS\DATA directory")
    def distribute_layer_metadata(in_path, out_path):
        print("Exporting xml file on M: drive - {}".format(in_path))
        arcpy.ExportMetadata_conversion(in_path, translator, out_path.replace('.lyr', '.lyr.xml'))

    arcpy.env.workspace = lyr_dir_path
    arcpy.env.overwriteOutput = True

    distribute_layer_metadata(os.path.join(sde_path, 'NYC_Building_Footprints_Poly'),
                            os.path.join(lyr_dir_path, 'Building footprints.lyr'))
    distribute_layer_metadata(os.path.join(sde_path, 'NYC_Building_Footprints_Points'),
                            os.path.join(lyr_dir_path, 'Building footprint centroids.lyr'))
    distribute_layer_metadata(os.path.join(sde_path, 'NYC_Building_Footprints_Poly_BIN_Only'),
                            os.path.join(lyr_dir_path, 'Building footprints BIN Only.lyr'))

    # Reconnect users
    arcpy.AcceptConnections(sde_path, True)

    EndTime = datetime.datetime.now().replace(microsecond=0)
    print("Script runtime: {}".format(EndTime - StartTime))

    log.write(str(StartTime) + "\t" + str(EndTime) + "\t" + str(EndTime - StartTime) + "\n")
    log.close()

except:

    # Reconnect users
    arcpy.AcceptConnections(sde_path, True)

    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]

    pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
    msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages() + "\n"

    print pymsg
    print msgs

    log.write("" + pymsg + "\n")
    log.write("" + msgs + "")
    log.write("\n")
    log.close()
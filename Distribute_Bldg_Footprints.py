# Utilizes Python 2 32-bit version in order to access metadata functionality not present on 64-bit version or Python 3
# version

import requests, os, zipfile, arcpy, datetime, sys, traceback, ConfigParser, xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

try:
    # Set configuration file path
    config = ConfigParser.ConfigParser()
    config.read(r'BuildingFootprint_config_template.ini')

    # Set log path
    log_path = config.get("PATHS", "distribute_log_path")
    log = open(log_path, "a")

    # Define zip, sde, and metadata paths
    zip_dir_path = config.get("PATHS", "zip_dir_path")
    zip_path = os.path.join(zip_dir_path, "Building_Footprints.zip")
    sde_path = config.get("PATHS", "sde_path")
    lyr_dir_path = config.get("PATHS", 'lyr_dir_path')
    template_path = config.get("PATHS", 'template_path')

    # Disconnect all users
    arcpy.AcceptConnections(sde_path, False)
    arcpy.DisconnectUser(sde_path, "ALL")

    # Set start time
    StartTime = datetime.datetime.now().replace(microsecond=0)

    # Set translator path for exporting metdata from SDE

    print("Setting arcdir")
    Arcdir = arcpy.GetInstallInfo("desktop")["InstallDir"]
    translator = Arcdir + "Metadata/Translator/ARCGIS2FGDC.xml"
    xslt_geoprocess = Arcdir + "Metadata/Stylesheets/gpTools/remove geoprocessing history.xslt"
    xslt_storage = Arcdir + "Metadata/Stylesheets/gpTools/remove local storage info.xslt"
    print("Arcdir set")

    # Allow for overwriting in SDE PROD environment

    arcpy.env.workspace = sde_path
    arcpy.env.overwriteOutput = True

    # Set proxy credentials for bypassing firewall

    print("Setting proxy credential info")
    proxies = {
        'http': config.get("PROXIES", "http_proxy"),
        'https': config.get("PROXIES", "https_proxy"),
    }
    print("Proxy creds set")

    # Scrape update dates from item description due to lack of publication date in metadata

    def extract_update(config_url_tag):
        # Establish connection to Open Data platform
        print("Establishing connection")
        r = requests.get(config.get('URLS', config_url_tag),
                         proxies=proxies,
                         allow_redirects=True,
                         verify=True)
        c = r.content
        soup = BeautifulSoup(c, 'html.parser')
        update_date = soup.find('span', 'aboutUpdateDate').getText()
        return (update_date)


    last_update_date = extract_update('update_url')
    last_update_date_dt = datetime.datetime.strptime(last_update_date, '%b %d %Y')
    last_update_date_str = datetime.datetime.strftime(last_update_date_dt, '%Y%m%d')
    last_update_date_meta = datetime.datetime.strftime(last_update_date_dt, '%b %d %Y')

    today = datetime.datetime.today()
    today = datetime.datetime.strftime(today, '%b %d %Y')

    # Export renamed shapefiles to Production SDE

    def export_featureclass(input_path, output_name):
        print("Upgrading downloaded metadata to ArcGIS standard")
        arcpy.UpgradeMetadata_conversion(input_path, 'FGDC_TO_ARCGIS')
        print("Downloaded metadata upgraded to ArcGIS standard")
        print("Overwriting original metadata with DCP standard")
        arcpy.MetadataImporter_conversion(os.path.join(template_path, '{}.xml'.format(output_name)),
                                          input_path)
        print("Original metadata overwritten")
        tree = ET.parse('{}.xml'.format(input_path))
        root = tree.getroot()
        for title in root.iter('title'):
            title.text = output_name.replace('_', ' ')
        for pubdate_fgdc in root.iter('pubdate'):
            pubdate_fgdc.text = last_update_date_str
        for descrip_fgdc in root.iter('abstract'):
            descrip_fgdc.text += ' Dataset last updated: {}. Dataset last downloaded: {}'.format(
                last_update_date_meta, today)

        print("Writing updated metadata to {}".format(input_path))
        tree.write('{}.xml'.format(input_path))
        print("Metadata update complete for {}".format(input_path))
        print("Upgrading metadata format for {}".format(input_path))
        arcpy.UpgradeMetadata_conversion(input_path, 'FGDC_TO_ARCGIS')
        print("Metadata format upgraded for {}".format(input_path))
        print("Exporting shapefile to SDE PROD as {}".format(output_name))
        arcpy.FeatureClassToFeatureClass_conversion(input_path, sde_path, output_name)
        print("Removing local storage info")
        arcpy.XSLTransform_conversion(os.path.join(sde_path, output_name),
                                      xslt_storage,
                                      os.path.join(zip_dir_path, '{}_storage.xml'.format(input_path)))
        arcpy.XSLTransform_conversion('{}_storage.xml'.format(input_path),
                                      xslt_geoprocess,
                                      '{}_geoprocess.xml'.format(input_path))
        print("Importing final metadata to {}".format(output_name))
        arcpy.MetadataImporter_conversion(os.path.join(zip_dir_path, "{}_geoprocess.xml".format(input_path)),
                                          os.path.join(sde_path, output_name))


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
            arcpy.MetadataImporter_conversion(os.path.join(sde_path, 'NYC_Building_Footprints_Poly'),
                                              os.path.join(sde_path, output_name))


    print("Exporting Building Footprints BIN Only to Production SDE")
    export_reduced_featureclass(bldg_footprint_poly_path, "NYC_Building_Footprints_Poly_BIN_Only")

    # Generate layers and xml stand-alone files for Buildings and Lots

    print("Generating stand-alone layer and xml files for M:\GIS\DATA directory")


    def distribute_layer_metadata(in_path, out_path):
        Arcdir = arcpy.GetInstallInfo("desktop")["InstallDir"]
        translator = Arcdir + "Metadata/Translator/ARCGIS2FGDC.xml"
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

    print(pymsg)
    print(msgs)

    log.write("" + pymsg + "\n")
    log.write("" + msgs + "")
    log.write("\n")
    log.close()
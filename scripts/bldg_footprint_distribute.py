# Utilizes Python 2 32-bit version in order to access metadata functionality not present on 64-bit version or Python 3
# version

import datetime
import os
import sys
import traceback
import xml.etree.ElementTree as ET

import arcpy
import ConfigParser
import requests
from bs4 import BeautifulSoup

try:

    DATA_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    CONFIG_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ini")
    LOG_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(__file__)), "log")
    
    # Set configuration file path
    config = ConfigParser.ConfigParser()
    config.read(os.path.join(CONFIG_DIRECTORY, "config.ini"))

    # Set log path
    log = open(os.path.join(LOG_DIRECTORY, "bldg_footprint.log"), "a")

    # Define zip, sde, metadata, and missing bbl txt file paths
    # zip_dir_path = config.get("PATHS", "zip_dir_path")
    # zip_path = os.path.join(zip_dir_path, "Building_Footprints.zip")
    sde_path = config.get("PATHS", "sde_path")
    lyr_dir_path = config.get("PATHS", 'lyr_dir_path')
    template_path = config.get("PATHS", 'template_path')
    
    # Set start time and write to log
    StartTime = datetime.datetime.now().replace(microsecond=0)
    log.write(str(StartTime) + "\t")
    
    # # Disconnect all users
    arcpy.AcceptConnections(sde_path, False)
    arcpy.DisconnectUser(sde_path, "ALL")

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

    error_list = set()

    # Export renamed shapefiles to Production SDE

    def export_featureclass(input_path, output_name, modified_path):
        '''
        Index BIN field, create new double field called PLUTO_BBL populate new field with BBL values with conditionals
        accounting for incorrect BBL values (either short or missing) and reorder output tables to include new field
        within the previous standard
        '''
        print("Creating PLUTO BBL field")
        arcpy.AddField_management(input_path, 'PLUTO_BBL', 'DOUBLE')
        print("PLUTO BBL field created")
        cursor = arcpy.da.UpdateCursor(input_path, ['BASE_BBL', 'MPLUTO_BBL', 'PLUTO_BBL', 'BIN'])
        for row in cursor:
            print("Parsing BASE_BBLS: {} and MPLUTO_BBLS: {}".format(row[0], row[1]))
            if len(row[0]) != 10:
                error_list.add("Short BBL. BASE_BBL = {} ; MPLUTO_BBL = {} ; BIN = {}".format(row[0], row[1], row[3]))
            if row[1].isspace() is True:
                if row[0].isspace() is True:
                    error_list.add("Missing BBL. BIN = {}".format(row[3]))
                    continue
                if row[0].isspace() is False and r"`" not in row[0]:
                    row[2] = float(row[0])
                    cursor.updateRow(row)
                    continue
                '''
                Case where ` character is included in BBL value. Interim value of 1 to replace this character until I can confirm with Matt.
                This would create the correct BBL based on DOB Property Profile Overview lookup information
                '''
                if r"`" in row[0]:
                    new_bbl = row[0].replace("`", "1")
                    row[2] = float(new_bbl)
                    cursor.updateRow(row)
                    continue
                else:
                    row[2] = float(row[0])
                    cursor.updateRow(row)
                    continue

            if row[1] == r'':
                if row[0] == r'':
                    error_list.add("Missing BBL. BIN = {}".format(row[3]))
                if r"`" in row[0]:
                    new_bbl = row[0].replace("`", "1")
                    row[2] = float(new_bbl)
                    cursor.updateRow(row)
                    continue
                else:
                    row[2] = float(row[0])
                    cursor.updateRow(row)
                    continue
            else:
                row[2] = float(row[1])
                cursor.updateRow(row)
                continue

        print("Creating field map in order to re-order the export tables")
        fieldMap = arcpy.FieldMappings()
        fieldMap.addTable(input_path)
        newFieldMap = arcpy.FieldMappings()
        print("Field mapping created")

        print("Adding fields to new field map")
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('NAME')))
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('BIN')))
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('CNSTRCT_YR')))
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('LSTMODDATE')))
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('LSTSTATYPE')))
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('DOITT_ID')))
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('HEIGHTROOF')))
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('FEAT_CODE')))
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('GROUNDELEV')))
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('BASE_BBL')))
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('MPLUTO_BBL')))
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('PLUTO_BBL')))
        newFieldMap.addFieldMap(fieldMap.getFieldMap(fieldMap.findFieldMapIndex('GEOMSOURCE')))
        print("All fields added to field map")

        print("Exporting as modified shapefile in temporary directory")
        arcpy.FeatureClassToFeatureClass_conversion(in_features=input_path,
                                                    out_path=DATA_DIRECTORY,
                                                    out_name=modified_path.split('.')[0],
                                                    field_mapping=newFieldMap)
        print("Modified shapefile exported")

        print("Upgrading downloaded metadata to ArcGIS standard")
        arcpy.env.workspace = DATA_DIRECTORY
        arcpy.env.overwriteOutput = True
        metadata_path = os.path.join(DATA_DIRECTORY, modified_path)
        arcpy.UpgradeMetadata_conversion(metadata_path, 'FGDC_TO_ARCGIS')
        print("Downloaded metadata upgraded to ArcGIS standard")
        print("Overwriting original metadata with DCP standard")
        arcpy.MetadataImporter_conversion(os.path.join(template_path, '{}.xml'.format(output_name)),
                                          metadata_path)
        print("Original metadata overwritten")
        tree = ET.parse('{}.xml'.format(metadata_path))
        root = tree.getroot()
        for title in root.iter('title'):
            title.text = output_name.replace('_', ' ')
        for pubdate_fgdc in root.iter('pubdate'):
            pubdate_fgdc.text = last_update_date_str
        for descrip_fgdc in root.iter('abstract'):
            descrip_fgdc.text += ' Dataset last updated: {}. Dataset last downloaded: {}'.format(
                last_update_date_meta, today)

        print("Writing updated metadata to {}".format(metadata_path))
        tree.write('{}.xml'.format(metadata_path))
        print("Metadata update complete for {}".format(metadata_path))
        print("Upgrading metadata format for {}".format(metadata_path))
        arcpy.UpgradeMetadata_conversion(metadata_path, 'FGDC_TO_ARCGIS')
        print("Metadata format upgraded for {}".format(metadata_path))

        arcpy.env.workspace = sde_path
        arcpy.env.overwriteOutput = True

        print("Exporting shapefile to SDE PROD as {}".format(output_name))
        arcpy.FeatureClassToFeatureClass_conversion(metadata_path, sde_path, output_name)
        print("Removing local storage info")
        print("Adding index to BIN field")
        arcpy.AddIndex_management(os.path.join(sde_path, output_name), ['BIN'], 'BIN_Index')
        print("Index added to BIN field")
        print("Adding index to PLUTO_BBL field")
        arcpy.AddIndex_management(os.path.join(sde_path, output_name), ['PLUTO_BBL'], 'PLUTO_BBL_Index')
        print("Index added to PLUTO_BBL field")
        arcpy.XSLTransform_conversion(os.path.join(sde_path, output_name),
                                      xslt_storage,
                                      os.path.join(DATA_DIRECTORY, '{}_storage.xml'.format(modified_path.split('.')[0])))
        arcpy.XSLTransform_conversion(os.path.join(DATA_DIRECTORY, '{}_storage.xml'.format(modified_path.split('.')[0])),
                                      xslt_geoprocess,
                                      os.path.join(DATA_DIRECTORY, '{}_geoprocess.xml'.format(modified_path.split('.')[0])))
        print("Importing final metadata to {}".format(output_name))
        arcpy.MetadataImporter_conversion(os.path.join(DATA_DIRECTORY, "{}_geoprocess.xml".format(modified_path.split('.')[0])),
                                          os.path.join(sde_path, output_name))

    bldg_footprint_poly_path = os.path.join(DATA_DIRECTORY, "BUILDING_FOOTPRINTS_PLY.shp")
    bldg_footprint_pt_path = os.path.join(DATA_DIRECTORY, "BUILDING_FOOTPRINTS_PT.shp")

    print("Exporting Building Footprints Polygon to Production SDE")
    export_featureclass(bldg_footprint_poly_path, "NYC_Building_Footprints_Poly", "BUILDING_FOOTPRINTS_PLY_Modified.shp")
    print("Exporting Building Footprints Points to Production SDE")
    export_featureclass(bldg_footprint_pt_path, "NYC_Building_Footprints_Points", "BUILDING_FOOTPRINTS_PT_Modified.shp")

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
            print("Adding Index to BIN field")
            arcpy.AddIndex_management(input_path, ['BIN'], 'BIN_Index')
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

    log.write(str(EndTime) + "\t" + str(EndTime - StartTime) + "\n")
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
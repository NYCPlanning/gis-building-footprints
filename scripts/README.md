# Building Footprints Web Scrape

*******************************

Building footprints represent the full perimeter outline of each building as viewed from directly above. This script is used to scrape the NYC Open Data platform for the most recent Building Footprints data set update and distribute accordingly across DCP's internal network file-systems.

### Prerequisites

An installation of Python 2 with the following packages is required. A version of Python with the default ArcPy installation that comes with ArcGIS Desktop is required in order to utilize Metadata functionality that is currently not available in the default ArcPy installation that comes with ArcGIS Pro (Python 3).

##### BuildingFootprints\_Scrape.py

```
requests, os, zipfile, arcpy, datetime, sys, traceback, ConfigParser, xml.etree.ElementTree as ET
```

### Instructions for running

##### BuildingFootprints\_Scrape.py

1. Open the script in any integrated development environment (PyCharm is suggested)

2. Ensure that your IDE is set to be utilizing a version of Python 2 with the requests library available and the default installation of ArcPy that comes with ArcGIS Desktop. Also ensure that the above mentioned python packages are available.

3. Ensure that the configuration ini file is up-to-date with path variables. If any paths have changed since the time of this writing, those changes must be reflected in the Config.ini file.

4. Run the script. It will create a new temporary directory called building_footprints. Building footprints point and polygon shapefiles will be exported to this temporary directory.

5. Building footprint point and polygon shapefiles are exported to Production SDE. In addition, a third, BIN-Only feature class is exported to Production SDE:
  + **NYC\_Building\_Footprints\_Points**
  + **NYC\_Building\_Footprints\_Poly**
  + **NYC\_Building\_Footprints\_Poly\_BIN\_Only**

6. M: Drive layer files and associated stand-alone metadata xml are also generated using the aforementioned SDE PROD Feature Classes as sources.

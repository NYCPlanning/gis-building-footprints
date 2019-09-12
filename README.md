# Building Footprints Web Scrape and Distribution

*******************************

Building footprints represent the full perimeter outline of each building as viewed from directly above. These scripts are used to scrape the NYC Open Data platform for the most recent Building Footprints data set and update DCP's internal network file-systems.

### Prerequisites

##### Scrape\_Bldg\_Footprints.py

A version of Python 2 64-bit or Python 3 with the following packages is required.

```
import requests, os, zipfile, arcpy, datetime, sys, traceback, ConfigParser, shutil, xml.etree.ElementTree as ET, time
from bs4 import BeautifulSoup
```

##### Distribute\_Bldg\_Footprints.py

A version of Python 2 with the default ArcPy installation that comes with ArcGIS Desktop is required in order to utilize Metadata functionality that is currently not available in the default ArcPy installation that comes with Python 2 64-bit or ArcGIS Pro (Python 3).

```
import requests, os, zipfile, arcpy, datetime, sys, traceback, ConfigParser, xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
```

### Instructions for running

##### Scrape\_Bldg\_Footprints.py

1. Open the script in any integrated development environment

2. Ensure that your IDE is set to be utilizing a version of Python 2 64-bit with the requests library available and the default installation of ArcPy that comes with ArcGIS Desktop. Also ensure that the above mentioned python packages are available.

3. Ensure that the configuration ini file is up-to-date with path variables. If any paths have changed since the time of this writing, those changes must be reflected in the Config.ini file.

4. Run the script. It will create a new temporary directory called building_footprints. Building footprints point and polygon shapefiles will be exported to this temporary directory.

#### Distribute\_Bldg\_Footprints.py

1. Open the script in any integrated development environment

2. Ensure that your IDE is set to be utilizing a version of Python 2 32-bit with the default ArcPy installation that comes with ArcGIS Desktop. Also ensure that the above mentioned python packages are available.

3. Ensure that the configuration ini file is up-to-date with path variables. If any paths have changed since the time of this writing, those changes must be reflected in the Config.ini file.

4. Run the script. It will pull from the previously created temporary directory. Building footprint point and polygon shapefiles are exported to Production SDE. In addition, a third, BIN-Only feature class is exported to Production SDE from an in-memory layer created in the script:
  + **NYC\_Building\_Footprints\_Points**
  + **NYC\_Building\_Footprints\_Poly**
  + **NYC\_Building\_Footprints\_Poly\_BIN\_Only**
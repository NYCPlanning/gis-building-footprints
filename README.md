# Building Footprints Web Scrape

Building footprints represent the full perimeter outline of each building as viewed from directly above. This script is used to scrape the NYC Open Data platform for the most recent Building Footprints data set update and distribute accordingly across DCP's internal network file-systems.

## [Pull Script](scripts/bldg_footprint_pull.py)

### Prerequisites

An installation of Python 3 is required, and the `geopandas` package ***must*** be installed.

### Instructions for running

1. Schedule via Task Scheduler. **Important: python interpreter pointed to by the scheduled task *must* have geopandas installed. The name and path of this interpreter may vary between GIS Team members** 

2. Review config file for any required updates.

### Summary

- This script will export building footprints point and polygon shapefiles to a `/data/raw` subdirectory within the script's directory structure.


## [Distribution Script](scripts/bldg_footprint_distribute.py) (to enterprise geodatabase)

### Prerequisites
This script requires the Python 2 installation that is included with ArcMap.

### Instructions for running

1. Schedule via Task Scheduler.

2. Review config file for any required updates.

### Summary

1. Building footprint point and polygon shapefiles are exported to Production SDE. In addition, a third, BIN-Only feature class is exported to Production SDE:

2. M: Drive layer files and associated stand-alone metadata xml are also generated using the aforementioned SDE PROD Feature Classes as sources.

3. Some additional data changes are made, particularly to the various BBL fields
# README

This script uses the Purple API to get PM2.5 AQI readings from their sensor
fleet. The API is documented but also rate-limited in an unspecified way, so
please take care when using this script.

## Finding nearby sensors

This step has to download a rather large JSON file which lists every sensor in
the world - over 13 MB when I last checked. Because of that, and because the
sensors nearby any given location don't change that often, you should only run
this step rarely.

    ./run.py find-nearest-sensors home.json -- 37.3788 -122.0314

By default, the script finds the 8 nearest sensors within 2 km of the given
location. The sensor IDs are written to the output file specified on the
command line.

## Getting a reading from nearby sensors

Using the set of sensors generated with the previous step, you can get a
current reading from those sensors:

    ./run.py get-readings home.json readings.json

The output file looks like this:

    {
        "now": 141,
        "10m": 153,
        "30m": 154,
        "1h": 152,
        "6h": 145,
        "24h": 151,
        "1w": 86
    }

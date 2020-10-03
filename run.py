#!/usr/bin/env python3
import json
from statistics import mean, median, stdev
import time
from typing import NamedTuple

import aqi
import click
from pygeodesy.ellipsoidalVincenty import LatLon
import requests


Sensor = NamedTuple('Sensor', [
    ('id', int),
    ('label', str),
    ('distance_m', float),
])


@click.group()
def main():
    pass


@main.command()
@click.option('--max-count', type=int, default=8)
@click.option('--max-distance-km', type=float, default=2)
@click.argument('output_file', type=click.File('w', encoding='utf-8'), required=True)
@click.argument('latitude', type=float, required=True)
@click.argument('longitude', type=float, required=True)
def find_nearest_sensors(max_count, max_distance_km, output_file, latitude, longitude):
    resp = requests.get('https://www.purpleair.com/json')
    resp.raise_for_status()
    sensors = resp.json()['results']
    here = LatLon(latitude, longitude)
    max_distance_m = max_distance_km * 1000
    timestamp = time.time()
    min_last_seen = timestamp - 3600
    n_candidates = 0
    near = []
    for sensor in sensors:
        if sensor.get('A_H'):
            # hardware fault detected
            continue
        if sensor.get('DEVICE_LOCATIONTYPE') != 'outside':
            continue
        if sensor['LastSeen'] < min_last_seen:
            continue
        if 'PM2_5Value' not in sensor:
            continue
        if 'Lat' not in sensor or 'Lon' not in sensor:
            continue
        n_candidates += 1
        distance_m = here.distanceTo(LatLon(sensor['Lat'], sensor['Lon']))
        if distance_m <= max_distance_m:
            near.append(Sensor(
                id=sensor['ID'],
                label=sensor['Label'],
                distance_m=distance_m,
            ))
    print('Found %d nearby outdoor sensors (out of %d candidates).' % (len(near), n_candidates))
    nearest = sorted(near, key=lambda x: x.distance_m)[:max_count]
    output = {
        'timestamp': timestamp,
        'latitude': latitude,
        'longitude': longitude,
        'sensors': [{
            'id': x.id,
            'label': x.label,
            'distance_m': x.distance_m,
        } for x in nearest],
    }
    output_file.write(json.dumps(output, indent=4))


def to_aqi(raw):
    return int(aqi.to_iaqi(aqi.POLLUTANT_PM25, raw, algo=aqi.ALGO_EPA).to_integral_value())


@main.command()
@click.argument('config_file', type=click.File('r', encoding='utf-8'), required=True)
@click.argument('output_file', type=click.File('w', encoding='utf-8'), required=True)
def get_readings(config_file, output_file):
    config = json.load(config_file)
    url = 'https://www.purpleair.com/json?show=' + '|'.join(map(lambda x: str(x['id']), config['sensors']))
    resp = requests.get(url)
    resp.raise_for_status()
    results = resp.json()['results']

    for result in results:
        result['Stats'] = json.loads(result['Stats'])

    def stat(name):
        return map(lambda x: x['Stats'][name], results)

    mean_realtime = mean(stat('v'))
    stdev_realtime = stdev(stat('v'))
    trusted_results = []
    for x in results:
        v = x['Stats']['v']
        if abs(v - mean_realtime) <= stdev_realtime * 2:
            trusted_results.append(x)
    results = trusted_results

    output = {
        'now': to_aqi(mean(stat('v'))),
        '10m': to_aqi(mean(stat('v1'))),
        '30m': to_aqi(mean(stat('v2'))),
        '1h': to_aqi(mean(stat('v3'))),
        '6h': to_aqi(mean(stat('v4'))),
        '24h': to_aqi(mean(stat('v5'))),
        '1w': to_aqi(mean(stat('v6'))),
    }
    output_file.write(json.dumps(output, indent=4))


if __name__ == '__main__':
    main()

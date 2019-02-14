#!/usr/bin/env python3

"""Unifi Exporter

Usage:
  main.py [options] -s <unifi_url> -u <username> -p <password>

Exposes Prometheus metrics from the Unifi Controller

Options:
  -h               Print this help doc
  -s <url>         URL of the Unifi server, without path  eg https://unifi.local:8443
  -u <username>    Name of Unifi admin user with read permissions
  -p <password>    Password of the above user
  -i               Run in insecure mode (no checking of server's certificate)
  -t               Run test mode (outputs a bunch of json data)
"""

from datetime import datetime
from docopt import docopt
from prometheus_client import REGISTRY, start_http_server
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
from requests import get, post
from time import sleep

def get_cookies():
    url = args['-s'] + '/api/login'
    payload = {
        'username': args['-u'],
        'password': args['-p'],
        'strict': True
    }
    resp = post(url, json=payload, verify=args['verify'])
    resp.raise_for_status()
    print('fetched new cookies')
    return resp.cookies

def get_data(cookies, url):
    resp = get(url, cookies=cookies, verify=args['verify'])
    if resp.status_code != 401:
        cookies = get_cookies()
        resp = get(url, cookies=cookies, verify=args['verify'])
    return resp.json()

def get_clients(cookies):
    api_paths = {
        'network_conf': '/api/s/default/rest/networkconf',
        'unifi_devices': '/api/s/default/stat/device',
        'clients': '/api/s/default/stat/sta'
    }
    url = args['-s'] + api_paths['clients']
    resp = get_data(cookies, url)
    return resp['data']

def get_client_labels(client):
    labels = [
        client.get('mac'),
        client.get('ip'),
        client.get('is_wired'),
        client.get('hostname'),
        client.get('network'),
    ]
    for idx, label in enumerate(labels):
        if label is None:
            labels[idx] = ''
        elif type(label) is bool:
            labels[idx] = str(label).lower()
        else:
            labels[idx] = label.lower()
    return labels


class Collector(object):
    def collect(self):
        start = datetime.now()
        metrics = {
            'tx_bytes': CounterMetricFamily(
                'unifi_client_tx_bytes',
                'Count of bytes the Unifi client has transmitted (upload)',
                labels=[
                    'client_mac',
                    'client_ip',
                    'is_wired',
                    'hostname',
                    'network',
                ]
            ),
            'rx_bytes': CounterMetricFamily(
                'unifi_client_rx_bytes',
                'Count of bytes the Unifi client has received (download)',
                labels=[
                    'client_mac',
                    'client_ip',
                    'is_wired',
                    'hostname',
                    'network',
                ]
            ),
            'first_seen': CounterMetricFamily(
                'unifi_client_first_seen',
                'Time the Unifi controller first noticed a client',
                labels=[
                    'client_mac',
                    'client_ip',
                    'is_wired',
                    'hostname',
                    'network',
                ]
            ),
            'last_seen': CounterMetricFamily(
                'unifi_client_last_seen',
                'Time the Unifi controller last noticed a client',
                labels=[
                    'client_mac',
                    'client_ip',
                    'is_wired',
                    'hostname',
                    'network',
                ]
            )
        }
        clients = get_clients(cookies)
        for client in clients:
            labels = get_client_labels(client)
            for name, metric in metrics.items():
                if name in client:
                    metrics[name].add_metric(labels, client[name])

        for name, metric in metrics.items():
            yield metrics[name]

        total_time = datetime.now() - start
        msg = 'collected metrics in {} seconds'
        print(msg.format(total_time.total_seconds()))


if __name__ == '__main__':
    args = docopt(__doc__)
    args['verify'] = True
    if args['-i']:
        args['verify'] = False

    try:
        cookies = get_cookies()
    except:
        print('failed to connect to unifi controller')
        exit(1)

    REGISTRY.register(Collector())
    http_port = 8080
    print('serving metrics on port {}'.format(http_port))
    start_http_server(http_port)

    while True:
        sleep(1)


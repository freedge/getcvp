from cloudvision.Connector.grpc_client.grpcClient import GRPCClient, create_query
from prometheus_client import start_http_server, Summary
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
from cloudvision.Connector.codec.custom_types import FrozenDict
from cloudvision.Connector.codec import Wildcard, Path
from utils import pretty_print
import time
import argparse
import logging

LOG=logging.getLogger("cvpexporter")

class CustomCollector(object):
    def __init__(self, client: GRPCClient):
        self.client = client
        # only computed at start for our poc:
        self.devices = getDevices(self.client)
    def collect(self):
        LOG.debug("collecting")
        # yield GaugeMetricFamily('my_gauge', 'Help text', value=7)
        # c = CounterMetricFamily('my_counter_total', 'Help text', labels=['foo'])
        g = GaugeMetricFamily('bgpStatus', 'BGP Status', labels=["state", "hostName", "serial"])
        for device, name in self.devices:
            metrics = getBgpMetrics(deviceRoutes(self.client, device))
            for state, count in metrics.items():
                g.add_metric([state, name, device], count)
        LOG.debug("all metrics added")
        yield g

def getDevices(client):
    pathElts = [
        "DatasetInfo",
        "Devices"
    ]
    query = [
        create_query([(pathElts, [])], "analytics")
    ]
    devices = []

    for batch in client.get(query):
        for notif in batch["notifications"]:
            for k,v in notif["updates"].items():
                devices.append((k, v['hostname']))
    return devices

def get(client, dataset, pathElts):
    ''' Returns a query on a path element'''
    result = {}
    query = [
        create_query([(pathElts, [])], dataset)
    ]

    for batch in client.get(query):
        for notif in batch["notifications"]:
            result.update(notif["updates"])
    return result


def unfreeze(o):
    ''' Used to unfreeze Frozen dictionaries'''
    if isinstance(o, (dict, FrozenDict)):
        return dict({k: unfreeze(v) for k, v in o.items()})

    if isinstance(o, (str)):
        return o

    try:
        return [unfreeze(i) for i in o]
    except TypeError:
        pass

    return o


def deviceRoutes(client, dId):
    
    pathElts = [
        "Smash",
        "routing",
        "bgp",
        "bgpPeerInfoStatus",
        "default",
        "bgpPeerStatusEntry"
    ]
    dataset = dId
    routeQuery = get(client, dataset, pathElts)
    return unfreeze(routeQuery)

def getBgpMetrics(routes):
    states = {}
    for k, i in routes.items():
        key = i['bgpState']['Name']
        if key in states.keys():
            states[key] += 1
        else:
            states[key] = 1
    return states

def collect(client):
    for device, name in getDevices(client):
        print(name, getBgpMetrics(deviceRoutes(client, device)))
        break

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="expose metrics from CVP through Prometheus. This is very experimental")
    parser.add_argument("-t", "--tokenFile", help="path to a file containing the token, previously acquired with get_token.py", required=True)  
    parser.add_argument("-c", "--caFile", help="server certificate if not trusted, previously acquired with get_token.py --ssl") 
    parser.add_argument("-v", "--cvp", help="cvp service to connect to (eg: privatecvp:8443)", default="www.arista.io:443") 
    parser.add_argument("-s", "--server", help="run in server mode, listen for traffic", action="store_true", default=False)
    parser.add_argument("-p", "--port", help="when running in server mode, listen on this port",  type=int, default=8000)
    parser.add_argument("-d", "--debug", help="activate debug logs", action="store_true", default=False)

    args = parser.parse_args()
        
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    LOG.debug("Connecting to {}".format(args.cvp))
    with GRPCClient(args.cvp, token=args.tokenFile, ca=args.caFile) as client:
        if args.server:
            LOG.debug("Registering collector")
            REGISTRY.register(CustomCollector(client))
            LOG.debug("Listening on port {}".format(args.port))
            # Start up the server to expose the metrics.
            start_http_server(args.port)
            while True:
                time.sleep(8)
        else:
            LOG.debug("Getting metrics once")
            collect(client)
    

from cloudvision.Connector.grpc_client import GRPCClient, create_query
from cloudvision.Connector.codec.custom_types import FrozenDict
from cloudvision.Connector.codec import Wildcard, Path
from utils import pretty_print
from parser import base
import json

debug = False


def get(client, dataset, pathElts):
    ''' Returns a query on a path element'''
    result = {}
    query = [
        create_query([(pathElts, [])], dataset)
    ]

    for batch in client.get(query):
        for notif in batch["notifications"]:
            if debug:
                pretty_print(notif["updates"])
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
                devices.append(k)
    return devices

def deviceRoutes(client, dId):
    if args.vrf:
        pathElts = [
            "Smash",
            "routing",
            "vrf",
            "status",
            args.vrf,
            "route"
        ]
    else:
        pathElts = [
            "Smash",
            "routing",
            "status",
            "route"
        ]
    dataset = dId
    routeQuery = get(client, dataset, pathElts)

    if args.vrf:
        pathElts = [
            "Smash",
            "forwarding",
            "vrf",
            "status", 
            args.vrf,
            "fec"
        ]
    else:
        pathElts = [
            "Smash",
            "forwarding",
            "status", 
            "fec"
        ]
    dataset = dId
    fecQuery = get(client, dataset, pathElts)
    
    routes = []
    fecs = {}
    
    for k, v in fecQuery.items():
        fecs[k["value"]] = v

    for k, v in routeQuery.items():
        fecId = v["fecId"]["value"]
        fec = fecs[fecId]
        routes.append(unfreeze(dict(route=v, fec=fec)))


    return routes

# only print a subset of routes we care about
def printRoute(deviceId, routes):
    for route in routes:
        if "/32" in route['route']['key']:
            if route['fec']['via'][0]["hop"] != "0.0.0.0" and "Vlan" in route['fec']['via'][0]["intfId"]:
                print("%s,%s,%s,%s" % (deviceId, route['route']['key'][:-3], route['fec']['via'][0]["hop"], route['fec']['via'][0]["intfId"]))

def main(apiserverAddr, token=None, certs=None, ca=None, key=None):
    with GRPCClient(apiserverAddr, token=token, key=key, ca=ca, certs=certs) as client:
        print("device,fip,hop,intf")
        if args.deviceId:
            devices = [args.deviceId]
        else:
            devices = getDevices(client)
        for deviceId in devices:
            routes = deviceRoutes(client, deviceId)
            printRoute(deviceId, routes)

    return 0


if __name__ == "__main__":
    base.add_argument("--deviceId",
                      help="device id to query")
    base.add_argument("--vrf",
                      help="vrf to target if not Default")
    args = base.parse_args()

    exit(main(args.apiserver, token=args.tokenFile,
              certs=args.certFile, ca=args.caFile))

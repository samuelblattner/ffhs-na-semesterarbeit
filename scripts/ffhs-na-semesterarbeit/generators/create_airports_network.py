import json
from typing import Dict, List, Tuple, Iterable
from datetime import datetime
from dateutil.tz import gettz
import networkx as nx

from utils.utils import EUROPEAN_COUNTRIES


CSV_AIRPORT_HEADERS = (
    'id', 'ident', 'type', 'name', 'latitude_deg', 'longitude_deg', 'elevation_ft', 'continent', 'iso_country', 'iso_region', 'municipality',
    'scheduled_service',
    'gps_code', 'iata_code', 'local_code', 'home_link')

SEC_TO_PRIM_AIRPORT_MAPPING = (
    ('elevation_ft', 'elevation_ft'),
    ('continent', 'continent'),
    ('elevation_ft', 'elevation_ft'),
    ('elevation_ft', 'elevation_ft'),
    ('elevation_ft', 'elevation_ft'),
)

REMOVE_NODE_NAME_PATTERNS = (
    'Railway',
    'Rail Station',
    'Railroad',
    'RailS',
    'Rail.'
)

airport_network = nx.MultiDiGraph()


def load_airports() -> Tuple[Iterable, Dict, Dict]:
    """
    Load airports from two different sources.
    :return:
    """
    airports_by_ICAO = {}
    airports_by_IATA = {}

    with open('../../data/airports.json', 'r', encoding='utf-8') as af:
        main_airports = json.loads(''.join(af.readlines()))

    for airport in main_airports:

        airport.setdefault('longitude', float(airport.get('longitudeAirport')))
        airport.setdefault('latitude', float(airport.get('latitudeAirport')))

        icao_code = airport.get('codeIcaoAirport', None)
        iata_code = airport.get('codeIataAirport', None)

        if iata_code:
            airports_by_IATA.setdefault(iata_code, airport)
        if icao_code:
            airports_by_ICAO.setdefault(icao_code, airport)

    return filter(
        lambda a: not any(
            [forbiddenName in a.get('nameAirport') for forbiddenName in REMOVE_NODE_NAME_PATTERNS]
        ),
        main_airports
    ), airports_by_IATA, airports_by_ICAO


def load_routes():
    """
    Load routes
    :return:
    """
    with open('../../data/Routes_20181109.json', 'r', encoding='utf-8') as af:
        routes = json.loads(''.join(af.readlines()))

    return routes


airports, IATA, ICAO = load_airports()
for airport_data in airports:
    for data_param, data in airport_data.items():
        if data is None:
            airport_data[data_param] = ''

    airport_network.add_node(airport_data.get('airportId'), **airport_data)

num_routes = 0
orphaned_routes = []
unisolated_airports = []

for route in load_routes():
    from_ap_icao = route.get('departureIcao', None)
    from_ap_iata = route.get('departureIata', None)
    from_ap_obj = None
    to_ap_icao = route.get('arrivalIcao', None)
    to_ap_iata = route.get('arrivalIata', None)
    to_ap_obj = None

    if from_ap_icao is None or from_ap_icao == '' or from_ap_icao not in ICAO:
        if from_ap_iata is None or from_ap_iata == '' or from_ap_iata not in IATA:
            from_ap_obj = None
        else:
            from_ap_obj = IATA.get(from_ap_iata)
    else:
        from_ap_obj = ICAO.get(from_ap_icao)

    if to_ap_icao is None or to_ap_icao == '' or to_ap_icao not in ICAO:
        if to_ap_iata is None or to_ap_iata == '' or to_ap_iata not in IATA:
            to_ap_obj = None
        else:
            to_ap_obj = IATA.get(to_ap_iata)
    else:
        to_ap_obj = ICAO.get(to_ap_icao)

    if from_ap_obj is None or to_ap_obj is None or route.get('departureTime') is None or route.get('arrivalTime') is None:
        orphaned_routes.append(route)
        continue

    if from_ap_obj not in unisolated_airports:
        unisolated_airports.append(from_ap_obj)
    if to_ap_obj not in unisolated_airports:
        unisolated_airports.append(to_ap_obj)

    local_dep_time_str = route.get('departureTime')
    local_arr_time_str = route.get('arrivalTime')

    utc_dep_time = datetime.strptime(local_dep_time_str, '%H:%M:%S').replace(
        tzinfo=gettz(from_ap_obj.get('timezone'))).astimezone() if local_dep_time_str else None

    utc_arr_time = datetime.strptime(local_arr_time_str, '%H:%M:%S').replace(
        tzinfo=gettz(to_ap_obj.get('timezone'))).astimezone() if local_arr_time_str else None

    # NOTE: If local departure time is close to midnight and if converting to UTC pushes
    # the time over midnight, the datetime will automatically increment the day from 1 to 2
    # which could put the departure time PAST the arrival time. To prevent this, we simply
    # replace the day argument with 1 to enforce the departure time to be on day 1.
    utc_dep_time = utc_dep_time.replace(day=1)

    route['duration'] = abs((utc_arr_time - utc_dep_time).total_seconds()) if local_dep_time_str is not None and local_arr_time_str is not None else 0

    route['departureTimeUTC'] = utc_dep_time.strftime('%H:%M:%S') if local_dep_time_str else None
    route['arrivalTimeUTC'] = utc_arr_time.strftime('%H:%M:%S') if local_arr_time_str else None

    for data_param, data in route.items():
        if data is None:
            route[data_param] = ''
        if isinstance(data, List):
            route[data_param] = ', '.join(data)
    airport_network.add_edge(from_ap_obj.get('airportId'), to_ap_obj.get('airportId'), weight=route['duration'] or 1, **route)

    num_routes += 1

# nodes = [n for n in airport_network.nodes()]
# for node in nodes:
#     if node not in unisolated_airports:
#         airport_network.remove_node(node)

# For European Airports Network:
# Remove all airports that:
# - are not located in a European country
# - are not adjacent by max. one link to an airport in a European country.

nodes_to_delete = []
for node in airport_network.nodes():
    if airport_network.node[node]['nameCountry'] not in EUROPEAN_COUNTRIES:
        # for neighbor in airport_network.neighbors(node):
        #     if airport_network.node[neighbor]['nameCountry'] in EUROPEAN_COUNTRIES:
        #         break
        # else:
        nodes_to_delete.append(node)

for node_to_delete in nodes_to_delete:
    airport_network.remove_node(node_to_delete)

print('Have {} orphaned routes'.format(len(orphaned_routes)))
print(num_routes)
nx.write_gexf(airport_network, 'network_europe_exlusive.gexf')

import csv
import json
from typing import Dict, List, Tuple, Iterable, Iterator
import networkx as nx

CSV_AIRPORT_HEADERS = (
'id', 'ident', 'type', 'name', 'latitude_deg', 'longitude_deg', 'elevation_ft', 'continent', 'iso_country', 'iso_region', 'municipality', 'scheduled_service',
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

airport_network = nx.DiGraph()


def load_airports() -> Tuple[Iterable, Dict, Dict]:
    """
    Load airports from two different sources.
    :return:
    """
    main_airports = {}
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

    secondary_airports = {}
    # with open('../../data/airports_20181008.csv', 'r', encoding='utf-8') as af:
    #     csv_reader = csv.DictReader(af, fieldnames=CSV_AIRPORT_HEADERS)
    #     for s, secondary_airport_data in enumerate(csv_reader):
    #
    #         if s == 0:
    #             continue
    #
    #         # Check if we have the airport already from the primary source
    #         airport = airport_by_ICAO.get(secondary_airport_data.get('ident'), None)
    #
    #         if airport:
    #             # 1a: If this is the case, add supplementary data to existing data
    #             airport.setdefault('elevation_ft', secondary_airport_data.get('elevation_ft', ''))
    #             airport.setdefault('continent', secondary_airport_data.get('elevation_ft', ''))
    #
    #         else:
    #             airport = {}
    #             # 1b: If airport is not yet in collection, add secondary data as primary data
    #             airport.setdefault('airportId', 's-{}'.format(s))
    #             airport.setdefault('nameAirport', secondary_airport_data.get('name', ''))
    #             airport.setdefault('codeIataAirport', secondary_airport_data.get('iata_code', ''))
    #             airport.setdefault('codeIcaoAirport', secondary_airport_data.get('ident', ''))
    #             airport.setdefault('nameTranslations', '')
    #             airport.setdefault('latitudeAirport', secondary_airport_data.get('latitude_deg', ''))
    #             airport.setdefault('longitudeAirport', secondary_airport_data.get('longitude_deg', ''))
    #             airport.setdefault('elevation_ft', secondary_airport_data.get('elevation_ft', ''))
    #             airport.setdefault('continent', secondary_airport_data.get('continent', ''))
    #             airport.setdefault('geonameId', '')
    #             airport.setdefault('timezone', secondary_airport_data.get('continent', ''))
    #             airport.setdefault('GMT', secondary_airport_data.get('continent', ''))
    #             airport.setdefault('phone', secondary_airport_data.get('continent', ''))
    #             airport.setdefault('nameCountry', secondary_airport_data.get('iso_country', ''))
    #             airport.setdefault('codeIso2Country', secondary_airport_data.get('iso_country', ''))
    #             airport.setdefault('codeIataCity', secondary_airport_data.get('iso_region', ''))
    #             airport.setdefault('latitude', float(secondary_airport_data.get('latitude_deg', 0)))
    #             airport.setdefault('longitude', float(secondary_airport_data.get('longitude_deg', 0)))
    #
    #             airport_by_ICAO.setdefault(secondary_airport_data.get('ident'), airport)

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
    with open('../../data/Routes_20181009.json', 'r', encoding='utf-8') as af:
        routes = json.loads(''.join(af.readlines()))

    return routes

# print(len(load_airports().keys()))


airports, IATA, ICAO = load_airports()
for airport_data in airports:
    for data_param, data in airport_data.items():
        if data is None:
            airport_data[data_param] = ''
    airport_network.add_node(airport_data.get('airportId'), **airport_data)

num_routes = 0
orphaned_routes = []
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

    if from_ap_obj is None or to_ap_obj is None:
        orphaned_routes.append(route)
        continue

    for data_param, data in route.items():
        if data is None:
            route[data_param] = ''
        if isinstance(data, List):
            route[data_param] = ', '.join(data)
    airport_network.add_edge(from_ap_obj.get('airportId'), to_ap_obj.get('airportId'), **route)

    num_routes+=1

print(orphaned_routes[0])

print('Have {} orphaned routes'.format(len(orphaned_routes)))
print(num_routes)
nx.write_gexf(airport_network, 'network.gexf')


from random import random
from typing import Tuple, List, Dict

from dateutil import parser

EUROPEAN_COUNTRIES = (
    'Albania',
    'Andorra',
    'Austria',
    'Belarus',
    'Belgium',
    'Bosnia and Herzegovina',
    'Bulgaria',
    'Croatia',
    'Czech Republic',
    'Denmark',
    'Estonia',
    'Finland',
    'France',
    'Germany',
    'Greece',
    'Hungary',
    'Iceland',
    'Ireland',
    'Italy',
    'Latvia',
    'Liechtenstein',
    'Lithuania',
    'Luxembourg',
    'Malta',
    'Moldova',
    'Monaco',
    'Netherlands',
    'Norway',
    'Poland',
    'Portugal',
    'Romania',
    'Russia',
    'San Marino',
    'Serbia',
    'Slovakia',
    'Slovenia',
    'Spain',
    'Sweden',
    'Switzerland',
    'Ukraine',
    'United Kingdom',
)

import sys
from datetime import datetime, timedelta
from math import radians, atan2, sqrt, cos, sin

import networkx as nx
from dateutil.tz import gettz


def calculate_distance_from_coordinates(lat1, lng1, lat2, lng2):
    r = 6371.0
    rad_lat1 = radians(lat1)
    rad_lng1 = radians(lng1)
    rad_lat2 = radians(lat2)
    rad_lng2 = radians(lng2)

    dlat = rad_lat2 - rad_lat1
    dlng = rad_lng2 - rad_lng1

    a = (sin(dlat / 2) ** 2) + (cos(rad_lat1) * cos(rad_lat2)) * (sin(dlng / 2) ** 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return r * c


def calculate_flight_duration_per_distance(network: nx.MultiDiGraph):

    durations_per_km = []

    for from_airport in network.nodes():
        for f, t, k in network.out_edges(from_airport, keys=True):
            if f == t:
                continue

            from_data = network.nodes[f]
            to_data = network.nodes[t]

            try:
                dist = calculate_distance_from_coordinates(
                    from_data.get('latitude'),
                    from_data.get('longitude'),
                    to_data.get('latitude'),
                    to_data.get('longitude'),
                )
            except:
                continue

            flight_time = network.edges[f, t, k].get('duration')
            durations_per_km.append(flight_time / dist)

    return sum(durations_per_km) / len(durations_per_km)


def calculate_hub_attachment_likelihood(network: nx.MultiDiGraph, from_airport, to_airport):

    p = 0.5
    num_out_edges = len(network.out_edges(from_airport))

    num_links1 = network.get_edge_data(from_airport, to_airport)
    num_links1 = len(num_links1) if num_links1 else 0
    num_links2 = network.get_edge_data(to_airport, from_airport)
    num_links2 = len(num_links2) if num_links2 else 0
    num_shared_edges = num_links1 + num_links2
    return p * 1/network.number_of_nodes() + (1-p) * num_shared_edges / (1+num_out_edges)


def calculate_hub_neighbor_attachment_likelihood(network, from_airport, to_airport):

    p = 0.2

    # Find hubs that connect from and to airports
    from_neighbors = set([t for f, t, k in network.out_edges(from_airport, keys=True)])
    to_neighbors = set([t for f, t, k in network.out_edges(to_airport, keys=True)])
    common_hubs = from_neighbors.intersection(to_neighbors)

    random_connectivity = p * 1/network.number_of_nodes()

    if len(common_hubs) == 0:
        return random_connectivity

    all_to_hub_strengths = []
    for common_hub in common_hubs:
        num_links1 = network.get_edge_data(from_airport, common_hub)
        num_links1 = len(num_links1) if num_links1 else 0

        num_links2 = network.get_edge_data(common_hub, from_airport)
        num_links2 = len(num_links2) if num_links2 else 0

        all_to_hub_strengths.append((
            num_links1 + num_links2,
            common_hub
        ))

    strength, strongest_hub = sorted(all_to_hub_strengths, key=lambda hn: hn[0], reverse=True)[0]

    existing_direct_routes1 = network.get_edge_data(from_airport, to_airport)
    existing_direct_routes1 = len(existing_direct_routes1) if existing_direct_routes1 else 0

    existing_direct_routes2 = network.get_edge_data(to_airport, from_airport)
    existing_direct_routes2 = len(existing_direct_routes2) if existing_direct_routes2 else 0

    existing_direct_routes = existing_direct_routes1 + existing_direct_routes2

    neighbor_connectivity = (1-p) * (1 / ((1 + existing_direct_routes)**5)) * (strength / sum([s[0] for s in all_to_hub_strengths]))

    return random_connectivity + neighbor_connectivity


def calculate_non_hub_connectivity(network: nx.MultiDiGraph, from_airport, to_airport):

    p = 0.2

    return p * 1/network.number_of_nodes() + (1-p) * 1/((network.degree(to_airport) + 1)**2)


def grow_traffic_by_x_years(network: nx.MultiDiGraph, years, growth_rate, duration_per_km, preferential_attachment=None):

    num_of_edges = len(network.edges)
    prospect_num_of_edges = num_of_edges * (growth_rate**years)

    num_additional_edges = int(prospect_num_of_edges) - num_of_edges

    DIST_CACHE = {}

    num_distributed_new_edges = 0
    while num_distributed_new_edges < num_additional_edges:

        for fn, from_airport in enumerate(network.nodes()):

            if num_distributed_new_edges >= num_additional_edges:
                return

            sys.stdout.write('\rDistributed: {} of {} new links'.format(num_distributed_new_edges, num_additional_edges))

            for to_airport in network.nodes():

                if num_distributed_new_edges >= num_additional_edges:
                    return

                # Avoid connections to self
                if from_airport == to_airport:
                    continue

                if preferential_attachment == 'HUB':
                    p = calculate_hub_attachment_likelihood(network, from_airport, to_airport)
                    if random() > p:
                        continue

                elif preferential_attachment == 'NEIGHBOR':
                    p = calculate_hub_neighbor_attachment_likelihood(network, from_airport, to_airport)
                    # sys.stdout.write('\rP: {} '.format(p))
                    if random() > p:
                        continue

                elif preferential_attachment == 'NONHUB':
                    p = calculate_non_hub_connectivity(network, from_airport, to_airport)
                    # sys.stdout.write('\rP: {} '.format(p))
                    if random() > p:
                        continue

                from_airport_obj = network.nodes[from_airport]
                to_airport_obj = network.nodes[to_airport]

                # Check existing connections between the airports.
                # If there are any, we can just use their flight duration
                for ef, et, ek in network.out_edges([from_airport, to_airport], keys=True):
                    if ef == from_airport and et == to_airport or ef == to_airport and et == to_airport:
                        flight_duration_in_min = network.edges[ef, et, ek].get('duration')
                        break

                # If no connections exist yet
                else:
                    distance = DIST_CACHE.get(from_airport, {}).get(to_airport, None)
                    if distance is None:
                        distance = calculate_distance_from_coordinates(
                            lat1=from_airport_obj.get('latitude'),
                            lng1=from_airport_obj.get('longitude'),
                            lat2=to_airport_obj.get('latitude'),
                            lng2=to_airport_obj.get('longitude')
                        )

                        DIST_CACHE.setdefault(from_airport, {to_airport: distance})
                        DIST_CACHE.setdefault(to_airport, {from_airport: distance})

                    flight_duration_in_min = int(distance * duration_per_km / 60)

                utc_dep_time = datetime.strptime('{}:{}:00'.format(5 + int(15 * random()), int(12*random()) * 5), '%H:%M:%S').replace(
                    tzinfo=gettz(network.nodes[from_airport].get('timezone'))).astimezone()

                utc_arr_time = utc_dep_time + timedelta(minutes=flight_duration_in_min)

                network.add_edge(from_airport, to_airport, **{
                    'departureTimeUTC': utc_dep_time.strftime('%H:%M:%S'),
                    'arrivalTimeUTC': utc_arr_time.strftime('%H:%M:%S'),
                    'duration': flight_duration_in_min * 60
                })

                num_distributed_new_edges += 1


def create_flight_departures_arrivals_index(network) -> Tuple[Dict, Dict]:
    """
    Creates two indices where arrivals and departures are collected by minute.
    This helps to prevent the simulation from analyzing all flights for every
    simulation step (minute) and thus reduces total simulation time greatly.
    :param network:
    :return:
    """

    dep_index = {}
    arr_index = {}

    ins = 0

    for node in network.nodes():
        for f, t, k in network.out_edges(node, keys=True):
            outbound_flight_data = network.edges[f, t, k]
            scheduled_departure_utc = parser.parse(outbound_flight_data['departureTimeUTC']).time()
            scheduled_departure_utc = scheduled_departure_utc.hour * 60 + scheduled_departure_utc.minute
            dep_index.setdefault(scheduled_departure_utc, {}).setdefault(
                '{}{}{}'.format(f, t, k),
                (outbound_flight_data, f, t)
            )

        for f, t, k in network.in_edges(node, keys=True):
            ins += 1
            inbound_flight_data = network.edges[f, t, k]
            scheduled_arrival_utc = parser.parse(inbound_flight_data['arrivalTimeUTC']).time()
            scheduled_arrival_utc = scheduled_arrival_utc.hour * 60 + scheduled_arrival_utc.minute
            arr_index.setdefault(scheduled_arrival_utc, {}).setdefault(
                '{}{}{}'.format(f, t, k),
                (inbound_flight_data, f, t)
            )

    return dep_index, arr_index


def create_airport_capacity_load_index(network, capacity_factor=1.2):

    cap_index = {}
    load_index = {}

    for airport in network.nodes():
        cap_index.setdefault(airport, {})

        for f, t, k in network.out_edges(airport, keys=True):
            outbound_flight_data = network.edges[f, t, k]
            scheduled_departure_utc = parser.parse(outbound_flight_data['departureTimeUTC']).time()
            cap_index[airport].setdefault(scheduled_departure_utc.hour, 0)
            cap_index[airport][scheduled_departure_utc.hour] += 1

        for f, t, k in network.in_edges(airport, keys=True):
            inbound_flight_data = network.edges[f, t, k]
            scheduled_arrival_utc = parser.parse(inbound_flight_data['arrivalTimeUTC']).time()
            cap_index[airport].setdefault(scheduled_arrival_utc.hour, 0)
            cap_index[airport][scheduled_arrival_utc.hour] += 1

        max_cap = max(cap_index[airport].values()) if cap_index[airport].values() else 0
        if airport == '9908':
            print(network.nodes[airport]['codeIcaoAirport'])
            print(max_cap)
            print(max_cap/60)
        cap_index[airport] = capacity_factor * max_cap
        load_index[airport] = 0

    return cap_index, load_index


def transform_to_random(network, duration_per_km=4.5):
    transformed = nx.MultiDiGraph()
    all_nodes_keys = list(network.nodes().keys())
    num_edges = len(network.edges)
    num_edges_added = 0
    DIST_CACHE = {}

    for node in network.nodes():
        transformed.add_node(node, **network.nodes[node])

    for f, t, k in network.edges:

        # Select from and to airport randomly
        from_airport = to_airport = -1
        while from_airport == to_airport:
            from_airport = all_nodes_keys[int(random() * len(all_nodes_keys))]
            to_airport = all_nodes_keys[int(random() * len(all_nodes_keys))]

        from_airport_obj = network.nodes[from_airport]
        to_airport_obj = network.nodes[to_airport]

        # Calculate distance and flight duration between them
        distance = DIST_CACHE.get(from_airport, {}).get(to_airport, None)
        if distance is None:
            distance = calculate_distance_from_coordinates(
                lat1=from_airport_obj.get('latitude'),
                lng1=from_airport_obj.get('longitude'),
                lat2=to_airport_obj.get('latitude'),
                lng2=to_airport_obj.get('longitude')
            )

            DIST_CACHE.setdefault(from_airport, {to_airport: distance})
            DIST_CACHE.setdefault(to_airport, {from_airport: distance})

        flight_duration_in_min = int(distance * duration_per_km / 60)

        # Choose a random departure time during the day
        utc_dep_time = parser.parse(network.edges[f, t, k]['departureTimeUTC'])

        # Calculate arrival time
        utc_arr_time = utc_dep_time + timedelta(minutes=flight_duration_in_min)

        # Add flight to new network
        transformed.add_edge(
            from_airport,
            to_airport,
            **{
                'departureTimeUTC': utc_dep_time.strftime('%H:%M:%S'),
                'arrivalTimeUTC': utc_arr_time.strftime('%H:%M:%S'),
                'duration': flight_duration_in_min * 60
            }
        )

        num_edges_added += 1

    return transformed

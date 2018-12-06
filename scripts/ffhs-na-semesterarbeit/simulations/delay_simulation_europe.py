import sys
from random import random

import networkx as nx
from dateutil import parser
from matplotlib.backends.backend_pdf import PdfPages

from utils.utils import create_flight_departures_arrivals_index, create_airport_capacity_load_index, transform_to_random, grow_traffic_by_x_years
from utils.utils import EUROPEAN_COUNTRIES
from matplotlib import pyplot as plt

europe_aviation_network: nx.MultiDiGraph = nx.read_gexf('network_europe.gexf')
random_european_network = transform_to_random(europe_aviation_network)

DEPARTURE_MINUTE_INDEX = {}
ARRIVAL_MINUTE_INDEX = {}

# Initial values
current_time = 0  # Midnight UTC
max_time = 60 * 24  # 60 Minutes times 24 hours = Total minutes per day
delay_decay_min = 1/4
connectivity = 0.4  # Percentage of passengers transferred to a connecting flight upon arrival
connection_growth_per_year = 1.04
flight_duration_per_km = 4.50
turn_around_duration = 45


networks = (
    (europe_aviation_network, 'Natürliches Netzwerk'),
    # (random_european_network, 'Zufallsnetzwerk')
)


def initialize_simulation(network):

    global DEPARTURE_MINUTE_INDEX, ARRIVAL_MINUTE_INDEX, AIRPORT_CAPACITY_INDEX, AIRPORT_LOAD_INDEX, current_time
    current_time = 0
    DEPARTURE_MINUTE_INDEX = {}
    ARRIVAL_MINUTE_INDEX = {}
    AIRPORT_CAPACITY_INDEX = {}
    AIRPORT_LOAD_INDEX = {}

    for node in network.nodes():
        network.nodes[node]['delays'] = []


def calculate_airport_loads_for_time(time):

    global AIRPORT_LOAD_INDEX

    if time % 60 == 0 or time == 0:
        AIRPORT_LOAD_INDEX = {}

    for key, value in DEPARTURE_MINUTE_INDEX.get(time, {}).items():
        outbound_flight_data, from_airport, to_airport = value
        AIRPORT_LOAD_INDEX.setdefault(from_airport, 0)
        AIRPORT_LOAD_INDEX[from_airport] += 1

    for key, value in ARRIVAL_MINUTE_INDEX.get(time, {}).items():
        inbound_flight_data, from_airport, to_airport = value
        AIRPORT_LOAD_INDEX.setdefault(to_airport, 0)
        AIRPORT_LOAD_INDEX[to_airport] += 1


def do_outbound_flights_step_for_time(network: nx.MultiDiGraph, time):

    calculate_airport_loads_for_time(time)

    for key, value in DEPARTURE_MINUTE_INDEX.get(time, {}).items():
        outbound_flight_data, from_airport, to_airport = value

        from_airport_data = network.nodes[from_airport]

        scheduled_departure_utc = parser.parse(outbound_flight_data['departureTimeUTC']).time()
        scheduled_departure_utc = scheduled_departure_utc.hour * 60 + scheduled_departure_utc.minute
        scheduled_arrival_utc = parser.parse(outbound_flight_data['arrivalTimeUTC']).time()
        scheduled_arrival_utc = scheduled_arrival_utc.hour * 60 + scheduled_arrival_utc.minute

        outbound_flight_data['initial_delay'] = 0
        outbound_flight_data['en_route_delay'] = 0

        capacity_delay = 30 ** max(0, AIRPORT_LOAD_INDEX[from_airport] / AIRPORT_CAPACITY_INDEX[from_airport] - 1) - 1

        affective_delays = [d for d in from_airport_data['delays'] if d.get('introduction_time') < scheduled_departure_utc < d.get('introduction_time') + d.get('amount') + turn_around_duration + capacity_delay]
        largest_affective_delay = None
        for affective_delay in affective_delays:
            overlap = affective_delay.get('introduction_time') + affective_delay.get('amount') + turn_around_duration + capacity_delay - scheduled_departure_utc
            largest_overlap = 0 if largest_affective_delay is None else largest_affective_delay.get('introduction_time') + largest_affective_delay.get('amount') + turn_around_duration + capacity_delay - scheduled_departure_utc
            if largest_affective_delay is None or overlap > largest_overlap:
                largest_affective_delay = affective_delay

        if largest_affective_delay is not None:
            delay_amount = largest_affective_delay.get('amount')
            delay_introduction_time = largest_affective_delay.get('introduction_time')
            outbound_flight_data['initial_delay'] += connectivity * (delay_introduction_time + delay_amount + turn_around_duration + capacity_delay - scheduled_departure_utc)

        outbound_flight_data['en_route_delay'] = -15 + int(random() * 30)

        # Reschedule for inbound
        total_outbound_delay = outbound_flight_data['initial_delay'] + outbound_flight_data['en_route_delay']
        old_arrival_time_slot = ARRIVAL_MINUTE_INDEX.get(scheduled_arrival_utc, {})
        new_arrival_time_slot = ARRIVAL_MINUTE_INDEX.get(scheduled_arrival_utc + total_outbound_delay, {})
        del old_arrival_time_slot[key]
        new_arrival_time_slot.setdefault(key, (outbound_flight_data, from_airport, to_airport))

        # Cause delay
        network.nodes[to_airport].setdefault('delays', []).append({'introduction_time': scheduled_arrival_utc, 'amount': total_outbound_delay})


def do_inbound_flights_step_for_time(network: nx.MultiDiGraph, time):

    calculate_airport_loads_for_time(time)

    for key, value in ARRIVAL_MINUTE_INDEX.get(time, {}).items():

        inbound_flight_data, from_airport, to_airport = value
        to_airport_data = network.nodes[to_airport]
        inbound_delay = inbound_flight_data.get('initial_delay', 0) + inbound_flight_data.get('en_route_delay', 0)
        capacity_delay = max(0, AIRPORT_LOAD_INDEX[to_airport] / AIRPORT_CAPACITY_INDEX[to_airport] - 1) * 15

        delays = to_airport_data.get('delays', [])
        delays.append({
            'amount': inbound_delay + capacity_delay,
            'introduction_time': time
        })
        to_airport_data['delays'] = delays


def do_degrade_airport_delays(airports: nx.MultiDiGraph):

    for airport in airports.nodes():

        airport_data = airports.nodes[airport]
        remove_delays = []
        active_delays = airport_data.get('delays', [])

        for delay in active_delays:
            delay['amount'] -= delay_decay_min
            if delay['amount'] <= 0:
                remove_delays.append(delay)

        for remove_delay in remove_delays:
            active_delays.remove(remove_delay)

        airports.nodes[airport]['delays'] = active_delays


def do_simulation_step(airports, step_size=1):

    global current_time

    do_outbound_flights_step_for_time(airports, current_time)
    do_degrade_airport_delays(airports)
    # do_inbound_flights_step_for_time(airports, current_time)

    current_time += step_size

    if current_time > max_time:
        raise StopIteration()


def calculate_european_delay(network):
    total_delay = 0
    for airport in network.nodes():
        if network.nodes[airport]['nameCountry'] not in EUROPEAN_COUNTRIES:
            continue
        total_delay += sum([d['amount'] for d in network.nodes[airport]['delays']])

    return total_delay


delay_tables = [None] * len(networks)
for n, network_tuple in enumerate(networks):

    network, network_name = network_tuple
    initialize_simulation(network)

    print('numer before: ', len(network.edges))

    grow_traffic_by_x_years(network, 10, connection_growth_per_year, flight_duration_per_km, 'NEIGHBOR')

    print('numer after: ', len(network.edges))

    sys.stdout.write('\rCreating departures/arrivals index...')
    DEPARTURE_MINUTE_INDEX, ARRIVAL_MINUTE_INDEX = create_flight_departures_arrivals_index(network)

    sys.stdout.write('\rCreating airport capacity/load index...')
    AIRPORT_CAPACITY_INDEX, AIRPORT_LOAD_INDEX = create_airport_capacity_load_index(network, capacity_factor=1.2)

    delay_tables[n] = []
    cap_table = []
    load_table = []
    max_delay = 0

    load_zh = AIRPORT_LOAD_INDEX['9908']
    cap_zh = AIRPORT_CAPACITY_INDEX['9908']

    while True:
        try:
            do_simulation_step(network)
            sys.stdout.write('\rSimulation step {} of {}'.format(current_time, max_time))
            sys.stdout.flush()
            total_delay = calculate_european_delay(network)
            max_delay = max(max_delay, total_delay)
            delay_tables[n].append(total_delay)

            cap_table.append(cap_zh)
            calculate_airport_loads_for_time(current_time)
            load_table.append(AIRPORT_LOAD_INDEX.get('9908', 0))

        except StopIteration:
            print('Simulation complete.')
            break

    print('max')
    print(max_delay)

fig = plt.figure()
plt.clf()

for delay_table, network in zip(delay_tables, networks):
    plt.plot(range(24 * 60), delay_table, label='Verspätung Europa total, {}'.format(network[1]))
    plt.legend()
    plt.xlabel('Minute UTC')
    plt.ylabel('Verspätung [min]')

    pp = PdfPages('total_delay.pdf')
    fig.savefig(pp, format='pdf')
    pp.close()

fig = plt.figure()
plt.clf()
#
# plt.plot(range(24 * 60), cap_table, label='Kapazität LSZH')
# plt.plot(range(24 * 60), load_table, label='Last LSZH')
#
# plt.xlabel('Minute UTC')
# plt.ylabel('Anzahl Flugbewegungen')
#
# pp = PdfPages('cap_load_lszh.pdf')
# fig.savefig(pp, format='pdf')
# pp.close()
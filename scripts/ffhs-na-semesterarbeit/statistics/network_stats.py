import networkx as nx
from matplotlib.backends.backend_pdf import PdfPages
from networkx import Graph
import matplotlib.pyplot as plt

from utils.utils import create_flight_departures_arrivals_index, EUROPEAN_COUNTRIES

graph: nx.MultiDiGraph = nx.read_gexf('network.gexf')

def print_simple_stats():
    degrees = list(dict(graph.degree).values())
    in_degrees = list(dict(graph.in_degree).values())
    out_degrees = list(dict(graph.out_degree).values())

    print('<k>: {}'.format(sum(degrees) / graph.number_of_nodes()))
    print('<k_in>: {}'.format(sum(in_degrees) / graph.number_of_nodes()))
    print('<k_out>: {}'.format(sum(out_degrees) / graph.number_of_nodes()))

    print()
    print('<k^2>: {}'.format(sum([deg ** 2 for deg in degrees]) / graph.number_of_nodes()))


def plot_degree_hist(output=None):
    if output:
        degrees = list(dict(graph.degree).values())
        fig = plt.figure()
        plt.hist(degrees, bins=max(degrees) - min(degrees))
        plt.xlabel('Grad')
        plt.ylabel('Anzahl')
        pp = PdfPages(output)
        fig.savefig(pp, format='pdf')
        pp.close()


def plot_dep_arr_hist(countries_only=None, output=None):
    dep_index, arr_index = create_flight_departures_arrivals_index(graph)
    departures_hist = []
    arrivals_hist = []
    for minute in range(60 * 24):
        departures_hist.append(len([dep for dep, airport_data in dep_index.get(minute, []) if countries_only is None or airport_data['nameCountry'] in countries_only]))
        arrivals_hist.append(len([arr for arr, airport_data in arr_index.get(minute, []) if countries_only is None or airport_data['nameCountry'] in countries_only]))

    if output:
        fig = plt.figure()
        plt.clf()
        plt.plot(range(24 * 60), departures_hist, label='Abflüge')
        plt.plot(range(24 * 60), arrivals_hist, label='Ankünfte')
        plt.legend()
        plt.xlabel('Minute UTC')
        plt.ylabel('Anzahl Flüge')

        pp = PdfPages(output)
        fig.savefig(pp, format='pdf')
        pp.close()


plot_dep_arr_hist('arr_dep_world.pdf')
plot_dep_arr_hist(EUROPEAN_COUNTRIES, 'arr_dep_europe.pdf')

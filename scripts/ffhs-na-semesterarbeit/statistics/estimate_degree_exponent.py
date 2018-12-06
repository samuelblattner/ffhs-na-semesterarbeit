import networkx as nx
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.markers import MarkerStyle
from networkx import Graph

from scipy.special import zeta
from scipy.stats import kstest
from matplotlib import pyplot as plt


graph: Graph = nx.read_gexf('network.gexf')

degree_data = sorted(dict(graph.degree).values())
degree_classes = sorted(set(degree_data))

N = graph.number_of_nodes()

kmin_class = max(min(degree_classes), 1)
kmax_class = max(degree_classes)

kmin_count = degree_data.count(kmin_class)
kmax_count = degree_data.count(kmax_class)

Kmin_class = kmin_class
Kmin_count = kmin_count

D = {}

print(len(degree_classes))
print(degree_classes)


def estimate_gamma(Kmin_class, degree_data_subset):
    return 1 + len(degree_data_subset) / (np.sum([np.log(max(degree, 1) / (Kmin_class - 0.5)) for degree in degree_data_subset]))


for idx, Kmin_class in enumerate(degree_classes):
    if Kmin_class == 0:
        continue

    Kmin_count = degree_data.count(Kmin_class)

    degree_data_subset = degree_data[degree_data.index(Kmin_class):]

    gamma = estimate_gamma(Kmin_class, degree_data_subset)

    # print(Kmin_class)
    # print(gamma)
    print(Kmin_class)
    print(degree_data.count(Kmin_class))
    D.setdefault(Kmin_class, kstest(degree_data_subset, lambda k: 1 - (zeta(gamma, k) / zeta(gamma, Kmin_class))))


table_l = sorted(filter(lambda test_tuple: test_tuple[1].pvalue > 0.01, D.items()), key=lambda test_tuple: test_tuple[1].statistic)
table = sorted(D.items(), key=lambda test_tuple: test_tuple[1].statistic)

best_gamma = estimate_gamma(table_l[0][0], degree_data[degree_data.index(table_l[0][0]):])
print(table_l[0])
print(best_gamma)


# plt.scatter([t[0] for t in table], [t[1].statistic for t in table], c=['cyan' if t[1].pvalue > 0.01 else 'grey' for t in table], marker=MarkerStyle(marker='x', ))
# plt.loglog([t[0] for t in table], [t[1].statistic for t in table])

# plt.scatter(degree_classes[1:], [degree_data.count(k) for k in degree_classes[1:]])
plt.figure()
ax = plt.gca()
ax.set_yscale('log')
ax.set_xlabel('k')
ax.set_xscale('log')
ax.set_ylabel('p')

ax.scatter(degree_classes[1:], [degree_data.count(k) / float(len(degree_data)) for k in degree_classes[1:]], marker=MarkerStyle(marker='.',))

ax.plot(degree_classes[degree_classes.index(table_l[0][0]):], [(k**-best_gamma)/(zeta(best_gamma, table_l[0][0])) for k in degree_classes[degree_classes.index(table_l[0][0]):]])

plt.savefig('degree-distribution.pdf', format='pdf')
plt.show()


print([degree_data.count(k) / len(degree_data) for k in degree_classes[1:]])
# print([1/(zeta(best_gamma, table_l[0][0])) * k**-best_gamma for k in degree_classes[degree_classes.index(table_l[0][0]):]])

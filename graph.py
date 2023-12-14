import ipywidgets as widgets
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import geopandas as gpd
from IPython.display import HTML
from IPython.display import display
from PIL import Image
from matplotlib import lines
import heapq

class Graph:
    """A graph connects nodes (vertices) by edges (links). Each edge can also
    have a length associated with it. The constructor call is something like:
        g = Graph({'A': {'B': 1, 'C': 2})
    this makes a graph with 3 nodes, A, B, and C, with an edge of length 1 from
    A to B,  and an edge of length 2 from A to C. You can also do:
        g = Graph({'A': {'B': 1, 'C': 2}, directed=False)
    This makes an undirected graph, so inverse links are also added. The graph
    stays undirected; if you add more links with g.connect('B', 'C', 3), then
    inverse link is also added. You can use g.nodes() to get a list of nodes,
    g.get('A') to get a dict of links out of A, and g.get('A', 'B') to get the
    length of the link from A to B. 'Lengths' can actually be any object at
    all, and nodes can be any hashable object."""

    def __init__(self, graph_dict=None, directed=True):
        self.graph_dict = graph_dict or {}
        self.directed = directed
        if not directed:
            self.make_undirected()

    def make_undirected(self):
        """Make a digraph into an undirected graph by adding symmetric edges."""
        for a in list(self.graph_dict.keys()):
            for (b, dist) in self.graph_dict[a].items():
                self.connect1(b, a, dist)

    def connect(self, A, B, distance=1):
        """Add a link from A and B of given distance, and also add the inverse
        link if the graph is undirected."""
        self.connect1(A, B, distance)
        if not self.directed:
            self.connect1(B, A, distance)

    def connect1(self, A, B, distance):
        """Add a link from A to B of given distance, in one direction only."""
        self.graph_dict.setdefault(A, {})[B] = distance

    def get(self, a, b=None):
        """Return a link distance or a dict of {node: distance} entries.
        .get(a,b) returns the distance or None;
        .get(a) returns a dict of {node: distance} entries, possibly {}."""
        links = self.graph_dict.setdefault(a, {})
        if b is None:
            return links
        else:
            return links.get(b)

    def nodes(self):
        """Return a list of nodes in the graph."""
        s1 = set([k for k in self.graph_dict.keys()])
        s2 = set([k2 for v in self.graph_dict.values() for k2, v2 in v.items()])
        nodes = s1.union(s2)
        return list(nodes)


def UndirectedGraph(graph_dict=None):
    """Build a Graph where every edge (including future ones) goes both ways."""
    return Graph(graph_dict=graph_dict, directed=False)


def dijkstra_shortest_path(graph, start, end, weight='weight'):
    """
    Dijkstra's algorithm to find the shortest path in a weighted graph.
    """
    queue = [(0, start, [])]
    visited = set()
    
    while queue:
        (cost, node, path) = heapq.heappop(queue)
        if node not in visited:
            visited.add(node)
            path = path + [node]
            
            if node == end:
                return path
            
            for neighbor, edge_data in graph[node].items():
                if neighbor not in visited:
                    heapq.heappush(queue, (cost + edge_data.get(weight, 1), neighbor, path))
    
    return []

def show_map(graph_data, step=0, node_colors=None, redistribute=False):
    G = nx.Graph(graph_data['graph_dict'])
    # node color is green if production > consumption, red if consumption > production, white if consumption = production, grey if no data
    node_colors = {k: 'green' if v['production'][step] > v['consumption'][step] else 'red' if v['production'][step] < v['consumption'][step] else 'white' if v['production'][step] == v['consumption'][step] else 'grey' for k, v in graph_data['node_data'].items()}

    node_positions = graph_data['node_positions']
    node_label_pos = graph_data['node_label_positions']
    node_data_pos = graph_data['node_data_positions']
    edge_weights = graph_data['edge_weights']
    data = graph_data['node_data']

    # set the size of the plot
    plt.figure(figsize=(18, 13))
    # draw the graph (both nodes and edges) with locations from france_locations
    nx.draw(G, pos={k: node_positions[k] for k in G.nodes()},
            node_color=[node_colors[node] for node in G.nodes()], linewidths=0.3, edgecolors='k')

    # draw french contours
    try:
        france_shapefile = gpd.read_file('data/metropole.geojson')
        print('Drawing french contours')
        france_shapefile.boundary.plot(ax=plt.gca(), edgecolor='black')
    except:
        print('Shapefile not found. No french contours drawn.')

    # draw labels for nodes
    node_label_handles = nx.draw_networkx_labels(G, pos=node_label_pos, font_size=14)

    # add a white bounding box behind the node labels
    [label.set_bbox(dict(facecolor='white', edgecolor='none')) for label in node_label_handles.values()]

    # draw data for nodes (dictionary with 2 keys: 'production' and 'consumption' displayed on 2 lines)
    # use step parameter to display production and consumption for a given step in prediction
    formatted_labels = {key: f"production : {value['production'][step]}\n consumption : {round(value['consumption'][step])}" for key, value in data.items()}
    node_data_handles = nx.draw_networkx_labels(G, pos=node_data_pos, labels=formatted_labels, font_size=7)

    # add a white bounding box behind the node data labels
    [label.set_bbox(dict(facecolor='white', edgecolor='none')) for label in node_data_handles.values()]

    # add edge labels to the graph
    nx.draw_networkx_edge_labels(G, pos=node_positions, edge_labels=edge_weights, font_size=14)

    # visualize redistribution of surplus electricity with arrows
    if redistribute:
        surplus_cities = [city for city in G.nodes() if data[city]['production'][step] > data[city]['consumption'][step]]
        deficit_cities = [city for city in G.nodes() if data[city]['production'][step] < data[city]['consumption'][step]]

        for surplus_city in surplus_cities:
            surplus = max(0, data[surplus_city]['production'][step] - data[surplus_city]['consumption'][step])

            for deficit_city in deficit_cities:
                path = dijkstra_shortest_path(G, surplus_city, deficit_city, weight='weight')
                
                if path:
                    arrow_start = node_positions[surplus_city]
                    arrow_end = node_positions[path[1]]  # Next city in the shortest path
                    arrow_length = min(0.5, surplus / 500)  # Adjust arrow length based on surplus (scaled for visualization)
                    arrow_props = dict(facecolor='yellow', edgecolor='yellow', arrowstyle='->', shrinkA=0, shrinkB=0, lw=2)
                    plt.annotate("", xytext=arrow_start, xy=arrow_end, arrowprops=arrow_props, size=20)

    # add a legend
    white_circle = lines.Line2D([], [], color="white", marker='o', markersize=15, markerfacecolor="white")
    red_circle = lines.Line2D([], [], color="red", marker='o', markersize=15, markerfacecolor="red")
    gray_circle = lines.Line2D([], [], color="gray", marker='o', markersize=15, markerfacecolor="gray")
    green_circle = lines.Line2D([], [], color="green", marker='o', markersize=15, markerfacecolor="green")
    plt.legend((white_circle, red_circle, gray_circle, green_circle),
               ('No data', 'electricity production deficit', 'Unknown', 'power generation surplus'),
               numpoints=1, prop={'size': 16}, loc=(.8, .75))

    # show the plot. No need to use in notebooks. nx.draw will show the graph itself.
    plt.show()


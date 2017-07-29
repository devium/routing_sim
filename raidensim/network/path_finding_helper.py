import networkx as nx

from raidensim.dijkstra_weighted import dijkstra_path
from raidensim.network.node import Node


class PathFindingHelper(object):
    def __init__(self, cn, range_, center):
        self.cn = cn
        self.range = range_
        self.center = center

    def is_in_range(self, target):
        assert isinstance(target, Node)

        return abs(target.uid - self.center) <= self.range / 2

    def _get_path_cost_function(self, value, hop_cost=1):
        """
        Same as the global :func:`~ChannelNetwork._get_path_cost_function` except it considers
        nodes outside the helper's range unavailable.
        """

        def cost_func_fast(a, b, _account):
            if not self.is_in_range(a) and not self.is_in_range(b):
                return None

            if a.uid < b.uid:
                capacity = _account['balance'] + _account[a.uid]
            else:
                capacity = - _account['balance'] + _account[a.uid]

            assert capacity >= 0
            if capacity < value:
                return None
            return hop_cost

        return cost_func_fast

    def find_path(self, source, target, value):
        assert isinstance(source, Node)
        assert isinstance(target, Node)
        try:
            path = dijkstra_path(self.cn.G, source, target, self._get_path_cost_function(value))
            return path
        except nx.NetworkXNoPath:
            return None
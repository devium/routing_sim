from typing import List, Callable

import networkx as nx

from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.fee_strategy import FeeStrategy
from raidensim.strategy.routing.routing_strategy import RoutingStrategy
from raidensim.types import Path


class GlobalRoutingStrategy(RoutingStrategy):
    def __init__(self, fee_strategy: FeeStrategy):
        self.fee_strategy = fee_strategy

    def route(self, raw: RawNetwork, source: Node, target: Node, value: int) -> (Path, List[Path]):
        def edge_cost(u: Node, v: Node, e: dict):
            if e['capacity'] > value:
                return self.fee_strategy.get_fee(u, v, e, value)
            return None

        try:
            return nx.dijkstra_path(raw, source, target, weight=edge_cost), []
        except nx.NetworkXNoPath:
            return [], []

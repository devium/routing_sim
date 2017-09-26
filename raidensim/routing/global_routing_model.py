from typing import List, Callable

import math
import networkx as nx

from raidensim.network.node import Node
from raidensim.routing.routing_model import RoutingModel
from raidensim.types import Path


class GlobalRoutingModel(RoutingModel):
    def __init__(self, fee_model: Callable[[Node, Node, dict, int], float]):
        self.fee_model = fee_model

    def route(self, source: Node, target: Node, value: int) -> (Path, List[Path]):
        def edge_cost(a: Node, b: Node, attrs: dict):
            if attrs['capacity'] > value:
                return self.fee_model(a, b, attrs, value)
            return None

        try:
            return nx.dijkstra_path(source.cn, source, target, weight=edge_cost), []
        except nx.NetworkXNoPath:
            return [], []


def constant_fee_model(a: Node, b: Node, attrs: dict, value: int) -> float:
    return 1


def net_balance_fee_model(a: Node, b: Node, attrs: dict, value: int) -> float:
    # Sigmoid function.
    return 1 / (1 + math.exp(-(attrs['net_balance'] + value)))


def imbalance_fee_model(a: Node, b: Node, attrs: dict, value: int) -> float:
    # Sigmoid function.
    return 1 / (1 + math.exp(-(attrs['imbalance'] + 2 * value)))

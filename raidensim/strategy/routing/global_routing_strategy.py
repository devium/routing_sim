from typing import List, Callable

import networkx as nx

from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.strategy.routing.routing_strategy import RoutingStrategy
from raidensim.types import Path
from raidensim.util import sigmoid


class GlobalRoutingStrategy(RoutingStrategy):
    def __init__(self, fee_model: Callable[[Node, Node, dict, int], float]):
        self.fee_model = fee_model

    def route(self, raw: RawNetwork, source: Node, target: Node, value: int) -> (Path, List[Path]):
        def edge_cost(u: Node, v: Node, e: dict):
            if e['capacity'] > value:
                return self.fee_model(u, v, e, value)
            return None

        try:
            return nx.dijkstra_path(raw, source, target, weight=edge_cost), []
        except nx.NetworkXNoPath:
            return [], []


def constant_fee_model(u: Node, v: Node, e: dict, value: int) -> float:
    return 1


def net_balance_fee_model(u: Node, v: Node, e: dict, value: int) -> float:
    # Include balance caused by the transfer.
    return sigmoid(e['net_balance'] + value)


def imbalance_fee_model(u: Node, v: Node, e: dict, value: int) -> float:
    # Include imbalance caused by the transfer.
    return sigmoid(e['imbalance'] + 2 * value)

from typing import Callable, Iterable, Union

from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.types import Fullness


class FilterStrategy(object):
    def filter(self, raw: RawNetwork, a: Node, b: Node) -> bool:
        raise NotImplementedError


class PositionStrategy(object):
    def _map_node(self, node: Node):
        raise NotImplementedError

    def map(self, nodes: Union[Node, Iterable[Node]]):
        if isinstance(nodes, Node):
            return self._map_node(nodes)
        elif isinstance(nodes, Iterable[Node]):
            return {node: self._map_node(node) for node in nodes}
        else:
            raise ValueError

    def distance(self, a: Node, b: Node):
        raise NotImplementedError


class SelectionStrategy(object):
    def __init__(self, filter_strategies: Iterable[FilterStrategy]):
        self.filter_strategies = filter_strategies

    def match(self, raw: RawNetwork, a: Node, b: Node):
        return all(filter_strategy.filter(raw, a, b) for filter_strategy in self.filter_strategies)

    def targets(self, raw: RawNetwork, node: Node) -> Iterable[Node]:
        raise NotImplementedError


class ConnectionStrategy(object):
    def connect(self, raw: RawNetwork, a: Node, b: Node):
        raise NotImplementedError


class NetworkStrategy(object):
    def __init__(
            self,
            initiated_channels_mapping: Callable[[Fullness], int],
            selection_strategy: SelectionStrategy,
            connection_strategy: ConnectionStrategy,
            position_strategy: PositionStrategy
    ):
        self.initiated_channels_mapping = initiated_channels_mapping
        self.selection_strategy = selection_strategy
        self.connection_strategy = connection_strategy
        self.position_strategy = position_strategy

    def connect(self, raw: RawNetwork, node: Node):
        max_initiated_channels = self.initiated_channels_mapping(node.fullness)
        targets = None
        if node['num_initiated_channels'] < max_initiated_channels:
            targets = self.selection_strategy.targets(raw, node)

        try:
            while node['num_initiated_channels'] < max_initiated_channels:
                target = next(targets)
                self.connection_strategy.connect(raw, node, target)
        except StopIteration:
            print('Out of suitable nodes for {}. {}/{} connections unfulfilled'.format(
                node,
                max_initiated_channels - node['num_initiated_channels'],
                max_initiated_channels
            ))

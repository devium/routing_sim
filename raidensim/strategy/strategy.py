from collections import defaultdict
from typing import Callable, Generator, Tuple, Iterable, Any, Dict

from raidensim.network.node import Node
from raidensim.types import Fullness

NodeConnectionData = Tuple[Node, Dict[str, Any]]


class FilterStrategy(object):
    def filter(self, a: NodeConnectionData, b: NodeConnectionData) -> bool:
        raise NotImplementedError


class SelectionStrategy(object):
    def __init__(self, filter_strategies: Iterable[FilterStrategy]):
        self.filter_strategies = filter_strategies

    def match(self, a: NodeConnectionData, b: NodeConnectionData):
        return all(filter_strategy.filter(a, b) for filter_strategy in self.filter_strategies)

    def targets(
            self, node: NodeConnectionData, node_to_connection_data: Dict[Node, Dict[str, Any]]
    ) -> Iterable[NodeConnectionData]:
        raise NotImplementedError


class ConnectionStrategy(object):
    def connect(self, a: NodeConnectionData, b: NodeConnectionData):
        raise NotImplementedError


class NetworkStrategy(object):
    def __init__(
            self,
            initiated_channels_mapping: Callable[[Fullness], int],
            selection_strategy: SelectionStrategy,
            connection_strategy: ConnectionStrategy,
    ):
        self.initiated_channels_mapping = initiated_channels_mapping
        self.selection_strategy = selection_strategy
        self.connection_strategy = connection_strategy
        self.node_to_connection_data = defaultdict(lambda: defaultdict(int))

    def connect(self, node: Node):
        node_data = self.node_to_connection_data[node]
        max_initiated_channels = self.initiated_channels_mapping(node.fullness)
        targets = None
        if node_data['num_initiated_channels'] < max_initiated_channels:
            targets = self.selection_strategy.targets(
                (node, node_data), self.node_to_connection_data
            )

        try:
            while node_data['num_initiated_channels'] < max_initiated_channels:
                target = next(targets)
                self.connection_strategy.connect((node, node_data), target)
        except StopIteration:
            print('Out of suitable nodes for {}.'.format(node))

import random
from typing import Iterator

from raidensim.network.lattice import WovenLattice
from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from .filter_strategy import FilterStrategy


class SelectionStrategy(object):
    def __init__(self, filter_strategies: Iterator[FilterStrategy]):
        self.filter_strategies = filter_strategies

    def match(self, raw: RawNetwork, a: Node, b: Node):
        return all(filter_strategy.filter(raw, a, b) for filter_strategy in self.filter_strategies)

    def targets(self, raw: RawNetwork, node: Node) -> Iterator[Node]:
        raise NotImplementedError


class FirstMatchSelectionStrategy(SelectionStrategy):
    def targets(self, raw: RawNetwork, node: Node) -> Iterator[Node]:
        return (target for target in raw.nodes if self.match(raw, node, target))


class RandomSelectionStrategy(SelectionStrategy):
    """
    Warning: inefficient. Filters and shuffles all nodes on each call.
    """
    def targets(self, raw: RawNetwork, node: Node) -> Iterator[Node]:
        nodes = [target for target in raw.nodes if self.match(raw, node, target)]
        random.shuffle(nodes)
        while nodes:
            yield nodes.pop(0)


class RandomAuxLatticeSelectionStrategy(SelectionStrategy):
    def __init__(self, lattice: WovenLattice, filter_strategies: Iterator[FilterStrategy]):
        SelectionStrategy.__init__(self, filter_strategies)
        self.lattice = lattice

    def targets(self, raw: RawNetwork, node: Node) -> Iterator[Node]:
        aux_neighbors = list(self.lattice.aux_node_neighbors(node))
        random.shuffle(aux_neighbors)
        return (target for target in aux_neighbors if self.match(raw, node, target))

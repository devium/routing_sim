from typing import List

from raidensim.network.node import Node
from raidensim.network.raw_network import RawNetwork
from raidensim.types import Path


class RoutingModel(object):
    def route(self, raw: RawNetwork, source: Node, target: Node, value: int) -> (Path, List[Path]):
        raise NotImplementedError

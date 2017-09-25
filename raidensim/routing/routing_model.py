from typing import List

from raidensim.network.node import Node
from raidensim.types import Path


class RoutingModel(object):
    def route(self, source: Node, target: Node, value: int) -> (Path, List[Path]):
        raise NotImplementedError

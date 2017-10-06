from collections import defaultdict


class Node(defaultdict):
    """
    Each node holds a dict of additional data used for routing, connecting, etc.
    """
    def __init__(self, uid: int, fullness: float):
        super().__init__(int)
        self.uid = uid
        self.fullness = fullness

    def __repr__(self):
        return '<{}({}, fullness: {})>'.format(self.__class__.__name__, self.uid, self.fullness)

    def __hash__(self):
        return self.uid

    def __ne__(self, o: object) -> bool:
        return not self == o

    def __eq__(self, o: object) -> bool:
        return isinstance(o, Node) and self.uid == o.uid

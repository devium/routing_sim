from collections import defaultdict
from typing import List


def get_channel_distribution(cn) -> List[int]:
    return [len(node.channels) for node in cn.nodes]


def get_channel_capacities(cn) -> List[float]:
    return [cv.capacity for node in cn.nodes for cv in node.channels.values()]


def get_channel_net_balances(cn) -> List[float]:
    balances = defaultdict(int)
    for node in cn.nodes:
        for cv in node.channels.values():
            balances[frozenset([node.uid, cv.partner])] = abs(cv.balance)

    return list(balances.values())


def get_channel_imbalances(cn) -> List[float]:
    imbalances = defaultdict(int)
    for node in cn.nodes:
        for cv in node.channels.values():
            imbalances[frozenset([node.uid, cv.partner])] = \
                abs(cv.deposit - cv.partner_deposit + 2 * cv.balance)

    return list(imbalances.values())
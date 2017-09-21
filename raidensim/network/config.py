import random

from .dist import Distribution


class NetworkConfiguration(object):
    def __init__(
            self,
            num_nodes: int,
            fullness_dist: Distribution,
            min_max_initiated_channels=2,
            max_max_initiated_channels=10,
            min_max_accepted_channels=100,
            max_max_accepted_channels=100,
            min_max_channels=110,
            max_max_channels=110,
            min_deposit=10,
            max_deposit=100,
            min_partner_deposit=0.5,
            open_strategy='bi_closest_fuller'
    ):
        self.num_nodes = num_nodes
        self.fullness_dist = fullness_dist
        self.min_max_initiated_channels = min_max_initiated_channels
        self.max_max_initiated_channels = max_max_initiated_channels
        self.min_max_accepted_channels = min_max_accepted_channels
        self.max_max_accepted_channels = max_max_accepted_channels
        self.min_max_channels = min_max_channels
        self.max_max_channels = max_max_channels
        self.min_deposit = min_deposit
        self.max_deposit = max_deposit
        self.min_partner_deposit = min_partner_deposit
        self.open_strategy = open_strategy

    @staticmethod
    def _linear(min_, max_, fullness):
        return int((max_ - min_) * fullness + min_)

    def get_max_initiated_channels(self, fullness):
        return NetworkConfiguration._linear(
            self.min_max_initiated_channels, self.max_max_initiated_channels, fullness
        )

    def get_max_accepted_channels(self, fullness):
        return NetworkConfiguration._linear(
            self.min_max_accepted_channels, self.max_max_accepted_channels, fullness
        )

    def get_max_channels(self, fullness):
        return NetworkConfiguration._linear(
            self.min_max_channels, self.max_max_channels, fullness
        )

    def get_channel_deposit(self, fullness):
        return NetworkConfiguration._linear(
            self.min_deposit, self.max_deposit, fullness
        )

    # Pathfinding helpers
    ph_num_helpers = 20
    ph_max_range_fr = 1 / 8.
    ph_min_range_fr = 1 / 16.


class MicroRaidenNetworkConfiguration(NetworkConfiguration):
    """
    A network configuration that makes a distinction between clients and servers.
    Clients are minimal-fullness nodes with few outgoing channels to server nodes only.
    Clients do not accept channels.
    Server nodes only accept channels but do not initiate any.
    The resulting topology are multiple many-to-one star-like networks.
    """
    def __init__(
            self,
            num_nodes: int,
            server_fullness_dist,
            client_fraction=0.95,
            min_max_initiated_channels=2,
            max_max_initiated_channels=10,
            min_max_accepted_channels=100,
            max_max_accepted_channels=100,
            min_deposit=10,
            max_deposit=100
    ):
        # Client fullnesses == 0
        NetworkConfiguration.__init__(
            self,
            fullness_dist=self.Distribution(client_fraction, server_fullness_dist),
            num_nodes=num_nodes,
            min_max_initiated_channels=min_max_initiated_channels,
            max_max_initiated_channels=max_max_initiated_channels,
            min_max_accepted_channels=min_max_accepted_channels,
            max_max_accepted_channels=max_max_accepted_channels,
            min_max_channels=min_max_initiated_channels + min_max_accepted_channels,
            max_max_channels=max_max_initiated_channels + max_max_accepted_channels,
            min_deposit=min_deposit,
            max_deposit=max_deposit,
            open_strategy='microraiden'
        )

    def get_max_initiated_channels(self, fullness):
        # Only clients initiate channels.
        if fullness == 0:
            return NetworkConfiguration._linear(
                self.min_max_initiated_channels,
                self.max_max_initiated_channels,
                random.uniform(0, 1)
            )
        else:
            return 0

    def get_max_accepted_channels(self, fullness):
        # Only servers accept channels.
        if fullness == 0:
            return 0
        else:
            return NetworkConfiguration._linear(
                self.min_max_accepted_channels, self.max_max_accepted_channels, fullness
            )

    def get_max_channels(self, fullness):
        return NetworkConfiguration._linear(
            self.min_max_channels, self.max_max_channels, fullness
        )

    def get_channel_deposit(self, fullness):
        return NetworkConfiguration._linear(
            self.min_deposit, self.max_deposit, fullness
        )

    class Distribution(object):
        def __init__(self, client_fraction, server_fullness_dist):
            self.client_fraction = client_fraction
            self.server_fullness_dist = server_fullness_dist

        def reset(self):
            random.seed(0)
            self.server_fullness_dist.reset()

        def random(self):
            if random.uniform(0, 1) < self.client_fraction:
                return 0
            else:
                return self.server_fullness_dist.random() / 2 + 0.5

        def get_pdf(self):
            return self.server_fullness_dist.get_pdf()

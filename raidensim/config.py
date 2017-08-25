class NetworkConfiguration(object):
    def __init__(
            self,
            num_nodes,
            fullness_dist,
            min_channels=2,
            max_channels=10,
            min_deposit=10,
            max_deposit=100
    ):
        self.num_nodes = num_nodes
        self.fullness_dist = fullness_dist
        self.min_channels = min_channels
        self.max_channels = max_channels
        self.min_deposit = min_deposit
        self.max_deposit = max_deposit

    def get_num_channels(self, fullness):
        """
        Linear min/max mapping of fullness to channel count.
        """
        return int((self.max_channels - self.min_channels) * fullness + self.min_channels)

    def get_channel_deposit(self, fullness):
        """
        Linear min/max mapping of fullness to deposit per channel.
        """
        return int((self.max_deposit - self.min_deposit) * fullness + self.min_deposit)

    # pathfinding helpers
    ph_num_helpers = 20
    ph_max_range_fr = 1 / 8.
    ph_min_range_fr = 1 / 16.

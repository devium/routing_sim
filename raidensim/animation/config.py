from raidensim.network import NetworkConfiguration
from raidensim.network.dist import Distribution


class AnimationConfiguration:
    def __init__(
            self,
            out_dir: str,
            network: NetworkConfiguration,
            popup_channels: bool,
            animation_length: float,
            transfer_hop_delay: float,
            transfer_freq_max: float,
            top_hole_radius: float,
            popup_freq_max: float = 200,
            simulation_step_size: float = 0.01,
            transfer_attempts_max: int = 10,
            transfer_value: int = 1

    ):
        self.out_dir = out_dir
        self.network = network
        self.popup_channels = popup_channels
        self.animation_length = animation_length
        self.transfer_hop_delay = transfer_hop_delay
        self.transfer_freq_max = transfer_freq_max
        self.top_hole_radius = top_hole_radius
        self.popup_freq_max = popup_freq_max
        self.simulation_step_size = simulation_step_size
        self.transfer_attempts_max = transfer_attempts_max
        self.transfer_value = transfer_value

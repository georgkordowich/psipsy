from power_sim_lib.models.backend import *
from power_sim_lib.models.blocks import LeadLag, PT1Limited
from power_sim_lib.models.generic_dynamic_model import GenericModel


class SEXS(GenericModel):
    """
    Represents the SEXS (Simplified Excitation System) model in power system simulations.

    This class models a simplified excitation system for synchronous generators, combining lead-lag and
    first-order transfer function with limited output. It's used to simulate the dynamic behavior of the
    generator's voltage control system.

    Attributes:
        lead_lag (LeadLag): The lead-lag control block.
        pt1_lim (PT1Limited): The PT1 transfer function block with output limiting.
        v_setpoint (float or torch.Tensor): The setpoint for the system voltage.
        bias (float or torch.Tensor): A bias value for voltage control.
    """
    def __init__(self, param_dict=None, parallel_sims=None, v_setpoint=1.0):
        """
        Initializes the SEXS model with specified parameters.

        Parameters:
            param_dict (dict, optional): A dictionary of parameters for the model.
            parallel_sims (int, optional): Number of parallel simulations to enable.
            v_setpoint (float, optional): The setpoint for the system voltage. Default is 1.0.
        """
        if param_dict is not None:
            # simply take all values from the dictionary and assign them to the object
            self.__dict__.update(param_dict)
        else:
            self.name = 'SEXS1'
            self.k = 0.0
            self.t_a = 0.0
            self.t_b = 0.0
            self.t_e = 0.0
            self.e_min = 0.0
            self.e_max = 0.0

        self.lead_lag = LeadLag(t_1=self.t_a, t_2=self.t_b, parallel_sims=parallel_sims)
        self.pt1_lim = PT1Limited(t_pt1=self.t_e, gain_pt1=self.k, lim_min=self.e_min, lim_max=self.e_max,
                                  parallel_sims=parallel_sims)

        self.v_setpoint = v_setpoint
        self.bias = 0.0

    def differential(self):
        """
        Computes the differential equations for the SEXS model.

        Returns:
            torch.Tensor: A tensor containing the derivatives of the state variables.
        """
        return torch.concatenate([self.lead_lag.differential(), self.pt1_lim.differential()], axis=1)

    def get_state_vector(self):
        """
        Retrieves the current state vector of the SEXS model.

        Returns:
            torch.Tensor: The current state vector of the model.
        """
        return torch.concatenate([self.lead_lag.get_state_vector(), self.pt1_lim.get_state_vector()], axis=1)

    def set_state_vector(self, x):
        """
        Sets the state vector of the SEXS model.

        Parameters:
            x (torch.Tensor): A tensor representing the new state vector.
        """
        self.lead_lag.set_state_vector(x[:, 0:1])
        self.pt1_lim.set_state_vector(x[:, 1:2])

    def get_output(self, input_value):
        """
        Computes the output of the SEXS model given an input value.

        Parameters:
            input_value (float or torch.Tensor): The input value to the model.

        Returns:
            torch.Tensor: The output of the model.
        """
        in1 = self.v_setpoint - input_value + self.bias
        in2 = self.lead_lag.get_output(in1)
        output = self.pt1_lim.get_output(in2)
        return output

    def enable_parallel_simulation(self, parallel_sims):
        """
        Enables parallel simulations by transforming the model's parameters into tensors.

        Parameters:
            parallel_sims (int): Number of parallel simulations.
        """
        self.v_setpoint = torch.ones((parallel_sims, 1), dtype=torch.float64) * self.v_setpoint
        self.bias = torch.ones((parallel_sims, 1), dtype=torch.float64) * self.bias

    def initialize(self, e_fd):
        """
        Initializes the SEXS model for simulation.

        Parameters:
            e_fd (float or torch.Tensor): The initial value for the field voltage.
        """
        # put the values here that shall come out of the blocks in the first time step so that all derivatives are zero
        in1 = self.pt1_lim.initialize(e_fd)
        self.bias = self.lead_lag.initialize(in1)

from mxcube3.core.adapter.adapter_base import ActuatorAdapterBase
from mxcube3.core.adapter.utils import RateLimited


class WavelengthAdapter(ActuatorAdapterBase):
    """
    Adapter for wavelength Hardware Object, a web socket is used communicate
    information on longer running processes.
    """

    def __init__(self, ho, *args, **kwargs):
        """
        Args:
            (object): Hardware object.
        """
        super(WavelengthAdapter, self).__init__(ho, *args, **kwargs)
        self._type = "FLOAT"

        try:
            ho.connect("energyChanged", self._value_change)
            ho.connect("stateChanged", self.state_change)
        except BaseException:
            pass

    @RateLimited(6)
    def _value_change(self, pos, wl, *args, **kwargs):
        self.value_change(wl)

    def _set_value(self, value):
        """
        Execute the sequence to set the value.
        Args:
            value (float): Target wavelength [Å].
        Returns:
            (float as str): The actual value set.
        Raises:
            ValueError: Value not valid or attemp to set read only value.
            RuntimeError: Timeout while setting the value.
            StopItteration: When a value change was interrupted (abort/cancel).
        """
        try:
            self._ho.set_wavelength(float(value))
            return self.get_value()
        except BaseException:
            raise

    def _get_value(self):
        """
        Read the wavelength value.
        Returns:
            (float as str): Wavelength [Å].
        Raises:
            ValueError: When value for any reason can't be retrieved.
        """
        try:
            return self._ho.get_wavelength()
        except (AttributeError, TypeError):
            raise ValueError("Could not get value")

    def state(self):
        """
        Get the state.
        Returns:
            (str): The state
        """
        # The state is an enum, return the name only
        return self._ho.get_state().name

    def stop(self):
        """
        Stop the execution.
       """
        self._ho.abort()

    def limits(self):
        """
        Read the wavelengt limits.
        Returns:
            (tuple): Two floats (min, max) limits.
        Raises:
            ValueError: When limits for any reason can't be retrieved.
        """
        try:
            return self._ho.get_wavelength_limits()
        except (AttributeError, TypeError):
            raise ValueError("Could not get limits")

    def read_only(self):
        """
        Check if the wavelength is read only or not.
        Retuns:
            (bool): True if read only, False if not.
        """
        return self._ho.read_only

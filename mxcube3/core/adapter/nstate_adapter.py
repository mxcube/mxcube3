from enum import Enum
from mxcubecore.HardwareObjects.abstract import AbstractNState
from mxcubecore.HardwareObjects.abstract import AbstractShutter

from mxcube3.core.adapter.adapter_base import ActuatorAdapterBase
from mxcube3.core.models import NStateModel

class NStateAdapter(ActuatorAdapterBase):
    def __init__(self, ho, *args, **kwargs):
        """
        Args:
            (object): Hardware object.
        """
        super(NStateAdapter, self).__init__(ho, *args, **kwargs)
        self._type = "NSTATE"

        ho.connect("valueChanged", self._value_change)
        ho.connect("stateChanged", self.state_change)

    def _value_change(self, value):
        if isinstance(value, Enum):
            v = value.name
        else:
            v = value

        self.value_change(v)

    def _get_valid_states(self):
        state_names = [v.name for v in self._ho.VALUES]
        state_names.remove("UNKNOWN")

        return state_names

    def _get_available_states(self):
        state_names = self._get_usable_states()
        state_names.remove(self._ho.get_value().name)

        return state_names

    def commands(self):
        return (self._get_valid_states())

    def _set_value(self, value):
        self._ho.set_value(self._ho.VALUES[value])

    def _get_value(self):
        return self._ho.get_value().name

    def msg(self):
        try:
            msg = self._ho.get_value().name
        except BaseException:
            msg = "---"
            logging.getLogger("MX3.HWR").error(
                "Failed to get beamline attribute message"
            )

        return msg

    def data(self):
        return NStateModel(**self._dict_repr())
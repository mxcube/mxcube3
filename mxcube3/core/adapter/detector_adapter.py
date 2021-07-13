from mxcube3.core.adapter.adapter_base import AdapterBase
from mxcube3.core.adapter.motor_adapter import MotorAdapter


class DetectorAdapter(AdapterBase):
    def __init__(self, ho, *args, **kwargs):
        """
        Args:
            (object): Hardware object.
        """
        super(DetectorAdapter, self).__init__(ho, *args, **kwargs)
        ho.connect("statusChanged", self._state_change)
        self._type = "OBJECT"

        # self._adapt()

    def _state_change(self, *args, **kwargs):
        self.state_change(self.get_value(), **kwargs)

    def state(self):
        return self._ho.get_state().name

from mxcubecore.BaseHardwareObjects import HardwareObjectState

from mxcube3.core.adapter.adapter_base import ActuatorAdapterBase
from mxcube3.core.models import HOModel, HOMachineInfoModel
from mxcube3.core.adapter.utils import RateLimited


class MachineInfoAdapter(ActuatorAdapterBase):
    def __init__(self, ho, *args, **kwargs):
        """
        Args:
            (object): Hardware object.
        """
        super(MachineInfoAdapter, self).__init__(ho, *args, **kwargs)
        ho.connect("valueChanged", self._value_change)

    def _set_value(self, value):
        pass

    @RateLimited(0.1)
    def _value_change(self, *args, **kwargs):
        self.value_change(self.get_value(), **kwargs)

    def _get_value(self):
        return {
            "current": self.get_current(),
            "message": self.get_message(),
            "fillmode": self.get_fill_mode(),
        }

    def get_message(self):
        try:
            message = self._ho.getMessage()
        except (TypeError, AttributeError):
            message = ""

        return message

    def get_current(self):
        try:
            current = self._ho.getCurrent()
            current = (
                current
                if isinstance(current, str)
                else "{:.1f} mA".format(round(float(self._ho.getCurrent()), 1))
            )
        except (TypeError, AttributeError):
            current = "-1"

        return current

    def get_fill_mode(self):
        try:
            fmode = self._ho.getFillMode()
        except (TypeError, AttributeError):
            fmode = ""

        return fmode

    def limits(self):
        """
        Returns: The detector distance limits.
        """
        return (-1, -1)

    def stop(self):
        pass

    def state(self):
        return HardwareObjectState.READY.value

    def data(self):
        return HOMachineInfoModel(**self._dict_repr())

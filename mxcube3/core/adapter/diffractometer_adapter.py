from mxcube3.core.adapter.adapter_base import AdapterBase

class DiffractometerAdapter(AdapterBase):
    def __init__(self, ho, *args, **kwargs):
        """
        Args:
            (object): Hardware object.
        """
        super(DiffractometerAdapter, self).__init__(ho, *args, **kwargs)
        ho.connect("stateChanged", self._state_change)
        self._type = "OBJECT"

        # self._adapt()

    def _state_change(self, *args, **kwargs):
        self.state_change(self.get_value(), **kwargs)

    def stop(self):
        pass

    def state(self):
        return ""
        return "READY" if self._ho.is_ready() else "BUSY"

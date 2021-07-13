import logging

from mxcubecore.BaseHardwareObjects import HardwareObjectState

from mxcube3.core.adapter.adapter_base import AdapterBase


class DataPublisherAdapter(AdapterBase):
    def __init__(self, ho, *args, **kwargs):
        """
        Args:
            (object): Hardware object.
        """
        super(DataPublisherAdapter, self).__init__(ho, *args, **kwargs)

        try:
            ho.connect("data", self._new_data_handler)
            ho.connect("start", self._update_publisher_handler)
            ho.connect("end", self._update_publisher_handler)
        except BaseException:
            msg = "Could not initialize DataPublisherAdapter"
            logging.getLogger("MX3.HWR").exception(msg)
        else:
            self._available = True

    def _new_data_handler(self, data):
         self._application.server.emit("data_publisher_new_data", data, namespace="/hwr")

    def _update_publisher_handler(self, data):
         self._application.server.emit("data_publisher_update", data, namespace="/hwr")

    def state(self):
        return HardwareObjectState.READY.value

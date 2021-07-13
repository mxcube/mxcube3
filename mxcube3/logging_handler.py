from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import traceback

class MX3LoggingHandler(logging.handlers.BufferingHandler):
    def __init__(self, server):
        super().__init__(1000)
        self.server = server

        @server.flask_socketio.on("connect", namespace="/logging")
        @server.ws_restrict
        def connect():
            # this is needed to create the namespace, and the actual connection
            # to the server, but we don't need to do anything more
            pass


    def _record_to_json(self, record):
        if record.exc_info:
            stack_trace = "".join(traceback.format_exception(*record.exc_info))
        else:
            stack_trace = ""
        try:
            record.asctime
        except AttributeError:
            record.asctime = logging._defaultFormatter.formatTime(record)

        return {
            "message": record.getMessage(),
            "severity": record.levelname,
            "timestamp": record.asctime,
            "logger": record.name,
            "stack_trace": stack_trace,
        }

    def emit(self, record):
        if record.name != "geventwebsocket.handler":
            record_dict = self._record_to_json(record)
            super().emit(record_dict)
            self.server.emit("log_record", record_dict, namespace="/logging")
        else:
            super().emit(record)

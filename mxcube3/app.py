"""
Module that contains application wide settings and state as well as functions
for accessing and manipulating those.
"""
import datetime
import os
import sys
import logging
import traceback
import pickle
import atexit
import json

from logging import StreamHandler, NullHandler
from logging.handlers import TimedRotatingFileHandler

from mxcubecore import HardwareRepository as hwr
from mxcubecore import removeLoggingHandlers
from mxcubecore.HardwareObjects import (QueueManager, queue_entry)
from mxcubecore.ConvertUtils import make_table

from mxcube3.video import streaming_processes
from mxcube3.logging_handler import MX3LoggingHandler
from mxcube3.core.adapter.utils import get_adapter_cls_from_hardware_object
from mxcube3.core.adapter.adapter_base import AdapterBase


removeLoggingHandlers()

class MXCUBECore():
    # The HardwareRepository object
    HWR = None

    # Below, all the HardwareObjects made available through this module,
    # Initialized by the init function

    # BeamlineSetup
    beamline_ho = None
    # XMLRPCServer
    actions = None
    # Plotting
    plotting = None

    adapter_dict = {}

    @staticmethod
    def get_hwo(obj, name):
        """
        Convenience method for getting HardwareObjects from the HardwareRepository.
        Retrieves the HardwareObject with the name <name> from either the
        HardwareRepository or from a parent HardwareObject passed as <obj>

        Handles exceptions with exit_with_error, which means that the application
        will exit on exception

        :param obj: HardwreObject or HardwareRepository
        :param str name: The name of the HardwreObject

        :rtype: HardwareObject
        :return: The HardwareObject
        """
        ho = None

        try:
            if hasattr(obj, "get_hardware_object"):
                ho = obj.get_hardware_object(name)
            else:
                ho = obj.get_object_by_role(name)
        except Exception:
            msg = "Could not initialize hardware object corresponding to %s \n"
            msg = msg % name.upper()
            msg += "Make sure that all related device servers are running \n"
            msg += "Make sure that the detector software is running \n"

            MXCUBECore.exit_with_error(msg)

        return ho

    @staticmethod
    def exit_with_error(msg):
        """
        Writes the traceback and msg to the log and exits the application

        :param str msg: Additional message to write to log

        """
        logging.getLogger("HWR").error(traceback.format_exc())

        if msg:
            logging.getLogger("HWR").error(msg)

        msg = "Could not initialize one or several hardware objects, stopped "
        msg += "at first error !"

        logging.getLogger("HWR").error(msg)
        logging.getLogger("HWR").error("Quitting server !")
        sys.exit(-1)

    @staticmethod
    def init(app, hwdir):
        """
        Initializes the HardwareRepository with XML files read from hwdir.

        The hwr module must be imported at the very beginning of the application
        start-up to function correctly.

        This method can however be called later, so that initialization can be
        done when one wishes.

        :param hwr: HardwareRepository module
        :param str hwdir: Path to hardware objects

        :return: None
        """
        from mxcube3.core.adapter.beamline_adapter import BeamlineAdapter

        fname = os.path.dirname(__file__)
        hwr.add_hardware_objects_dirs([os.path.join(fname, "HardwareObjects")])
        hwr.init_hardware_repository(os.path.abspath(os.path.expanduser(hwdir)))
        _hwr = hwr.get_hardware_repository()
        _hwr.connect()

        MXCUBECore.HWR = _hwr
       
        try:
            MXCUBECore.beamline_ho = hwr.beamline
            MXCUBECore.beamline = BeamlineAdapter(hwr.beamline, MXCUBEApplication)
            MXCUBECore.adapt_hardware_objects(app)

        except Exception:
            msg = "Could not initialize one or several hardware objects, "
            msg += "stopped at first error ! \n"
            msg += "Make sure That all devices servers are running \n"
            msg += "Make sure that the detector software is running \n"
            MXCUBECore.exit_with_error(msg)


    @staticmethod
    def _import_adapter_cls(adapter_cls_str):
        adapter_mod = importlib.import_module(
            f"mxcube3.core.adapter.{utils.str_to_snake(adapter_cls_str)}"
        )

        return getattr(adapter_mod, adapter_cls_str)

    @staticmethod
    def _get_object_from_id(_id):
        if _id in MXCUBECore.adapter_dict:
            return MXCUBECore.adapter_dict[_id]["adapter"]

    @staticmethod
    def _get_adapter_id(ho):
        try:
            if ho.username != None:
                _id = ho.username
            else:
                _id = ho.name()[1:]
        except:
            _id = ho.name()[1:]

        return _id.replace(" ", "_").lower()

    
    @staticmethod
    def _add_adapter(_id, adapter_cls, ho, adapter_instance):
        if _id not in MXCUBECore.adapter_dict:
            MXCUBECore.adapter_dict[_id] = {
                "id": str(_id),
                "adapter_cls": adapter_cls.__name__,
                "ho": ho.name()[1:],
                "adapter": adapter_instance
            }
        else:
            logging.getLogger("MX3.HWR").warning(f"Skipping {ho.name()}, id: {_id} already exists" % (ho_name, _id))


    @staticmethod
    def get_adapter(_id):
        return MXCUBECore._get_object_from_id(_id)

    def _get_attr_from_path(self, obj, attr):
        """Recurses through an attribute chain to get the attribute."""
        return reduce(getattr, attr.split("."), obj)        

    @staticmethod
    def adapt_hardware_objects(app):
        adapter_config = app.CONFIG.app.adapter_properties or []

        for ho_name in MXCUBECore.HWR.hardware_objects:
            # Go through all hardware objects exposed by mxcubecore
            # hardware reposiotry set id to username if its deinfed
            # use the name otherwise (file name without extension)
            ho = MXCUBECore.HWR.get_hardware_object(ho_name)

            _id = MXCUBECore._get_adapter_id(ho)

            # Try to use the interface exposed by abstract classes in mxcubecore to adapt
            # the object
            adapter_cls = get_adapter_cls_from_hardware_object(ho)

            if adapter_cls:
                try:
                    adapter_instance = adapter_cls(ho, _id, app, **dict(adapter_config))
                    logging.getLogger("MX3.HWR").info("Added adapter for %s" % _id)
                except:
                    logging.getLogger("MX3.HWR").exception("Could not add adapter for %s" % _id)
                    logging.getLogger("MX3.HWR").info("%s not available" % _id)
                    adapter_cls = AdapterBase
                    adapter_instance = AdapterBase(None, _id, app)

                MXCUBECore._add_adapter(_id, adapter_cls, ho, adapter_instance)
            else:
                logging.getLogger("MX3.HWR").info("No adapter for %s" % _id)

        print(make_table(
            ["Name", "Adapter", "HO filename"],
            [[item["id"], item["adapter_cls"], item["ho"]] for item in MXCUBECore.adapter_dict.values()]
        ))

class MXCUBEApplication():
    # Below variables used for internal application state

    # SampleID and sample data of currently mounted sample, to handle samples
    # that are not mounted by sample changer.
    CURRENTLY_MOUNTED_SAMPLE = ""

    # Sample location of sample that are in process of being mounted
    SAMPLE_TO_BE_MOUNTED = ""

    # Method used for sample centring
    CENTRING_METHOD = queue_entry.CENTRING_METHOD.LOOP

    # Look up table for finding the limsID for a corresponding queueID (QueueNode)
    NODE_ID_TO_LIMS_ID = {}

    # Initial file list for user, initialized at login, for creating automatic
    # run numbers
    INITIAL_FILE_LIST = []

    # Lookup table for sample changer location to data matrix or
    # data matrix to location
    SC_CONTENTS = {"FROM_CODE": {}, "FROM_LOCATION": {}}

    # Current sample list, with tasks
    SAMPLE_LIST = {"sampleList": {}, "sampleOrder": []}

    # Users currently logged in
    USERS = {}

    # Path to video device (i.e. /dev/videoX)
    VIDEO_FORMAT = "MPEG1"

    # Contains the complete client side ui state, managed up state_storage.py
    UI_STATE = dict()
    TEMP_DISABLED = []

    # Below variables used for application wide settings

    # Enabled or Disable remote usage
    ALLOW_REMOTE = False

    # Enable timeout gives control (if ALLOW_REMOTE is True)
    TIMEOUT_GIVES_CONTROL = False

    # Enable automatic Mountie of sample when queue executed in
    # "automatic/pipeline" mode
    AUTO_MOUNT_SAMPLE = False

    # Automatically add and execute diffraction plans coming from
    # characterizations
    AUTO_ADD_DIFFPLAN = False

    # Number of sample snapshots taken before collect
    NUM_SNAPSHOTS = 4

    CONFIG = None

    mxcubecore = MXCUBECore()

    server = None

    @staticmethod
    def init(server, hwr_xml_dir, allow_remote, ra_timeout, video_device, log_fpath, cfg):
        """
        Initializes application wide variables, sample video stream, and applies

        :param hwr: HardwareRepository module
        :param str hwr_xml_dir: Path to hardware objects
        :param bool allow_remote: Allow remote usage, True else False
        :param bool ra_timeout: Timeout gives control, True else False
        :param bool video_device: Path to video device

        :return None:
        """
        logging.getLogger("MX3.HWR").info("Starting MXCuBE3...")
        from mxcube3.core import utils

        MXCUBEApplication.server = server
        MXCUBEApplication.ALLOW_REMOTE = allow_remote
        MXCUBEApplication.TIMEOUT_GIVES_CONTROL = ra_timeout
        MXCUBEApplication.CONFIG = cfg

        MXCUBEApplication.mxcubecore.init(MXCUBEApplication, hwr_xml_dir)

        if video_device:
            MXCUBEApplication.init_sample_video(video_device)

        MXCUBEApplication.init_signal_handlers()

        utils.enable_snapshots(
            MXCUBEApplication.mxcubecore.beamline_ho.collect,
            MXCUBEApplication.mxcubecore.beamline_ho.diffractometer,
            MXCUBEApplication.mxcubecore.beamline_ho.sample_view
        )

        atexit.register(MXCUBEApplication.app_atexit)

        # Install server-side UI state storage
        MXCUBEApplication.init_state_storage()
        MXCUBEApplication.init_logging(log_fpath)


    @staticmethod
    def init_sample_video(video_device):
        """
        Initializes video streaming from video device <video_device>, relies on
        v4l2loopback kernel module to write the sample video stream to
        <video_device>.

        The streaming is handled by the streaming module

        :param str video_device: Path to video device, i.e. /dev/videoX

        :return: None
        """
        try:
            MXCUBEApplication.mxcubecore.beamline_ho.sample_view.camera.start_streaming()
        except Exception as ex:
            msg = "Could not initialize video, error was: "
            msg += str(ex)
            logging.getLogger("HWR").info(msg)

    @staticmethod
    def init_signal_handlers():
        """
        Connects the signal handlers defined in routes/signals.py to the
        corresponding signals/events
        """
        from mxcube3.core import beamlineutils
        from mxcube3.core import sviewutils
        from mxcube3.core import scutils
        from mxcube3.core import qutils

        try:
            qutils.init_signals(MXCUBEApplication.mxcubecore.beamline_ho.queue_model)
        except Exception:
            sys.excepthook(*sys.exc_info())

        try:
            sviewutils.init_signals()
        except Exception:
            sys.excepthook(*sys.exc_info())

        try:
            scutils.init_signals()
        except Exception:
            sys.excepthook(*sys.exc_info())

        try:
            beamlineutils.init_signals()
            beamlineutils.diffractometer_init_signals()
        except Exception:
            sys.excepthook(*sys.exc_info())

    @staticmethod
    def init_logging(log_file):
        """
        :param str log_file: Path to log file

        :return: None
        """
        removeLoggingHandlers()

        fmt = "%(asctime)s |%(name)-7s|%(levelname)-7s| %(message)s"
        log_formatter = logging.Formatter(fmt)

        if log_file:
            log_file_handler = TimedRotatingFileHandler(
                log_file, when="midnight", backupCount=7
            )
            os.chmod(log_file, 0o666)
            log_file_handler.setFormatter(log_formatter)

        root_logger = logging.getLogger()
        #root_logger.setLevel(logging.INFO)
        root_logger.addHandler(NullHandler())

        custom_log_handler = MX3LoggingHandler(
            MXCUBEApplication.server
        )
        custom_log_handler.setLevel(logging.DEBUG)
        custom_log_handler.setFormatter(log_formatter)

        exception_logger = logging.getLogger("exceptions")
        hwr_logger = logging.getLogger("HWR")
        mx3_hwr_logger = logging.getLogger("MX3.HWR")
        user_logger = logging.getLogger("user_level_log")
        queue_logger = logging.getLogger("queue_exec")
        stdout_log_handler = StreamHandler(sys.stdout)
        stdout_log_handler.setFormatter(log_formatter)

        for logger in (
            exception_logger,
            hwr_logger,
            user_logger,
            mx3_hwr_logger,
            queue_logger,
        ):
            logger.addHandler(custom_log_handler)
            logger.addHandler(stdout_log_handler)

            if log_file:
                logger.addHandler(log_file_handler)

    @staticmethod
    def init_state_storage():
        """
        Set up of server side state storage, the UI state of the client is
        stored on the server
        """
        from mxcube3 import state_storage

        state_storage.init()

    @staticmethod
    def get_ui_properties():
        # Add type information to each component retrieved from the beamline adapter 
        # (either via config or via mxcubecore.beamline)
        for item_name, item_data in MXCUBEApplication.CONFIG.app.ui_properties.items():
            for component_data in item_data["components"]:
                try:
                    mxcore = MXCUBEApplication.mxcubecore
                    adapter = mxcore.get_adapter(component_data["attribute"])
                    adapter_cls_name = type(adapter).__name__
                    value_type = adapter.value_type
                except AttributeError as ex:
                    adapter_cls_name = ""
                    value_type = ""
                else:
                    adapter_cls_name = adapter_cls_name.replace("Adapter", "")
    
                if not "object_type" in component_data:
                    component_data["object_type"] = adapter_cls_name
                
                if not "value_type" in component_data:
                    component_data["value_type"] = value_type


        return MXCUBEApplication.CONFIG.app.ui_properties

    @staticmethod
    def save_settings():
        """
        Saves all application wide variables to disk, stored-mxcube-session.json
        """

        from mxcube3.core import qutils

        queue = qutils.queue_to_dict(MXCUBEApplication.mxcubecore.beamline_ho.queue_model.get_model_root())

        # For the moment not storing USERS

        data = {
            "QUEUE": queue,
            "CURRENTLY_MOUNTED_SAMPLE": CURRENTLY_MOUNTED_SAMPLE,
            "SAMPLE_TO_BE_MOUNTED": SAMPLE_TO_BE_MOUNTED,
            "CENTRING_METHOD": CENTRING_METHOD,
            "NODE_ID_TO_LIMS_ID": NODE_ID_TO_LIMS_ID,
            "INITIAL_FILE_LIST": INITIAL_FILE_LIST,
            "SC_CONTENTS": SC_CONTENTS,
            "SAMPLE_LIST": SAMPLE_LIST,
            "TEMP_DISABLED": TEMP_DISABLED,
            "ALLOW_REMOTE": ALLOW_REMOTE,
            "TIMEOUT_GIVES_CONTROL": TIMEOUT_GIVES_CONTROL,
            "VIDEO_FORMAT": VIDEO_FORMAT,
            "AUTO_MOUNT_SAMPLE": AUTO_MOUNT_SAMPLE,
            "AUTO_ADD_DIFFPLAN": AUTO_ADD_DIFFPLAN,
            "NUM_SNAPSHOTS": NUM_SNAPSHOTS,
            "UI_STATE": UI_STATE,
        }

        with open("stored-mxcube-session.json", "w") as fp:
            json.dump(data, fp)

    @staticmethod
    def load_settings():
        """
        Loads application wide variables from "stored-mxcube-session.json"
        """
        with open("stored-mxcube-session.json", "r") as f:
            data = json.load(f)

        from mxcube3.core import qutils

        qutils.load_queue_from_dict(data.get("QUEUE", {}))

        MXCUBEApplication.CENTRING_METHOD = data.get("CENTRING_METHOD", queue_entry.CENTRING_METHOD.LOOP)
        MXCUBEApplication.NODE_ID_TO_LIMS_ID = data.get("NODE_ID_TO_LIMS_ID", {})
        MXCUBEApplication.SC_CONTENTS = data.get("SC_CONTENTS", {"FROM_CODE": {}, "FROM_LOCATION": {}})
        MXCUBEApplication.SAMPLE_LIST = data.get("SAMPLE_LIST", {"sampleList": {}, "sampleOrder": []})
        MXCUBEApplication.ALLOW_REMOTE = data.get("ALLOW_REMOTE", False)
        MXCUBEApplication.TIMEOUT_GIVES_CONTROL = data.get("TIMEOUT_GIVES_CONTROL", False)
        MXCUBEApplication.AUTO_MOUNT_SAMPLE = data.get("AUTO_MOUNT_SAMPLE", False)
        MXCUBEApplication.AUTO_ADD_DIFFPLAN = data.get("AUTO_ADD_DIFFPLAN", False)
        MXCUBEApplication.NUM_SNAPSHOTS = data.get("NUM_SNAPSHOTS", False)
        MXCUBEApplication.UI_STATE = data.get("UI_STATE", {})

    @staticmethod
    def app_atexit():
        pass

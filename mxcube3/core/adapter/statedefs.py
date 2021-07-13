# -*- coding: utf-8 -*-
class MOTOR_STATE(object):
    """
    Motor states, to be added to AbstractMotor definition when the web-
    application is in a more mature state.
    """

    NOTINITIALIZED = "NOTINITIALIZED"
    UNUSABLE = "UNUSABLE"
    READY = "READY"
    MOVESTARTED = "MOVESTARTED"
    MOVING = "MOVING"
    ONLIMIT = "ONLIMIT"

    VALUE_TO_STR = {
        0: "NOTINITIALIZED",
        1: "UNUSABLE",
        2: "READY",
        3: "MOVESTARTED",
        4: "MOVING",
        5: "ONLIMIT",
    }


ABSTRACT_NSTATE_TO_VALUE = {
    "CLOSED": 0,
    "OUT": 0,
    "OPEN": 1,
    "IN": 1,
    "UNKNOWN": 2,
    "UDEFINED": 2,
}


class INOUT_STATE(object):
    """
    States for inout devices, mapped to the client (UI) representation of
    in out devices. IN state to be interpreted as positive
    (high/active/enabled) and OUT as negative (low/inactive/disabled).
    """

    IN = "in"
    OUT = "out"
    UNDEFINED = "undefined"

    TO_INOUT_STATE = {IN: IN, OUT: OUT}

    STR_TO_VALUE = {OUT: 0, IN: 1, UNDEFINED: 2}

    STATE_TO_MSG_STR = {OUT: "OUT", IN: "IN"}


class TANGO_SHUTTER_STATE(object):
    """
    State mapping for TangoShuter.TangoShutter
    """

    TO_INOUT_STATE = {
        "closed": INOUT_STATE.IN,
        "opened": INOUT_STATE.OUT,
        "close": INOUT_STATE.IN,
        "open": INOUT_STATE.OUT,
    }

    STATE_TO_MSG_STR = {INOUT_STATE.OUT: "OPEN", INOUT_STATE.IN: "CLOSED"}


class BEAMSTOP_STATE(object):
    """
    State mapping for Beamstop
    """

    TO_INOUT_STATE = {"in": INOUT_STATE.IN, "out": INOUT_STATE.OUT}

    STATE_TO_MSG_STR = {INOUT_STATE.OUT: "OUT", INOUT_STATE.IN: "IN"}


class ABSTRACT_NSTATE(object):
    TO_INOUT_STATE = {}
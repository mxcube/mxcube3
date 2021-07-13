# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import json
import pickle as pickle
import redis
import itertools
import logging
import re

from mock import Mock

from mxcubecore.HardwareObjects import queue_model_objects as qmo
from mxcubecore.HardwareObjects import queue_entry as qe
from mxcubecore.HardwareObjects import queue_model_enumerables as qme
from mxcubecore.HardwareObjects.base_queue_entry import QUEUE_ENTRY_STATUS

from mxcube3 import mxcube
from mxcube3 import server

from . import limsutils
from . import utils

from functools import reduce

# Important: same constants as in constants.js
QUEUE_PAUSED = "QueuePaused"
QUEUE_RUNNING = "QueueRunning"
QUEUE_STOPPED = "QueueStopped"
QUEUE_FAILED = "QueueFailed"

SAMPLE_MOUNTED = 0x8
COLLECTED = 0x4
WARNING = 0x10
FAILED = 0x2
RUNNING = 0x1
UNCOLLECTED = 0x0
READY = 0

ORIGIN_MX3 = "MX3"
QUEUE_CACHE = {}


def is_collected(task):
    return (task["state"] & COLLECTED) == COLLECTED


def get_queue_from_cache():
    return QUEUE_CACHE


def build_prefix_path_dict(path_list):
    prefix_path_dict = {}

    for path in path_list:
        try:
            path, run_number, img_number = qmo.PathTemplate.interpret_path(path)
        except ValueError:
            logging.getLogger("MX3.HWR").info(
                '[QUEUE] Warning, failed to interpret path: "%s", please check path'
                % path
            )
            path, run_number, image_number = (path, 0, 0)

        prefix_path_dict[path] = run_number

    return prefix_path_dict


def get_run_number(pt):
    prefix_path_dict = build_prefix_path_dict(mxcube.INITIAL_FILE_LIST)

    # Path templates of files not yet written to to disk, we are only
    # interested in the prefix path
    fname = pt.get_image_path()
    prefix_path, _, _ = qmo.PathTemplate.interpret_path(fname)
    run_number = mxcube.mxcubecore.beamline_ho.queue_model.get_next_run_number(pt)

    if prefix_path in prefix_path_dict:
        rn = run_number + prefix_path_dict[prefix_path]
    else:
        rn = run_number

    return rn


def node_index(node):
    """
    Get the position (index) in the queue, sample and node id of node <node>.

    :returns: dictionary on the form:
              {'sample': sample, 'idx': index, 'queue_id': node_id}
    """
    sample, index, sample_model = None, None, None

    # RootNode nothing to return
    if isinstance(node, qmo.RootNode):
        sample, idx = None, None
    # For samples simply return the sampleID
    elif isinstance(node, qmo.Sample):
        sample = node.loc_str
    # TaskGroup just return the sampleID
    elif node.get_parent():
        if isinstance(node, qmo.TaskGroup):
            sample_model = node.get_parent()
        else:
            sample_model = node.get_parent().get_parent()

        sample = sample_model.loc_str
        task_groups = sample_model.get_children()
        tlist = []

        for group in task_groups:
            if group.interleave_num_images:
                tlist.append(group)
            else:
                tlist.extend(group.get_children())

        try:
            index = tlist.index(node)
        except Exception:
            pass

    return {
        "sample": sample,
        "idx": index,
        "queue_id": node._node_id,
        "sample_node": sample_model,
    }


def load_queue_from_dict(queue_dict):
    """
    Loads the queue in queue_dict in to the current mxcube.mxcubecore.beamline_ho.queue_model (mxcube.mxcubecore.beamline_ho.queue_model)

    :param dict queue_dict: Queue dictionary, on the same format as returned by
                            queue_to_dict
    """
    if queue_dict:
        item_list = []

        for sid in queue_dict["sample_order"]:
            item_list.append(queue_dict[sid])

        queue_add_item(item_list)


def queue_to_dict(node=None, include_lims_data=False):
    """
    Returns the dictionary representation of the queue

    :param TaskNode node: list of Node objects to get representation for,
                          queue root used if nothing is passed.

    :returns: dictionary on the form:
              { sampleID_1:{ sampleID_1: sid_1,
                             queueID: qid_1,
                             location: location_n
                             tasks: [task1, ... taskn]},
                             .
                             .
                             .
                sampleID_N:{ sampleID_N: sid_N,
                             queueID: qid_N,
                             location: location_n,
                             tasks: [task1, ... taskn]}

             where the contents of task is a dictionary, the content depends on
             the TaskNode type (DataCollection, Chracterisation, Sample). The
             task dict can be directly used with the set_from_dict methods of
             the corresponding node.
    """
    if not node:
        node = mxcube.mxcubecore.beamline_ho.queue_model.get_model_root()

    res = reduce(
        lambda x, y: x.update(y) or x, queue_to_dict_rec(node, include_lims_data), {}
    )

    return res


def queue_to_json(node=None, include_lims_data=False):
    """
    Returns the json representation of the queue

    :param TaskNode node: list of Node objects to get representation for,
                          queue root used if nothing is passed.

    :returns: json str on the form:
              [ { sampleID_1: sid_1,
                  queueID: qid_1,
                  location: location_n
                  tasks: [task1, ... taskn]},
                .
                .
                .
                { sampleID_N: sid_N,
                  queueID: qid_N,
                  location: location_n,
                  tasks: [task1, ... taskn]} ]

             where the contents of task is a dictionary, the content depends on
             the TaskNode type (Datacollection, Chracterisation, Sample). The
             task dict can be directly used with the set_from_dict methods of
             the corresponding node.
    """
    if not node:
        node = mxcube.mxcubecore.beamline_ho.queue_model.get_model_root()

    res = reduce(
        lambda x, y: x.update(y) or x, queue_to_dict_rec(node, include_lims_data), {}
    )

    return json.dumps(res, sort_keys=True, indent=4)


def get_node_state(node_id):
    """
    Get the state of the given node.

    :param TaskNode node: Node to get state for

    :returns: tuple containing (enabled, state)
              where state: {0, 1, 2, 3} = {in_queue, running, success, failed}
              {'sample': sample, 'idx': index, 'queue_id': node_id}
    """
    try:
        node, entry = get_entry(node_id)
    except BaseException:
        return (True, UNCOLLECTED)

    enabled = node.is_enabled()
    curr_entry = mxcube.mxcubecore.beamline_ho.queue_manager.get_current_entry()

    running = mxcube.mxcubecore.beamline_ho.queue_manager.is_executing and (
        curr_entry == entry or curr_entry == entry._parent_container
    )

    if entry.status == QUEUE_ENTRY_STATUS.FAILED:
        state = FAILED
    elif node.is_executed() or entry.status == QUEUE_ENTRY_STATUS.SUCCESS:
        state = COLLECTED
    elif running or entry.status == QUEUE_ENTRY_STATUS.RUNNING:
        state = RUNNING
    else:
        state = UNCOLLECTED

    return (enabled, state)


def get_queue_state():
    """
    Return the dictionary representation of the current queue and its state

    :returns: dictionary on the form:
              {
                loaded: ID of currently loaded sample,
                queue: same format as queue_to_dict() but without sample_order,
                queueStatus: one of [QUEUE_PAUSED, QUEUE_RUNNING, QUEUE_STOPPED]
              }
    """
    from . import scutils

    queue = queue_to_dict(include_lims_data=True)
    sample_order = queue.get("sample_order", [])
    try:
        current = scutils.get_current_sample().get("sampleID", "")
    except Exception as ex:
        logging.getLogger("MX3.HWR").warning(
            "Error retrieving current sample, {0}".format(ex.message)
        )
        current = ""

    res = {
        "current": current,
        "centringMethod": mxcube.CENTRING_METHOD,
        "autoMountNext": get_auto_mount_sample(),
        "autoAddDiffPlan": mxcube.AUTO_ADD_DIFFPLAN,
        "numSnapshots": mxcube.NUM_SNAPSHOTS,
        "groupFolder": mxcube.mxcubecore.beamline_ho.session.get_group_name(),
        "queue": sample_order,
        "sampleList": limsutils.sample_list_get(current_queue=queue),
        "queueStatus": queue_exec_state(),
    }

    return res


def _handle_dc(sample_node, node, include_lims_data=False):
    parameters = node.as_dict()
    parameters["shape"] = getattr(node, "shape", "")
    parameters["helical"] = node.experiment_type == qme.EXPERIMENT_TYPE.HELICAL
    parameters["mesh"] = node.experiment_type == qme.EXPERIMENT_TYPE.MESH

    parameters.pop("sample")
    parameters.pop("acquisitions")
    parameters.pop("acq_parameters")
    parameters.pop("centred_position")

    queueID = node._node_id
    enabled, state = get_node_state(queueID)

    parameters["subdir"] = os.path.join(
        *parameters["path"].split(mxcube.mxcubecore.beamline_ho.session.raw_data_folder_name)[1:]
    ).lstrip("/")

    pt = node.acquisitions[0].path_template

    parameters["fileName"] = pt.get_image_file_name().replace(
        "%" + ("%sd" % str(pt.precision)), int(pt.precision) * "#"
    )

    parameters["fullPath"] = os.path.join(parameters["path"], parameters["fileName"])

    limsres = {}
    lims_id = mxcube.NODE_ID_TO_LIMS_ID.get(node._node_id, "null")

    # Only add data from lims if explicitly asked for, since
    # its a operation that can take some time.
    if include_lims_data and mxcube.mxcubecore.beamline_ho.lims.lims_rest:
        limsres = mxcube.mxcubecore.beamline_ho.lims.lims_rest.get_dc(lims_id)

    # Always add link to data, (no request made)
    limsres["limsTaskLink"] = limsutils.get_dc_link(lims_id)

    res = {
        "label": "Data Collection",
        "type": "DataCollection",
        "parameters": parameters,
        "sampleID": sample_node.loc_str,
        "sampleQueueID": sample_node._node_id,
        "taskIndex": node_index(node)["idx"],
        "queueID": queueID,
        "checked": node.is_enabled(),
        "state": state,
        "limsResultData": limsres,
    }

    return res


def _handle_wf(sample_node, node, include_lims_data):
    queueID = node._node_id
    enabled, state = get_node_state(queueID)
    parameters = node.parameters
    parameters.update(node.path_template.as_dict())

    parameters["path"] = parameters["directory"]

    parameters["subdir"] = os.path.join(
        *parameters["path"].split(mxcube.mxcubecore.beamline_ho.session.raw_data_folder_name)[1:]
    ).lstrip("/")

    pt = node.path_template

    parameters["fileName"] = pt.get_image_file_name().replace(
        "%" + ("%sd" % str(pt.precision)), int(pt.precision) * "#"
    )

    parameters["fullPath"] = os.path.join(parameters["path"], parameters["fileName"])

    limsres = {}
    lims_id = mxcube.NODE_ID_TO_LIMS_ID.get(node._node_id, "null")

    # Only add data from lims if explicitly asked for, since
    # its a operation that can take some time.
    if include_lims_data and mxcube.mxcubecore.beamline_ho.lims.lims_rest:
        limsres = mxcube.mxcubecore.beamline_ho.lims.lims_rest.get_dc(lims_id)

    # Always add link to data, (no request made)
    limsres["limsTaskLink"] = limsutils.get_dc_link(lims_id)

    res = {
        "label": parameters["label"],
        "type": "Workflow",
        "name": node._type,
        "parameters": parameters,
        "sampleID": sample_node.loc_str,
        "taskIndex": node_index(node)["idx"],
        "queueID": queueID,
        "checked": node.is_enabled(),
        "state": state,
        "limsResultData": limsres,
    }

    return res


def _handle_xrf(sample_node, node):
    queueID = node._node_id
    enabled, state = get_node_state(queueID)
    parameters = {"countTime": node.count_time, "shape": node.shape}
    parameters.update(node.path_template.as_dict())
    parameters["path"] = parameters["directory"]

    parameters["subdir"] = os.path.join(
        *parameters["path"].split(mxcube.mxcubecore.beamline_ho.session.raw_data_folder_name)[1:]
    ).lstrip("/")

    pt = node.path_template

    parameters["fileName"] = pt.get_image_file_name().replace(
        "%" + ("%sd" % str(pt.precision)), int(pt.precision) * "#"
    )

    parameters["fullPath"] = os.path.join(parameters["path"], parameters["fileName"])
    model, entry = get_entry(queueID)

    res = {
        "label": "XRF Scan",
        "type": "XRFScan",
        "parameters": parameters,
        "sampleID": sample_node.loc_str,
        "taskIndex": node_index(node)["idx"],
        "queueID": queueID,
        "sampleQueueID": sample_node._node_id,
        "checked": node.is_enabled(),
        "state": state,
    }

    return res


def _handle_energy_scan(sample_node, node):
    queueID = node._node_id
    enabled, state = get_node_state(queueID)
    parameters = {"element": node.element_symbol, "edge": node.edge, "shape": -1}

    parameters.update(node.path_template.as_dict())
    parameters["path"] = parameters["directory"]

    parameters["subdir"] = os.path.join(
        *parameters["path"].split(mxcube.mxcubecore.beamline_ho.session.raw_data_folder_name)[1:]
    ).lstrip("/")

    pt = node.path_template

    parameters["fileName"] = pt.get_image_file_name().replace(
        "%" + ("%sd" % str(pt.precision)), int(pt.precision) * "#"
    )

    parameters["fullPath"] = os.path.join(parameters["path"], parameters["fileName"])

    res = {
        "label": "Energy Scan",
        "type": "EnergyScan",
        "parameters": parameters,
        "sampleID": sample_node.loc_str,
        "sampleQueueID": sample_node._node_id,
        "taskIndex": node_index(node)["idx"],
        "queueID": queueID,
        "checked": node.is_enabled(),
        "state": state,
    }

    return res


def _handle_char(sample_node, node, include_lims_data=False):
    parameters = node.characterisation_parameters.as_dict()
    parameters["shape"] = node.get_point_index()
    refp = _handle_dc(sample_node, node.reference_image_collection)["parameters"]

    parameters.update(refp)

    queueID = node._node_id
    enabled, state = get_node_state(queueID)

    limsres = {}
    lims_id = mxcube.NODE_ID_TO_LIMS_ID.get(node._node_id, "null")

    # Only add data from lims if explicitly asked for, since
    # its a operation that can take some time.
    if include_lims_data and mxcube.mxcubecore.beamline_ho.lims.lims_rest:
        limsres = mxcube.mxcubecore.beamline_ho.lims.lims_rest.get_dc(lims_id)

    # Always add link to data, (no request made)
    limsres["limsTaskLink"] = limsutils.get_dc_link(lims_id)

    originID, task = _handle_diffraction_plan(node, sample_node)

    res = {
        "label": "Characterisation",
        "type": "Characterisation",
        "parameters": parameters,
        "checked": node.is_enabled(),
        "sampleID": sample_node.loc_str,
        "sampleQueueID": sample_node._node_id,
        "taskIndex": node_index(node)["idx"],
        "queueID": node._node_id,
        "state": state,
        "limsResultData": limsres,
        "diffractionPlan": task,
        "diffractionPlanID": originID,
    }

    return res


def _handle_diffraction_plan(node, sample_node):
    model, entry = get_entry(node._node_id)
    originID = model.get_origin()
    tasks = []

    if len(model.diffraction_plan) == 0:
        return (-1, {})
    else:
        collections = model.diffraction_plan[0]  # a list of lists

        for col in collections:
            t = _handle_dc(sample_node, col)
            if t is None:
                tasks.append({})
                continue

            t["isDiffractionPlan"] = True
            tasks.append(t)

        return (originID, tasks)

    return (-1, {})


def _handle_interleaved(sample_node, node):
    wedges = []

    for child in node.get_children():
        wedges.append(_handle_dc(sample_node, child))

    queueID = node._node_id
    enabled, state = get_node_state(queueID)

    res = {
        "label": "Interleaved",
        "type": "Interleaved",
        "parameters": {"wedges": wedges, "swNumImages": node.interleave_num_images},
        "checked": node.is_enabled(),
        "sampleID": sample_node.loc_str,
        "sampleQueueID": sample_node._node_id,
        "taskIndex": node_index(node)["idx"],
        "queueID": node._node_id,
        "state": state,
    }

    return res


def _handle_sample(node, include_lims_data=False):
    location = "Manual" if node.free_pin_mode else node.loc_str
    enabled, state = get_node_state(node._node_id)
    children_states = []

    for child in node.get_children():
        for _c in child.get_children():
            child_enabled, child_state = get_node_state(_c._node_id)
            children_states.append(child_state)

    if RUNNING in children_states:
        state = RUNNING & SAMPLE_MOUNTED
    elif 3 in children_states:
        state = FAILED & SAMPLE_MOUNTED
    elif all(i == COLLECTED for i in children_states) and len(children_states) > 0:
        state = COLLECTED & SAMPLE_MOUNTED
    else:
        state = UNCOLLECTED

    sample = {
        "sampleID": node.loc_str,
        "queueID": node._node_id,
        "code": node.code,
        "location": location,
        "sampleName": node.get_name(),
        "proteinAcronym": node.crystals[0].protein_acronym,
        "defaultPrefix": limsutils.get_default_prefix(node, False),
        "defaultSubDir": limsutils.get_default_subdir(node),
        "type": "Sample",
        "checked": enabled,
        "state": state,
        "tasks": queue_to_dict_rec(node, include_lims_data),
    }

    return {node.loc_str: sample}


def queue_to_dict_rec(node, include_lims_data=False):
    """
    Parses node recursively and builds a representation of the queue based on
    python dictionaries.

    :param TaskNode node: The node to parse
    :returns: A list on the form:
              [ { sampleID_1: sid_1,
                  queueID: qid_1,
                  location: location_n
                  tasks: [task1, ... taskn]},
                .
                .
                .
                { sampleID_N: sid_N,
                  queueID: qid_N,
                  location: location_n,
                  tasks: [task1, ... taskn]} ]
    """
    result = []

    if isinstance(node, list):
        node_list = node
    else:
        node_list = node.get_children()

    for node in node_list:
        if isinstance(node, qmo.Sample):
            if len(result) == 0:
                result = [{"sample_order": []}]

            result.append(_handle_sample(node, include_lims_data))

            if node.is_enabled():
                result[0]["sample_order"].append(node.loc_str)

        elif isinstance(node, qmo.Characterisation):
            sample_node = node.get_parent().get_parent()
            result.append(_handle_char(sample_node, node, include_lims_data))
        elif isinstance(node, qmo.DataCollection):
            sample_node = node_index(node)["sample_node"]
            result.append(_handle_dc(sample_node, node, include_lims_data))
        elif isinstance(node, qmo.Workflow):
            sample_node = node.get_parent().get_parent()
            result.append(_handle_wf(sample_node, node, include_lims_data))
        elif isinstance(node, qmo.XRFSpectrum):
            sample_node = node.get_parent().get_parent()
            result.append(_handle_xrf(sample_node, node))
        elif isinstance(node, qmo.EnergyScan):
            sample_node = node.get_parent().get_parent()
            result.append(_handle_energy_scan(sample_node, node))
        elif isinstance(node, qmo.TaskGroup) and node.interleave_num_images:
            sample_node = node.get_parent()
            result.append(_handle_interleaved(sample_node, node))
        else:
            result.extend(queue_to_dict_rec(node, include_lims_data))

    return result


def queue_exec_state():
    """
    :returns: The queue execution state, one of QUEUE_STOPPED, QUEUE_PAUSED
              or QUEUE_RUNNING

    """
    state = QUEUE_STOPPED

    if mxcube.mxcubecore.beamline_ho.queue_manager.is_paused():
        state = QUEUE_PAUSED
    elif mxcube.mxcubecore.beamline_ho.queue_manager.is_executing():
        state = QUEUE_RUNNING

    return state


def get_entry(_id):
    """
    Retrieves the model and the queue entry for the model node with id <id>

    :param int id: Node id of node to retrieve
    :returns: The tuple model, entry
    :rtype: Tuple
    """
    model = mxcube.mxcubecore.beamline_ho.queue_model.get_node(int(_id))
    entry = mxcube.mxcubecore.beamline_ho.queue_manager.get_entry_with_model(model)
    return model, entry


def set_enabled_entry(qid, enabled):
    model, entry = get_entry(qid)
    model.set_enabled(enabled)
    entry.set_enabled(enabled)


def delete_entry(entry):
    """
    Helper function that deletes an entry and its model from the queue
    """
    parent_entry = entry.get_container()
    parent_entry.dequeue(entry)
    model = entry.get_data_model()
    mxcube.mxcubecore.beamline_ho.queue_model.del_child(model.get_parent(), model)
    logging.getLogger("MX3.HWR").info("[QUEUE] is:\n%s " % queue_to_json())


def delete_entry_at(item_pos_list):
    current_queue = queue_to_dict()

    for (sid, tindex) in item_pos_list:
        if tindex in ["undefined", None]:
            node_id = current_queue[sid]["queueID"]
            model, entry = get_entry(node_id)
        else:
            node_id = current_queue[sid]["tasks"][int(tindex)]["queueID"]
            model, entry = get_entry(node_id)

            # Get the TaskGroup of the item, there is currently only one
            # task per TaskGroup so we have to remove the entire TaskGroup
            # with its task.
            if not isinstance(entry, qe.TaskGroupQueueEntry):
                entry = entry.get_container()

        delete_entry(entry)


def enable_entry(id_or_qentry, flag):
    """
    Helper function that sets the enabled flag to <flag> for the entry
    and associated model. Takes either the model node id or the QueueEntry
    object.

    Sets enabled flag on both the entry and model.

    :param object id_or_qentry: Node id of model or QueueEntry object
    :param bool flag: True for enabled False for disabled
    """
    if isinstance(id_or_qentry, qe.BaseQueueEntry):
        id_or_qentry.set_enabled(flag)
        id_or_qentry.get_data_model().set_enabled(flag)
    else:
        model, entry = get_entry(id_or_qentry)
        entry.set_enabled(flag)
        model.set_enabled(flag)


def swap_task_entry(sid, ti1, ti2):
    """
    Swaps order of two queue entries in the queue, with the same sample <sid>
    as parent

    :param str sid: Sample id
    :param int ti1: Position of task1 (old position)
    :param int ti2: Position of task2 (new position)
    """
    current_queue = queue_to_dict()

    node_id = current_queue[sid]["queueID"]
    smodel, sentry = get_entry(node_id)

    # Swap the order in the queue model
    ti2_temp_model = smodel.get_children()[ti2]
    smodel._children[ti2] = smodel._children[ti1]
    smodel._children[ti1] = ti2_temp_model

    # Swap queue entry order
    ti2_temp_entry = sentry._queue_entry_list[ti2]
    sentry._queue_entry_list[ti2] = sentry._queue_entry_list[ti1]
    sentry._queue_entry_list[ti1] = ti2_temp_entry

    logging.getLogger("MX3.HWR").info("[QUEUE] is:\n%s " % queue_to_json())


def move_task_entry(sid, ti1, ti2):
    """
    Swaps order of two queue entries in the queue, with the same sample <sid>
    as parent

    :param str sid: Sample id
    :param int ti1: Position of task1 (old position)
    :param int ti2: Position of task2 (new position)
    """
    current_queue = queue_to_dict()

    node_id = current_queue[sid]["queueID"]
    smodel, sentry = get_entry(node_id)

    # Swap the order in the queue model
    smodel._children.insert(ti2, smodel._children.pop(ti1))

    # Swap queue entry order
    sentry._queue_entry_list.insert(ti2, sentry._queue_entry_list.pop(ti1))

    logging.getLogger("MX3.HWR").info("[QUEUE] is:\n%s " % queue_to_json())


def set_sample_order(order):
    """
    Set the sample order of the queue
    :param list sample_order: List of sample ids
    """
    current_queue = queue_to_dict()
    sid_list = list([sid for sid in order if current_queue.get(sid, False)])

    if sid_list:
        queue_id_list = [current_queue[sid]["queueID"] for sid in sid_list]
        model_entry_list = [get_entry(qid) for qid in queue_id_list]
        model_list = [model_entry[0] for model_entry in model_entry_list]
        entry_list = [model_entry[1] for model_entry in model_entry_list]

        # Set the order in the queue model
        mxcube.mxcubecore.beamline_ho.queue_model.get_model_root()._children = model_list
        # Set queue entry order
        mxcube.mxcubecore.beamline_ho.queue_manager._queue_entry_list = entry_list

    limsutils.sample_list_set_order(order)

    logging.getLogger("MX3.HWR").info("[QUEUE] is:\n%s " % queue_to_json())


def queue_add_item(item_list):
    """
    Adds the queue items in item_list to the queue. The items in the list can
    be either samples and or tasks. Samples are only added if they are not
    already in the queue  and tasks are appended to the end of an
    (already existing) sample. A task is ignored if the sample is not already
    in the queue.

    The items in item_list are dictionaries with the following structure:

    { "type": "Sample | DataCollection | Characterisation",
      "sampleID": sid
      ... task or sample specific data
    }

    Each item (dictionary) describes either a sample or a task.
    """
    _queue_add_item_rec(item_list, None)

    # Handling interleaved data collections, swap interleave task with
    # the first of the data collections that are used as wedges, and then
    # remove all collections that were used as wedges
    for task in item_list[0]["tasks"]:
        if task["type"] == "Interleaved" and task["parameters"].get(
            "taskIndexList", False
        ):
            current_queue = queue_to_dict()

            sid = task["sampleID"]
            interleaved_tindex = len(current_queue[sid]["tasks"]) - 1

            tindex_list = sorted(task["parameters"]["taskIndexList"])

            # Swap first "wedge task" and the actual interleaved collection
            # so that the interleaved task is the first task
            swap_task_entry(sid, interleaved_tindex, tindex_list[0])

            # We remove the swapped wedge index from the list, (now pointing
            # at the interleaved collection) and add its new position
            # (last task item) to the list.
            tindex_list = tindex_list[1:]
            tindex_list.append(interleaved_tindex)

            # The delete operation can be done all in one call if we make sure
            # that we remove the items starting from the end (not altering
            # previous indices)
            for ti in reversed(tindex_list):
                delete_entry_at([[sid, int(ti)]])

    res = queue_to_dict()

    return res


def _queue_add_item_rec(item_list, sample_node_id=None):
    """
    Adds the queue items in item_list to the queue. The items in the list can
    be either samples and or tasks. Samples are only added if they are not
    already in the queue  and tasks are appended to the end of an
    (already existing) sample. A task is ignored if the sample is not already
    in the queue.

    The items in item_list are dictionaries with the following structure:

    { "type": "Sample | DataCollection | Characterisation",
      "sampleID": sid
      ... task or sample specific data
    }

    Each item (dictionary) describes either a sample or a task.
    """
    children = []

    for item in item_list:
        item_t = item["type"]
        # If the item a sample, then add it and its tasks. If its not, get the
        # node id for the sample of the new task and append it to the sample
        sample_id = str(item["sampleID"])

        if item_t == "Sample":
            # Do not add samples that are already in the queue
            if not item.get("queueID", False):
                sample_node_id = add_sample(sample_id, item)
            else:
                set_enabled_entry(item["queueID"], True)
                sample_node_id = item["queueID"]

            tasks = item.get("tasks")

            if tasks:
                _queue_add_item_rec(tasks, sample_node_id)
                children.extend(tasks)

        else:
            if not sample_node_id:
                sample_node_id = item.get("sampleQueueID", None)

        if item_t == "DataCollection":
            add_data_collection(sample_node_id, item)
        elif item_t == "Interleaved":
            add_interleaved(sample_node_id, item)
        elif item_t == "Characterisation":
            add_characterisation(sample_node_id, item)
        elif item_t == "Workflow":
            add_workflow(sample_node_id, item)
        elif item_t == "XRFScan":
            add_xrf_scan(sample_node_id, item)
        elif item_t == "EnergyScan":
            add_energy_scan(sample_node_id, item)


def add_sample(sample_id, item):
    """
    Adds a sample with sample id <sample_id> the queue.

    :param str sample_id: Sample id (often sample changer location)
    :returns: SampleQueueEntry
    """
    sample_model = qmo.Sample()
    sample_model.set_origin(ORIGIN_MX3)
    sample_model.set_from_dict(item)

    # Explicitly set parameters that are not sent by the client
    sample_model.loc_str = sample_id
    sample_model.free_pin_mode = item["location"] == "Manual"
    sample_model.set_name(item["sampleName"])
    sample_model.name = item["sampleName"]

    if sample_model.free_pin_mode:
        sample_model.location = (None, sample_id)
    else:
        sample_model.location = tuple(map(int, item["location"].split(":")))

    # Manually added sample, make sure that i'ts on the server side sample list
    if item["location"] == "Manual":
        item["defaultSubDir"] = limsutils.get_default_subdir(item)
        limsutils.sample_list_update_sample(sample_id, item)

    sample_entry = qe.SampleQueueEntry(view=Mock(), data_model=sample_model)
    enable_entry(sample_entry, True)

    mxcube.mxcubecore.beamline_ho.queue_model.add_child(
        mxcube.mxcubecore.beamline_ho.queue_model.get_model_root(), sample_model
    )
    mxcube.mxcubecore.beamline_ho.queue_manager.enqueue(sample_entry)

    return sample_model._node_id


def set_dc_params(model, entry, task_data, sample_model):
    """
    Helper method that sets the data collection parameters for a DataCollection.

    :param DataCollectionQueueModel: The model to set parameters of
    :param DataCollectionQueueEntry: The queue entry of the model
    :param dict task_data: Dictionary with new parameters
    """
    acq = model.acquisitions[0]
    params = task_data["parameters"]
    acq.acquisition_parameters.set_from_dict(params)

    ftype = mxcube.mxcubecore.beamline_ho.detector.get_property("file_suffix")
    ftype = ftype if ftype else ".?"

    acq.path_template.set_from_dict(params)
    # certain attributes have to be updated explicitly,
    # like precision, suffix ...
    acq.path_template.start_num = params["first_image"]
    acq.path_template.num_files = params["num_images"]
    acq.path_template.suffix = ftype
    acq.path_template.precision = "0" + str(
        mxcube.mxcubecore.beamline_ho.session["file_info"].get_property("precision", 4)
    )

    limsutils.apply_template(params, sample_model, acq.path_template)

    if params["prefix"]:
        acq.path_template.base_prefix = params["prefix"]
    else:
        acq.path_template.base_prefix = mxcube.mxcubecore.beamline_ho.session.get_default_prefix(
            sample_model, False
        )

    full_path = os.path.join(
        mxcube.mxcubecore.beamline_ho.session.get_base_image_directory(), params.get("subdir", "")
    )

    acq.path_template.directory = full_path

    process_path = os.path.join(
        mxcube.mxcubecore.beamline_ho.session.get_base_process_directory(),
        params.get("subdir", ""),
    )
    acq.path_template.process_directory = process_path

    # TODO, Please remove this ad-hoc definition
    #
    # MXCuBE3 specific shape attribute
    model.shape = params["shape"]

    # If there is a centered position associated with this data collection, get
    # the necessary data for the position and pass it to the collection.
    if params["helical"]:
        model.experiment_type = qme.EXPERIMENT_TYPE.HELICAL
        acq2 = qmo.Acquisition()
        model.acquisitions.append(acq2)

        line = mxcube.mxcubecore.beamline_ho.sample_view.get_shape(params["shape"])
        p1, p2 = line.refs
        p1, p2 = (
            mxcube.mxcubecore.beamline_ho.sample_view.get_shape(p1),
            mxcube.mxcubecore.beamline_ho.sample_view.get_shape(p2),
        )
        cpos1 = p1.get_centred_position()
        cpos2 = p2.get_centred_position()

        acq.acquisition_parameters.centred_position = cpos1
        acq2.acquisition_parameters.centred_position = cpos2

    elif params.get("mesh", False):
        grid = mxcube.mxcubecore.beamline_ho.sample_view.get_shape(params["shape"])
        acq.acquisition_parameters.mesh_range = (grid.width, grid.height)
        mesh_center = mxcube.mxcubecore.beamline_ho["default_mesh_values"].get_property(
            "mesh_center", "top-left"
        )
        if mesh_center == "top-left":
            acq.acquisition_parameters.centred_position = grid.get_centred_positions()[
                0
            ]
        else:
            acq.acquisition_parameters.centred_position = grid.get_centred_positions()[
                1
            ]
        acq.acquisition_parameters.mesh_steps = grid.get_num_lines()
        acq.acquisition_parameters.num_images = task_data["parameters"]["num_images"]

        model.experiment_type = qme.EXPERIMENT_TYPE.MESH
        model.set_requires_centring(False)

    elif params["shape"] != -1:
        point = mxcube.mxcubecore.beamline_ho.sample_view.get_shape(params["shape"])
        cpos = point.get_centred_position()
        acq.acquisition_parameters.centred_position = cpos

    # Only get a run number for new tasks, keep the already existing
    # run number for existing items.
    if not task_data.get("queueID", ""):
        acq.path_template.run_number = get_run_number(acq.path_template)

    model.set_enabled(task_data["checked"])
    entry.set_enabled(task_data["checked"])


def set_wf_params(model, entry, task_data, sample_model):
    """
    Helper method that sets the parameters for a workflow task.

    :param WorkflowQueueModel: The model to set parameters of
    :param GenericWorkflowQueueEntry: The queue entry of the model
    :param dict task_data: Dictionary with new parameters
    """
    params = task_data["parameters"]
    model.parameters = params
    model.path_template.set_from_dict(params)
    model.path_template.base_prefix = params["prefix"]
    model.path_template.num_files = 0
    model.path_template.precision = "0" + str(
        mxcube.mxcubecore.beamline_ho.session["file_info"].get_property("precision", 4)
    )

    limsutils.apply_template(params, sample_model, model.path_template)

    if params["prefix"]:
        model.path_template.base_prefix = params["prefix"]
    else:
        model.path_template.base_prefix = mxcube.mxcubecore.beamline_ho.session.get_default_prefix(
            sample_model, False
        )

    full_path = os.path.join(
        mxcube.mxcubecore.beamline_ho.session.get_base_image_directory(), params.get("subdir", "")
    )

    model.path_template.directory = full_path

    process_path = os.path.join(
        mxcube.mxcubecore.beamline_ho.session.get_base_process_directory(),
        params.get("subdir", ""),
    )
    model.path_template.process_directory = process_path

    model.set_name("Workflow task")
    model.set_type(params["wfname"])

    beamline_params = {}
    beamline_params["directory"] = model.path_template.directory
    beamline_params["prefix"] = model.path_template.get_prefix()
    beamline_params["run_number"] = model.path_template.run_number
    beamline_params["collection_software"] = "MXCuBE - 3.0"
    beamline_params["sample_node_id"] = sample_model._node_id
    beamline_params["sample_lims_id"] = sample_model.lims_id
    beamline_params["beamline"] = mxcube.mxcubecore.beamline_ho.session.endstation_name
    beamline_params["shape"] = params["shape"]

    params_list = list(map(str, list(itertools.chain(*iter(beamline_params.items())))))
    params_list.insert(0, params["wfpath"])
    params_list.insert(0, "modelpath")

    model.params_list = params_list

    model.set_enabled(task_data["checked"])
    entry.set_enabled(task_data["checked"])


def set_char_params(model, entry, task_data, sample_model):
    """
    Helper method that sets the characterisation parameters for a
    Characterisation.

    :param CharacterisationQueueModel: The mode to set parameters of
    :param CharacterisationQueueEntry: The queue entry of the model
    :param dict task_data: Dictionary with new parameters
    """
    params = task_data["parameters"]
    set_dc_params(model.reference_image_collection, entry, task_data, sample_model)

    try:
        params["strategy_complexity"] = ["SINGLE", "FEW", "MANY"].index(
            params["strategy_complexity"]
        )
    except ValueError:
        params["strategy_complexity"] = 0

    model.characterisation_parameters.set_from_dict(params)

    # MXCuBE3 specific shape attribute
    # TODO: Please consider defining shape attribute properly !
    model.shape = params["shape"]

    model.set_enabled(task_data["checked"])
    entry.set_enabled(task_data["checked"])


def set_xrf_params(model, entry, task_data, sample_model):
    """
    Helper method that sets the xrf scan parameters for a XRF spectrum Scan.

    :param XRFSpectrum QueueModel: The model to set parameters of
    :param XRFSpectrumQueueEntry: The queue entry of the model
    :param dict task_data: Dictionary with new parameters
    """
    params = task_data["parameters"]

    ftype = mxcube.mxcubecore.beamline_ho.xrf_spectrum.get_property("file_suffix", "dat").strip()

    model.path_template.set_from_dict(params)
    model.path_template.suffix = ftype
    model.path_template.precision = "0" + str(
        mxcube.mxcubecore.beamline_ho.session["file_info"].get_property("precision", 4)
    )

    if params["prefix"]:
        model.path_template.base_prefix = params["prefix"]
    else:
        model.path_template.base_prefix = mxcube.mxcubecore.beamline_ho.session.get_default_prefix(
            sample_model, False
        )

    full_path = os.path.join(
        mxcube.mxcubecore.beamline_ho.session.get_base_image_directory(), params.get("subdir", "")
    )

    model.path_template.directory = full_path

    process_path = os.path.join(
        mxcube.mxcubecore.beamline_ho.session.get_base_process_directory(),
        params.get("subdir", ""),
    )
    model.path_template.process_directory = process_path

    # Only get a run number for new tasks, keep the already existing
    # run number for existing items.
    if not params.get("queueID", ""):
        model.path_template.run_number = get_run_number(model.path_template)

    # Set count time, and if any, other paramters
    model.count_time = params.get("countTime", 0)

    # MXCuBE3 specific shape attribute
    model.shape = params["shape"]

    model.set_enabled(task_data["checked"])
    entry.set_enabled(task_data["checked"])


def set_energy_scan_params(model, entry, task_data, sample_model):
    """
    Helper method that sets the xrf scan parameters for a XRF spectrum Scan.

    :param EnergyScan QueueModel: The model to set parameters of
    :param EnergyScanQueueEntry: The queue entry of the model
    :param dict task_data: Dictionary with new parameters
    """
    params = task_data["parameters"]

    ftype = mxcube.mxcubecore.beamline_ho.energy_scan.get_property("file_suffix", "raw").strip()

    model.path_template.set_from_dict(params)
    model.path_template.suffix = ftype
    model.path_template.precision = "0" + str(
        mxcube.mxcubecore.beamline_ho.session["file_info"].get_property("precision", 4)
    )

    if params["prefix"]:
        model.path_template.base_prefix = params["prefix"]
    else:
        model.path_template.base_prefix = mxcube.mxcubecore.beamline_ho.session.get_default_prefix(
            sample_model, False
        )

    full_path = os.path.join(
        mxcube.mxcubecore.beamline_ho.session.get_base_image_directory(), params.get("subdir", "")
    )

    model.path_template.directory = full_path

    process_path = os.path.join(
        mxcube.mxcubecore.beamline_ho.session.get_base_process_directory(),
        params.get("subdir", ""),
    )
    model.path_template.process_directory = process_path

    # Only get a run number for new tasks, keep the already existing
    # run number for existing items.
    if not params.get("queueID", ""):
        model.path_template.run_number = get_run_number(model.path_template)

    # Set element, and if any, other parameters
    model.element_symbol = params.get("element", "")
    model.edge = params.get("edge", "")

    model.set_enabled(task_data["checked"])
    entry.set_enabled(task_data["checked"])


def _create_dc(task):
    """
    Creates a data collection model and its corresponding queue entry from
    a dict with collection parameters.

    :param dict task: Collection parameters
    :returns: The tuple (model, entry)
    :rtype: Tuple
    """
    dc_model = qmo.DataCollection()
    dc_model.set_origin(ORIGIN_MX3)
    dc_model.center_before_collect = True
    dc_entry = qe.DataCollectionQueueEntry(Mock(), dc_model)

    return dc_model, dc_entry


def _create_wf(task):
    """
    Creates a workflow model and its corresponding queue entry from
    a dict with collection parameters.

    :param dict task: Collection parameters
    :returns: The tuple (model, entry)
    :rtype: Tuple
    """
    dc_model = qmo.Workflow()
    dc_model.set_origin(ORIGIN_MX3)
    dc_entry = qe.GenericWorkflowQueueEntry(Mock(), dc_model)

    return dc_model, dc_entry


def _create_xrf(task):
    """
    Creates a XRFSpectrum model and its corresponding queue entry from
    a dict with collection parameters.

    :param dict task: Collection parameters
    :returns: The tuple (model, entry)
    :rtype: Tuple
    """
    xrf_model = qmo.XRFSpectrum()
    xrf_model.set_origin(ORIGIN_MX3)
    xrf_entry = qe.XRFSpectrumQueueEntry(Mock(), xrf_model)

    return xrf_model, xrf_entry


def _create_energy_scan(task, sample_model):
    """
    Creates a energy scan model and its corresponding queue entry from
    a dict with collection parameters.

    :param dict task: Collection parameters
    :returns: The tuple (model, entry)
    :rtype: Tuple
    """
    escan_model = qmo.EnergyScan(sample=sample_model)
    escan_model.set_origin(ORIGIN_MX3)
    escan_entry = qe.EnergyScanQueueEntry(Mock(), escan_model)

    return escan_model, escan_entry


def add_characterisation(node_id, task):
    """
    Adds a data characterisation task to the sample with id: <id>

    :param int id: id of the sample to which the task belongs
    :param dict task: Task data (parameters)

    :returns: The queue id of the Data collection
    :rtype: int
    """
    sample_model, sample_entry = get_entry(node_id)
    params = task["parameters"]

    refdc_model, refdc_entry = _create_dc(task)
    refdc_model.acquisitions[0].path_template.reference_image_prefix = "ref"
    refdc_model.set_name("refdc")
    char_params = qmo.CharacterisationParameters().set_from_dict(params)

    char_model = qmo.Characterisation(refdc_model, char_params)

    char_model.set_origin(ORIGIN_MX3)
    char_entry = qe.CharacterisationGroupQueueEntry(Mock(), char_model)
    char_entry.queue_model = mxcube.mxcubecore.beamline_ho.queue_model
    # Set the characterisation and reference collection parameters
    set_char_params(char_model, char_entry, task, sample_model)

    # the default value is True, here we adapt to mxcube3 needs
    char_model.auto_add_diff_plan = mxcube.AUTO_ADD_DIFFPLAN
    char_entry.auto_add_diff_plan = mxcube.AUTO_ADD_DIFFPLAN

    # A characterisation has two TaskGroups one for the characterisation itself
    # and its reference collection and one for the resulting diffraction plans.
    # But we only create a reference group if there is a result !
    refgroup_model = qmo.TaskGroup()
    refgroup_model.set_origin(ORIGIN_MX3)

    mxcube.mxcubecore.beamline_ho.queue_model.add_child(sample_model, refgroup_model)
    mxcube.mxcubecore.beamline_ho.queue_model.add_child(refgroup_model, char_model)
    refgroup_entry = qe.TaskGroupQueueEntry(Mock(), refgroup_model)

    refgroup_entry.set_enabled(True)
    sample_entry.enqueue(refgroup_entry)
    refgroup_entry.enqueue(char_entry)

    char_model.set_enabled(task["checked"])
    char_entry.set_enabled(task["checked"])

    return char_model._node_id


def add_data_collection(node_id, task):
    """
    Adds a data collection task to the sample with id: <id>

    :param int id: id of the sample to which the task belongs
    :param dict task: task data

    :returns: The queue id of the data collection
    :rtype: int
    """
    sample_model, sample_entry = get_entry(node_id)
    dc_model, dc_entry = _create_dc(task)
    set_dc_params(dc_model, dc_entry, task, sample_model)

    group_model = qmo.TaskGroup()
    group_model.set_origin(ORIGIN_MX3)
    group_model.set_enabled(True)
    mxcube.mxcubecore.beamline_ho.queue_model.add_child(sample_model, group_model)
    mxcube.mxcubecore.beamline_ho.queue_model.add_child(group_model, dc_model)

    group_entry = qe.TaskGroupQueueEntry(Mock(), group_model)
    group_entry.set_enabled(True)
    sample_entry.enqueue(group_entry)
    group_entry.enqueue(dc_entry)

    return dc_model._node_id


def add_workflow(node_id, task):
    """
    Adds a worklfow task to the sample with id: <id>

    :param int id: id of the sample to which the task belongs
    :param dict task: task data

    :returns: The queue id of the data collection
    :rtype: int
    """
    sample_model, sample_entry = get_entry(node_id)
    wf_model, dc_entry = _create_wf(task)
    set_wf_params(wf_model, dc_entry, task, sample_model)

    group_model = qmo.TaskGroup()
    group_model.set_origin(ORIGIN_MX3)
    group_model.set_enabled(True)
    mxcube.mxcubecore.beamline_ho.queue_model.add_child(sample_model, group_model)
    mxcube.mxcubecore.beamline_ho.queue_model.add_child(group_model, wf_model)

    group_entry = qe.TaskGroupQueueEntry(Mock(), group_model)
    group_entry.set_enabled(True)
    sample_entry.enqueue(group_entry)
    group_entry.enqueue(dc_entry)

    return wf_model._node_id


def add_interleaved(node_id, task):
    """
    Adds a interleaved data collection task to the sample with id: <id>

    :param int id: id of the sample to which the task belongs
    :param dict task: task data

    :returns: The queue id of the data collection
    :rtype: int
    """
    sample_model, sample_entry = get_entry(node_id)

    group_model = qmo.TaskGroup()
    group_model.set_origin(ORIGIN_MX3)
    group_model.set_enabled(True)
    group_model.interleave_num_images = task["parameters"]["swNumImages"]

    group_entry = qe.TaskGroupQueueEntry(Mock(), group_model)
    group_entry.set_enabled(True)
    sample_entry.enqueue(group_entry)
    mxcube.mxcubecore.beamline_ho.queue_model.add_child(sample_model, group_model)

    wc = 0

    for wedge in task["parameters"]["wedges"]:
        wc = wc + 1
        dc_model, dc_entry = _create_dc(wedge)
        set_dc_params(dc_model, dc_entry, wedge, sample_model)

        # Add wedge prefix to path
        dc_model.acquisitions[0].path_template.wedge_prefix = "wedge-%s" % wc

        # Disable snapshots for sub-wedges
        dc_model.acquisitions[0].acquisition_parameters.take_snapshots = False

        mxcube.mxcubecore.beamline_ho.queue_model.add_child(group_model, dc_model)
        group_entry.enqueue(dc_entry)

    return group_model._node_id


def add_xrf_scan(node_id, task):
    """
    Adds a XRF Scan task to the sample with id: <id>

    :param int id: id of the sample to which the task belongs
    :param dict task: task data

    :returns: The queue id of the data collection
    :rtype: int
    """
    sample_model, sample_entry = get_entry(node_id)
    xrf_model, xrf_entry = _create_xrf(task)
    set_xrf_params(xrf_model, xrf_entry, task, sample_model)

    group_model = qmo.TaskGroup()
    group_model.set_origin(ORIGIN_MX3)
    group_model.set_enabled(True)
    mxcube.mxcubecore.beamline_ho.queue_model.add_child(sample_model, group_model)
    mxcube.mxcubecore.beamline_ho.queue_model.add_child(group_model, xrf_model)

    group_entry = qe.TaskGroupQueueEntry(Mock(), group_model)
    group_entry.set_enabled(True)
    sample_entry.enqueue(group_entry)
    group_entry.enqueue(xrf_entry)

    return xrf_model._node_id


def add_energy_scan(node_id, task):
    """
    Adds a energy scan task to the sample with id: <id>

    :param int id: id of the sample to which the task belongs
    :param dict task: task data

    :returns: The queue id of the data collection
    :rtype: int
    """
    sample_model, sample_entry = get_entry(node_id)
    escan_model, escan_entry = _create_energy_scan(task, sample_model)
    set_energy_scan_params(escan_model, escan_entry, task, sample_model)

    group_model = qmo.TaskGroup()
    group_model.set_origin(ORIGIN_MX3)
    group_model.set_enabled(True)
    mxcube.mxcubecore.beamline_ho.queue_model.add_child(sample_model, group_model)
    mxcube.mxcubecore.beamline_ho.queue_model.add_child(group_model, escan_model)

    group_entry = qe.TaskGroupQueueEntry(Mock(), group_model)
    group_entry.set_enabled(True)
    sample_entry.enqueue(group_entry)
    group_entry.enqueue(escan_entry)

    return escan_model._node_id


def clear_queue():
    """
    Creates a new queue
    :returns: MxCuBE QueueModel Object
    """
    from mxcubecore import HardwareRepository as HWR

    # queue = pickle.loads(mxcube.mxcubecore.empty_queue)
    # queue.diffraction_plan = {}
    HWR.beamline.queue_model.diffraction_plan = {}
    HWR.beamline.queue_model.clear_model("ispyb")
    HWR.beamline.queue_model.clear_model("free-pin")
    HWR.beamline.queue_model.clear_model("plate")
    HWR.beamline.queue_model.select_model("ispyb")


def save_queue(session, redis=redis.Redis()):
    """
    Saves the current mxcube.mxcubecore.beamline_ho.queue_model (mxcube.mxcubecore.beamline_ho.queue_model) into a redis database.
    The queue that is saved is the pickled result returned by queue_to_dict

    :param session: Session to save queue for
    :param redis: Redis database

    """
    proposal_id = utils._proposal_id(session)

    if proposal_id is not None:
        # List of samples dicts (containing tasks) sample and tasks have same
        # order as the in queue HO
        queue = queue_to_dict(mxcube.mxcubecore.beamline_ho.queue_model.get_model_root())
        redis.set("mxcube.queue:%d" % proposal_id, pickle.dumps(queue))


def load_queue(session, redis=redis.Redis()):
    """
    Loads the queue belonging to session <session> into redis db <redis>

    :param session: Session for queue to load
    :param redis: Redis database
    """
    proposal_id = utils._proposal_id(session)

    if proposal_id is not None:
        serialized_queue = redis.get("mxcube.queue:%d" % proposal_id)
        queue = pickle.loads(serialized_queue)
        load_queue_from_dict(queue)


def queue_model_child_added(parent, child):
    """
    Listen to the addition of elements to the queue model ('child_added').
    Add the corresponding entries to the queue if they are not already
    added. Handels for instance the addition of reference collections for
    characterisations and workflows.
    """
    parent_model, parent_entry = get_entry(parent._node_id)
    child_model, child_entry = get_entry(child._node_id)

    # Origin is ORIGIN_MX3 if task comes from MXCuBE-3
    if child_model.get_origin() != ORIGIN_MX3:
        if isinstance(child, qmo.DataCollection):
            dc_entry = qe.DataCollectionQueueEntry(Mock(), child)

            enable_entry(dc_entry, True)
            enable_entry(parent_entry, True)
            parent_entry.enqueue(dc_entry)
            sample = parent.get_parent()

            task = _handle_dc(sample, child)
            server.emit("add_task", {"tasks": [task]}, namespace="/hwr")

        elif isinstance(child, qmo.TaskGroup):
            dcg_entry = qe.TaskGroupQueueEntry(Mock(), child)
            enable_entry(dcg_entry, True)
            parent_entry.enqueue(dcg_entry)


def queue_model_diff_plan_available(char, collection_list):
    cols = []
    for collection in collection_list:
        if isinstance(collection, qmo.DataCollection):
            if collection.get_origin():
                origin_model, origin_entry = get_entry(collection.get_origin())
            else:
                origin_model, origin_entry = get_entry(char._node_id)

            collection.set_enabled(False)

            dcg_model = char.get_parent()
            sample = dcg_model.get_parent()

            setattr(collection, "shape", origin_model.shape)

            task = _handle_dc(sample, collection)
            task.update({"isDiffractionPlan": True, "originID": origin_model._node_id})
            cols.append(task)

    server.emit("add_diff_plan", {"tasks": cols}, namespace="/hwr")


def set_auto_add_diffplan(autoadd, current_sample=None):
    """
    Sets auto add diffraction plan flag, automatically add to the queue
    (True) or wait for user (False)

    :param bool autoadd: True autoadd, False wait for user
    """
    mxcube.AUTO_ADD_DIFFPLAN = autoadd
    current_queue = queue_to_dict()

    if "sample_order" in current_queue:
        current_queue.pop("sample_order")

    sampleIDs = list(current_queue.keys())
    for sample in sampleIDs:
        # this would be a sample
        tasks = current_queue[sample]["tasks"]
        for t in tasks:
            if t["type"] == "Characterisation":
                model, entry = get_entry(t["queueID"])
                entry.auto_add_diff_plan = autoadd


def execute_entry_with_id(sid, tindex=None):
    """
    Execute the entry at position (sampleID, task index) in queue

    :param str sid: sampleID
    :param int tindex: task index of task within sample with id sampleID
    """
    from . import scutils

    current_queue = queue_to_dict()
    mxcube.mxcubecore.beamline_ho.queue_manager.set_pause(False)

    if tindex in ["undefined", "None", "null", None]:
        node_id = current_queue[sid]["queueID"]

        # The queue does not run the mount defined by the sample entry if it has no
        # tasks, so in order function as expected; just mount the sample
        if (
            not len(current_queue[sid]["tasks"])
        ) and sid != scutils.get_current_sample().get("sampleID", ""):

            try:
                scutils.mount_sample_clean_up(current_queue[sid])
            except BaseException:
                mxcube.mxcubecore.beamline_ho.queue_manager.emit("queue_execution_failed", (None,))
            else:
                mxcube.mxcubecore.beamline_ho.queue_manager.emit("queue_stopped", (None,))
        else:
            enabled_entries = []

            for sampleID in current_queue["sample_order"]:
                if current_queue[sampleID].get("checked", False):
                    enabled_entries.append(sampleID)

            enabled_entries.pop(enabled_entries.index(sid))
            mxcube.TEMP_DISABLED = enabled_entries
            enable_sample_entries(enabled_entries, False)
            enable_sample_entries([sid], True)

            mxcube.mxcubecore.beamline_ho.queue_manager.execute()
    else:
        node_id = current_queue[sid]["tasks"][int(tindex)]["queueID"]

        node, entry = get_entry(node_id)
        # in order to fill lims data, we execute first the parent (group_id missing)
        parent_id = node.get_parent()._node_id

        node, entry = get_entry(parent_id)

        mxcube.mxcubecore.beamline_ho.queue_manager._running = True

        mxcube.mxcubecore.beamline_ho.queue_manager._is_stopped = False
        mxcube.mxcubecore.beamline_ho.queue_manager._set_in_queue_flag()
        try:
            mxcube.mxcubecore.beamline_ho.queue_manager.execute_entry(entry)
        except BaseException:
            mxcube.mxcubecore.beamline_ho.queue_manager.emit("queue_execution_failed", (None,))
        finally:
            mxcube.mxcubecore.beamline_ho.queue_manager._running = False
            mxcube.mxcubecore.beamline_ho.queue_manager.emit("queue_stopped", (None,))
            mxcube.mxcubecore.beamline_ho.collect.queue_finished_cleanup()


def init_signals(queue):
    """
    Initialize queue hwobj related signals.
    """
    from mxcube3.routes import signals

    mxcube.mxcubecore.beamline_ho.collect.connect(
        mxcube.mxcubecore.beamline_ho.collect, "collectStarted", signals.collect_started
    )
    mxcube.mxcubecore.beamline_ho.collect.connect(
        mxcube.mxcubecore.beamline_ho.collect,
        "collectOscillationStarted",
        signals.collect_oscillation_started,
    )
    mxcube.mxcubecore.beamline_ho.collect.connect(
        mxcube.mxcubecore.beamline_ho.collect,
        "collectOscillationFailed",
        signals.collect_oscillation_failed,
    )
    mxcube.mxcubecore.beamline_ho.collect.connect(
        mxcube.mxcubecore.beamline_ho.collect, "collectImageTaken", signals.collect_image_taken
    )

    mxcube.mxcubecore.beamline_ho.collect.connect(
        mxcube.mxcubecore.beamline_ho.collect,
        "collectOscillationFinished",
        signals.collect_oscillation_finished,
    )

    queue.connect(queue, "child_added", queue_model_child_added)

    queue.connect(queue, "diff_plan_available", queue_model_diff_plan_available)

    mxcube.mxcubecore.beamline_ho.queue_manager.connect(
        "queue_execute_started", signals.queue_execution_started
    )

    mxcube.mxcubecore.beamline_ho.queue_manager.connect(
        "queue_execution_finished", signals.queue_execution_finished
    )

    mxcube.mxcubecore.beamline_ho.queue_manager.connect(
        "queue_stopped", signals.queue_execution_finished
    )

    mxcube.mxcubecore.beamline_ho.queue_manager.connect(
        "queue_paused", signals.queue_execution_paused
    )

    mxcube.mxcubecore.beamline_ho.queue_manager.connect(
        "queue_entry_execute_finished", signals.queue_execution_entry_finished
    )

    mxcube.mxcubecore.beamline_ho.queue_manager.connect(
        "queue_entry_execute_started", signals.queue_execution_entry_started
    )

    mxcube.mxcubecore.beamline_ho.queue_manager.connect("collectEnded", signals.collect_ended)

    mxcube.mxcubecore.beamline_ho.queue_manager.connect(
        "queue_interleaved_started", signals.queue_interleaved_started
    )

    mxcube.mxcubecore.beamline_ho.queue_manager.connect(
        "queue_interleaved_finished", signals.queue_interleaved_finished
    )

    mxcube.mxcubecore.beamline_ho.queue_manager.connect(
        "queue_interleaved_sw_done", signals.queue_interleaved_sw_done
    )

    mxcube.mxcubecore.beamline_ho.queue_manager.connect(
        "energy_scan_finished", signals.energy_scan_finished
    )


def enable_sample_entries(sample_id_list, flag):
    current_queue = queue_to_dict()

    for sample_id in sample_id_list:
        sample_data = current_queue[sample_id]
        enable_entry(sample_data["queueID"], flag)


def set_auto_mount_sample(automount, current_sample=None):
    """
    Sets auto mount next flag, automatically mount next sample in queue
    (True) or wait for user (False)

    :param bool automount: True auto-mount, False wait for user
    """
    mxcube.AUTO_MOUNT_SAMPLE = automount


def get_auto_mount_sample():
    """
    :returns: Returns auto mount flag
    :rtype: bool
    """
    return mxcube.AUTO_MOUNT_SAMPLE


def get_task_progress(node, pdata):
    progress = 0

    if node.is_executed():
        progress = 1
    elif is_interleaved(node):
        progress = (
            (pdata["current_idx"] + 1)
            * pdata["sw_size"]
            / float(pdata["nitems"] * pdata["sw_size"])
        )
    elif isinstance(node, qmo.Characterisation):
        dc = node.reference_image_collection
        total = float(dc.acquisitions[0].acquisition_parameters.num_images) * 2
        progress = pdata / total
    else:
        total = float(node.acquisitions[0].acquisition_parameters.num_images)
        progress = pdata / total

    return progress


def is_interleaved(node):
    return hasattr(node, "interleave_num_images") and \
           node.interleave_num_images != None and \
           node.interleave_num_images > 0


def init_queue_settings():
    mxcube.NUM_SNAPSHOTS = mxcube.mxcubecore.beamline_ho.collect.get_property("num_snapshots", 4)
    mxcube.AUTO_MOUNT_SAMPLE = mxcube.mxcubecore.beamline_ho.collect.get_property(
        "auto_mount_sample", False
    )
    mxcube.AUTO_ADD_DIFFPLAN = mxcube.mxcubecore.beamline_ho.collect.get_property(
        "auto_add_diff_plan", False
    )


def add_default_sample():
    from . import scutils

    sample = {
        "sampleID": "1",
        "sampleName": "noname",
        "proteinAcronym": "noacronym",
        "type": "Sample",
        "defaultPrefix": "noname",
        "location": "Manual",
        "loadable": True,
        "tasks": [],
    }

    try:
        scutils.mount_sample_clean_up(sample)
    except Exception as ex:
        logging.getLogger("MX3.HWR").exception("[SC] sample could not be mounted")
        logging.getLogger("MX3.HWR").exception(str(ex))
    else:
        queue_add_item([sample])


def queue_start(sid):
    """
    Start execution of the queue.

    :returns: Respons object, status code set to:
              200: On success
              409: Queue could not be started
    """
    logging.getLogger("MX3.HWR").info("[QUEUE] Queue going to start")
    from mxcube3.routes import signals

    try:
        # If auto mount sample is false, just run the sample
        # supplied in the call
        if not get_auto_mount_sample():
            if sid:
                execute_entry_with_id(sid)
        else:
            # Making sure all sample entries are enabled before running the
            # queue qutils.enable_sample_entries(queue["sample_order"], True)
            mxcube.mxcubecore.beamline_ho.queue_manager.set_pause(False)
            mxcube.mxcubecore.beamline_ho.queue_manager.execute()

    except Exception as ex:
        signals.queue_execution_failed(ex)
    else:
        logging.getLogger("MX3.HWR").info("[QUEUE] Queue started")


def queue_stop():
    from mxcube3.routes import signals

    if mxcube.mxcubecore.beamline_ho.queue_manager._root_task is not None:
        mxcube.mxcubecore.beamline_ho.queue_manager.stop()
    else:
        qe = mxcube.mxcubecore.beamline_ho.queue_manager.get_current_entry()
        # check if a node/task is executing and stop that one
        if qe:
            try:
                qe.stop()
            except Exception as ex:
                logging.getLogger("MX3.HWR").exception("[QUEUE] Could not stop queue")
            mxcube.mxcubecore.beamline_ho.queue_manager.set_pause(False)
            # the next two is to avoid repeating the task
            # TODO: if you now run the queue it will be enabled and run
            qe.get_data_model().set_executed(True)
            qe.get_data_model().set_enabled(False)
            qe._execution_failed = True

            mxcube.mxcubecore.beamline_ho.queue_manager._is_stopped = True
            signals.queue_execution_stopped()

def queue_pause():
    """
    Pause the execution of the queue
    """
    mxcube.mxcubecore.beamline_ho.queue_manager.pause(True)

    msg = {
        "Signal": queue_exec_state(),
        "Message": "Queue execution paused",
        "State": 1,
    }

    logging.getLogger("MX3.HWR").info("[QUEUE] Paused")

    return msg


def queue_unpause():
    """
    Unpause execution of the queue

    :returns: Response object, status code set to:
              200: On success
              409: Queue could not be unpause
    """
    mxcube.mxcubecore.beamline_ho.queue_manager.pause(False)

    msg = {
        "Signal": queue_exec_state(),
        "Message": "Queue execution started",
        "State": 1,
    }

    logging.getLogger("MX3.HWR").info("[QUEUE] Resumed")

    return msg


def queue_clear():
    limsutils.init_sample_list()
    clear_queue()
    msg = "[QUEUE] Cleared  " + str(
        mxcube.mxcubecore.beamline_ho.queue_model.get_model_root()._name
    )
    logging.getLogger("MX3.HWR").info(msg)


def set_queue(json_queue, session):
    # Clear queue
    # mxcube.mxcubecore.beamline_ho.queue_model = clear_queue()

    # Set new queue
    queue_add_item(json_queue)
    save_queue(session)


def queue_update_item(sqid, tqid, data):
    model, entry = get_entry(tqid)
    sample_model, sample_entry = get_entry(sqid)

    if data["type"] == "DataCollection":
        set_dc_params(model, entry, data, sample_model)
    elif data["type"] == "Characterisation":
        set_char_params(model, entry, data, sample_model)

    logging.getLogger("MX3.HWR").info("[QUEUE] is:\n%s " % queue_to_json())

    return model


def queue_enable_item(qid_list, enabled):

    for qid in qid_list:
        set_enabled_entry(qid, enabled)

    logging.getLogger("MX3.HWR").info("[QUEUE] is:\n%s " % queue_to_json())


def update_sample(sid, params):

    sample_node = mxcube.mxcubecore.beamline_ho.queue_model.get_node(sid)

    if sample_node:
        sample_entry = mxcube.mxcubecore.beamline_ho.queue_manager.get_entry_with_model(
            sample_node
        )
        # TODO: update here the model with the new 'params'
        # missing lines...
        sample_entry.set_data_model(sample_node)
        logging.getLogger("MX3.HWR").info("[QUEUE] sample updated")
    else:
        msg = "[QUEUE] Sample with id %s not in queue, can't update" % sid
        logging.getLogger("MX3.HWR").error(msg)
        raise Exception(msg)


def toggle_node(node_id):
    node = mxcube.mxcubecore.beamline_ho.queue_model.get_node(node_id)
    entry = mxcube.mxcubecore.beamline_ho.queue_manager.get_entry_with_model(node)
    queue = queue_to_dict()

    if isinstance(entry, qe.SampleQueueEntry):
        # this is a sample entry, thus, go through its checked children and
        # toggle those
        if entry.is_enabled():
            entry.set_enabled(False)
            node.set_enabled(False)
        else:
            entry.set_enabled(True)
            node.set_enabled(True)

        new_state = entry.is_enabled()
        for elem in queue[node_id]:
            child_node = mxcube.mxcubecore.beamline_ho.queue_model.get_node(elem["queueID"])
            child_entry = mxcube.mxcubecore.beamline_ho.queue_manager.get_entry_with_model(
                child_node
            )
            if new_state:
                child_entry.set_enabled(True)
                child_node.set_enabled(True)
            else:
                child_entry.set_enabled(False)
                child_node.set_enabled(False)

    else:
        # not a sample so find the parent and toggle directly
        logging.getLogger("MX3.HWR").info(
            "[QUEUE] toggling entry with id: %s" % node_id
        )
        # this is a TaskGroup, so it is not in the parsed queue
        parent_node = node.get_parent()
        # go a level up,
        # this is a TaskGroup for a Char, a sampleQueueEntry if DataCol
        parent_node = parent_node.get_parent()
        if isinstance(parent_node, qmo.TaskGroup):
            parent_node = parent_node.get_parent()
        parent = parent_node._node_id
        parent_entry = mxcube.mxcubecore.beamline_ho.queue_manager.get_entry_with_model(
            parent_node
        )
        # now that we know the sample parent no matter what is the entry
        # (char, dc) check if the brother&sisters are enabled (and enable the
        # parent)
        checked = 0

        for i in queue[parent]:
            # at least one brother is enabled, no need to change parent
            if i["queueID"] != node_id and i["checked"] == 1:
                checked = 1
                break
        if entry.is_enabled():
            entry.set_enabled(False)
            node.set_enabled(False)

        else:
            entry.set_enabled(True)
            node.set_enabled(True)

        new_state = entry.is_enabled()
        for met in queue[parent]:
            if int(met.get("queueID")) == node_id:
                if new_state == 0 and checked == 0:
                    parent_entry.set_enabled(False)
                    parent_node.set_enabled(False)
                elif new_state == 1 and checked == 0:
                    parent_entry.set_enabled(True)
                    parent_node.set_enabled(True)


def add_centring(_id, params):
    msg = "[QUEUE] centring add requested with data: " + str(params)
    logging.getLogger("MX3.HWR").info(msg)

    cent_node = qmo.SampleCentring()
    cent_entry = qe.SampleCentringQueueEntry()
    cent_entry.set_data_model(cent_node)
    cent_entry.set_queue_controller(mxcube.mxcubecore.qm)
    node = mxcube.mxcubecore.beamline_ho.queue_model.get_node(int(id))
    entry = mxcube.mxcubecore.beamline_ho.queue_manager.get_entry_with_model(node)
    entry._set_background_color = Mock()

    new_node = mxcube.mxcubecore.beamline_ho.queue_model.add_child_at_id(int(id), cent_node)
    entry.enqueue(cent_entry)

    logging.getLogger("MX3.HWR").info("[QUEUE] centring added to sample")

    return {"QueueId": new_node, "Type": "Centring", "Params": params}


def get_default_dc_params():
    """
    returns the default values for an acquisition (data collection).
    """
    acq_parameters = mxcube.mxcubecore.beamline_ho.get_default_acquisition_parameters()
    ftype = mxcube.mxcubecore.beamline_ho.detector.get_property("file_suffix")
    ftype = ftype if ftype else ".?"

    return {
        "acq_parameters": {
            "first_image": acq_parameters.first_image,
            "num_images": acq_parameters.num_images,
            "osc_start": acq_parameters.osc_start,
            "osc_range": acq_parameters.osc_range,
            "kappa": acq_parameters.kappa,
            "kappa_phi": acq_parameters.kappa_phi,
            "overlap": acq_parameters.overlap,
            "exp_time": acq_parameters.exp_time,
            "num_passes": acq_parameters.num_passes,
            "resolution": acq_parameters.resolution,
            "energy": acq_parameters.energy,
            "transmission": acq_parameters.transmission,
            "shutterless": acq_parameters.shutterless,
            "detector_mode": acq_parameters.detector_mode,
            "inverse_beam": False,
            "take_dark_current": True,
            "skip_existing_images": False,
            "take_snapshots": True,
            "helical": False,
            "mesh": False,
            "prefixTemplate": "{PREFIX}_{POSITION}",
            "subDirTemplate": "{ACRONYM}/{ACRONYM}-{NAME}",
        },
        "limits": mxcube.mxcubecore.beamline_ho.acquisition_limit_values,
    }


def get_default_char_acq_params():
    """
    returns the default values for a characterisation acquisition.
    TODO: implement as_dict in the qmo.AcquisitionParameters
    """
    acq_parameters = mxcube.mxcubecore.beamline_ho.get_default_acquisition_parameters(
        "characterisation"
    )
    ftype = mxcube.mxcubecore.beamline_ho.detector.get_property("file_suffix")
    ftype = ftype if ftype else ".?"
    char_defaults = (
        mxcube.mxcubecore.beamline_ho.characterisation.get_default_characterisation_parameters().as_dict()
    )

    acq_defaults = {
        "first_image": acq_parameters.first_image,
        "num_images": acq_parameters.num_images,
        "osc_start": acq_parameters.osc_start,
        "osc_range": acq_parameters.osc_range,
        "kappa": acq_parameters.kappa,
        "kappa_phi": acq_parameters.kappa_phi,
        "overlap": acq_parameters.overlap,
        "exp_time": acq_parameters.exp_time,
        "num_passes": acq_parameters.num_passes,
        "resolution": acq_parameters.resolution,
        "energy": acq_parameters.energy,
        "transmission": acq_parameters.transmission,
        "shutterless": False,
        "detector_mode": acq_parameters.detector_mode,
        "inverse_beam": False,
        "take_dark_current": True,
        "skip_existing_images": False,
        "take_snapshots": True,
        "prefixTemplate": "{PREFIX}_{POSITION}",
        "subDirTemplate": "{ACRONYM}/{ACRONYM}-{NAME}",
    }

    char_defaults.update(acq_defaults)

    return {"acq_parameters": char_defaults}


def get_default_mesh_params():
    """
    returns the default values for a mesh.
    """
    acq_parameters = mxcube.mxcubecore.beamline_ho.get_default_acquisition_parameters("mesh")

    return {
        "acq_parameters": {
            "first_image": acq_parameters.first_image,
            "num_images": acq_parameters.num_images,
            "osc_start": acq_parameters.osc_start,
            "osc_range": acq_parameters.osc_range,
            "kappa": acq_parameters.kappa,
            "kappa_phi": acq_parameters.kappa_phi,
            "overlap": acq_parameters.overlap,
            "exp_time": acq_parameters.exp_time,
            "num_passes": acq_parameters.num_passes,
            "resolution": acq_parameters.resolution,
            "energy": acq_parameters.energy,
            "transmission": acq_parameters.transmission,
            "shutterless": acq_parameters.shutterless,
            "detector_mode": acq_parameters.detector_mode,
            "inverse_beam": False,
            "take_dark_current": True,
            "skip_existing_images": False,
            "take_snapshots": True,
            "cell_counting": acq_parameters.cell_counting,
            "cell_spacing": acq_parameters.cell_spacing,
            "prefixTemplate": "{PREFIX}_{POSITION}",
            "subDirTemplate": "{ACRONYM}/{ACRONYM}-{NAME}",
        }
    }


def get_default_xrf_parameters():
    int_time = 5

    try:
        int_time = mxcube.mxcubecore.beamline_ho.xrf_spectrum.get_property(
            "default_integration_time", "5"
        ).strip()
        try:
            int(int_time)
        except ValueError:
            pass

    except Exception:
        msg = "Failed to get object with role: xrf_spectrum. "
        msg += "cannot get default values for XRF"
        logging.getLogger("MX3.HWR").error(msg)

    return {"countTime": int_time}


def get_sample(_id):
    sample = queue_to_dict().get(_id, None)

    if not sample:
        msg = "[QUEUE] sample info could not be retrieved"
        logging.getLogger("MX3.HWR").error(msg)

    return sample


def get_method(sample_id, method_id):
    sample = queue_to_dict().get(int(id), None)

    if not sample:
        msg = "[QUEUE] sample info could not be retrieved"
        logging.getLogger("MX3.HWR").error(msg)
        raise Exception(msg)
    else:
        # Find task with queue id method_id
        for task in sample.tasks:
            if task["queueID"] == int(method_id):
                return task

    msg = "[QUEUE] method info could not be retrieved, it does not exits for"
    msg += " the given sample"
    logging.getLogger("MX3.HWR").exception(msg)

    raise Exception(msg)


def set_group_folder(path):
    if path and path[0] in ["/", "."]:
        path = path[1:]

    if path and path[-1] != "/":
        path += "/"

    path = "".join([c for c in path if re.match(r"^[a-zA-Z0-9_/-]*$", c)])

    mxcube.mxcubecore.beamline_ho.session.set_user_group(path)
    root_path = mxcube.mxcubecore.beamline_ho.session.get_base_image_directory()
    return {"path": path, "rootPath": root_path}

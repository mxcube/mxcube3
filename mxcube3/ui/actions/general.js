import fetch from 'isomorphic-fetch';
import { unselectShapes } from './sampleview';

export function addUserMessage(records, target) {
  return {
    type: 'ADD_USER_MESSAGE',
    records,
    target,
  };
}

export function removeUserMessage(messageID) {
  return { type: 'REMOVE_USER_MESSAGE', messageID };
}


export function clearAllUserMessages() {
  return { type: 'CLEAR_ALL_USER_MESSAGES' };
}


export function setInitialState(data) {
  return { type: 'SET_INITIAL_STATE', data };
}

export function setLoading(loading, title = '', message = '', blocking = false,
  abortFun = undefined) {
  return {
    type: 'SET_LOADING', loading, title, message, blocking, abortFun
  };
}

export function showErrorPanel(show, message = '') {
  return {
    type: 'SHOW_ERROR_PANEL', show, message
  };
}

export function showDialog(show, t, title = '', data = null) {
  return {
    type: 'SHOW_DIALOG', show, t, title, data
  };
}

function parse(response) {
  if (response.status >= 200 && response.status < 300) {
    return response.json();
  }
  const error = new Error(response.statusText);
  error.response = response;
  throw error;
}

function notify(error) {
  // eslint-disable-next-line no-console
  console.error('REQUEST FAILED', error);
}

export function getInitialState() {
  return function (dispatch) {
    const state = {};

    const uiproperties = fetch('mxcube/api/v0.1/uiproperties', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const queue = fetch('mxcube/api/v0.1/queue/queue_state', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    // const motors = fetch('mxcube/api/v0.1/diffractometer/movables/state', {
    //   method: 'GET',
    //   credentials: 'include',
    //   headers: {
    //     Accept: 'application/json',
    //     'Content-type': 'application/json'
    //   }
    // });
    const beamInfo = fetch('mxcube/api/v0.1/beamline/beam/info', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const beamlineSetup = fetch('mxcube/api/v0.1/beamline/', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const sampleVideoInfo = fetch('mxcube/api/v0.1/sampleview/camera', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const diffractometerInfo = fetch('mxcube/api/v0.1/diffractometer/info', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const detectorInfo = fetch('mxcube/api/v0.1/detector/', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const dcParameters = fetch('mxcube/api/v0.1/queue/dc', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const charParameters = fetch('mxcube/api/v0.1/queue/char_acq', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const meshParameters = fetch('mxcube/api/v0.1/queue/mesh', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const xrfParameters = fetch('mxcube/api/v0.1/queue/xrf', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const savedShapes = fetch('mxcube/api/v0.1/sampleview/shapes', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const sampleChangerInitialState = fetch('mxcube/api/v0.1/sample_changer/get_initial_state', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const remoteAccess = fetch('mxcube/api/v0.1/ra/', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const workflow = fetch('mxcube/api/v0.1/workflow/', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
    const log = fetch('mxcube/api/v0.1/log', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });

    const pchains = [
      uiproperties.then(parse).then((json) => { state.uiproperties = json; }).catch(notify),
      queue.then(parse).then((json) => { state.queue = json; }).catch(notify),
      // motors.then(parse).then((json) => { state.Motors = json; }).catch(notify),
      beamInfo.then(parse).then((json) => { state.beamInfo = json; }).catch(notify),
      beamlineSetup.then(parse).then(
        (json) => { state.beamlineSetup = json; return json; }
      ).then(
        (json) => { state.datapath = json.path; return json; }
      ).catch(notify),
      sampleVideoInfo.then(parse).then((json) => { state.Camera = json; }).catch(notify),
      diffractometerInfo.then(parse).then((json) => { Object.assign(state, json); }).catch(notify),
      detectorInfo.then(parse).then((json) => { state.detector = json; }).catch(notify),
      dcParameters.then(parse).then(
        (json) => { state.dcParameters = json.acq_parameters; return json; }
      ).then(
        (json) => { state.acqParametersLimits = json.limits; }
      ).catch(notify),
      charParameters.then(parse).then(
        (json) => { state.charParameters = json.acq_parameters; }
      ).catch(notify),
      meshParameters.then(parse).then(
        (json) => { state.meshParameters = json.acq_parameters; }
      ).catch(notify),
      xrfParameters.then(parse).then(
        (json) => { state.xrfParameters = json; }
      ).catch(notify),
      savedShapes.then(parse).then((json) => { state.shapes = json.shapes; }).catch(notify),
      sampleChangerInitialState.then(parse).then(
        (json) => { state.sampleChangerState = { state: json.state }; return json; }
      ).then(
        (json) => { state.sampleChangerContents = json.contents; return json; }
      ).then(
        (json) => { state.loadedSample = json.loaded_sample; return json; }
      )
        .then(
          (json) => { state.sampleChangerCommands = json.cmds; return json; }
        )
        .then(
          (json) => { state.sampleChangerGlobalState = json.global_state; return json; }
        )
        .catch(notify),
      remoteAccess.then(parse).then((json) => { state.remoteAccess = json.data; }).catch(notify),
      workflow.then(parse).then((json) => { state.workflow = json; }).catch(notify),
      log.then(parse).then((json) => { state.logger = json; }).catch(notify),
    ];

    Promise.all(pchains).then(() => {
      dispatch(setInitialState(state));
    }).then(() => {
      dispatch(unselectShapes({ shapes: state.shapes }));
    });
  };
}

export function showConnectionLostDialog(show = true) {
  return {
    type: 'SHOW_CONNECTION_LOST_DIALOG', show
  };
}

export function showConfirmClearQueueDialog(show = true) {
  return {
    type: 'SHOW_CONFIRM_CLEAR_QUEUE_DIALOG', show
  };
}

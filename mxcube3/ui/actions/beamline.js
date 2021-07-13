import fetch from 'isomorphic-fetch';
// The different states a beamline attribute can assume.
export const STATE = {
  IDLE: 'READY',
  BUSY: 'MOVING',
  ABORT: 'UNUSABLE'
};


// Action types
export const BL_ATTR_SET = 'BL_ATTR_SET';
export const BL_ATTR_GET_ALL = 'BL_ATTR_GET_ALL';
export const BL_ATTR_SET_STATE = 'BL_ATTR_SET_STATE';
export const BL_ATTR_MOV_SET_STATE = 'BL_ATTR_MOV_SET_STATE';
export const BL_ATTR_ACT_SET_STATE = 'BL_ATTR_ACT_SET_STATE';
export const BL_MACH_INFO = 'BL_MACH_INFO';
export const BL_ATTR_MOV_SET = 'BL_ATTR_MOV_SET';
export const BL_ATTR_ACT_SET = 'BL_ATTR_ACT_SET';

export function setBeamlineAttrAction(data) {
  return { type: BL_ATTR_SET, data };
}

export function getBeamlineAttrsAction(data) {
  return { type: BL_ATTR_GET_ALL, data };
}

export function setMachInfo(info) {
  return { type: BL_MACH_INFO, info };
}

export function busyStateAction(name) {
  return {
    type: BL_ATTR_SET_STATE,
    data: { name, state: STATE.BUSY }
  };
}

export function sendGetAllAttributes() {
  const url = 'mxcube/api/v0.1/beamline/';

  return (dispatch) => {
    fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      },
      credentials: 'include'
    }).then(response => response.json())
      .then((data) => {
        dispatch(getBeamlineAttrsAction(data));
      }, () => {
        throw new Error(`GET ${url} failed`);
      });
  };
}

export function setBeamlineAttribute(name, value) {
  return setBeamlineAttrAction({ name, value });
}

export function sendSetAttribute(name, value) {
  const url = `mxcube/api/v0.1/beamline/${name}`;

  return (dispatch) => {
    dispatch(busyStateAction(name));

    fetch(url, {
      method: 'PUT',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify({ name, value })
    });
  };
}


export function sendAbortCurrentAction(name) {
  return () => {
    fetch(`mxcube/api/v0.1/beamline/${name}/abort`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      },
      credentials: 'include'
    });
  };
}


export function sendPrepareForNewSample() {
  return () => {
    fetch('mxcube/api/v0.1/beamline/prepare_beamline', {
      method: 'PUT',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      }
    });
  };
}

import fetch from 'isomorphic-fetch';
import { showErrorPanel } from './general';
import { setCurrentSample, clearCurrentSample } from './queue';

export function setContents(contents) {
  return { type: 'SET_SC_CONTENTS', data: { sampleChangerContents: contents } };
}

export function setSCState(state) {
  return { type: 'SET_SC_STATE', state };
}

export function setLoadedSample(data) {
  return { type: 'SET_LOADED_SAMPLE', data };
}

export function setSCGlobalState(data) {
  return { type: 'SET_SC_GLOBAL_STATE', data };
}

export function updateSCContents(data) {
  return { type: 'UPDATE_SC_CONTENTS', data };
}

export function setSCCommandResponse(response) {
  return { type: 'SET_SC_RESPONSE', response };
}

export function refresh() {
  return function (dispatch) {
    fetch('mxcube/api/v0.1/sample_changer/contents', {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      },
      credentials: 'include'
    }).then(response => {
      if (response.status >= 400) {
        throw new Error('Error refreshing sample changer contents');
      }

      response.json().then(contents => { dispatch(setContents(contents)); });
    });

    fetch('mxcube/api/v0.1/sample_changer/loaded_sample', {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      },
      credentials: 'include'
    }).then(response => {
      if (response.status >= 400) {
        throw new Error('Error refreshing sample changer contents');
      }

      response.json().then(loadedSample => { dispatch(setLoadedSample(loadedSample)); });
    });
  };
}

export function select(address) {
  return function (dispatch) {
    fetch(`mxcube/api/v0.1/sample_changer/select/${address}`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      },
      credentials: 'include'
    }).then(response => {
      if (response.status >= 400) {
        throw new Error(`Error while selecting sample changer container @ ${address}`);
      }

      response.json().then(contents => { dispatch(setContents(contents)); });
    });
  };
}

export function scan(address) {
  return function (dispatch) {
    fetch(`mxcube/api/v0.1/sample_changer/scan/${address}`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      },
      credentials: 'include'
    }).then(response => {
      if (response.status >= 400) {
        throw new Error(`Error while scanning sample changer @ ${address}`);
      }

      response.json().then(contents => { dispatch(setContents(contents)); });
    });
  };
}

export function loadSample(sampleData, successCb = null) {
  return function (dispatch, getState) {
    const state = getState();

    if (state.sampleChanger.loadedSample.address !== sampleData.location) {
      fetch('mxcube/api/v0.1/sample_changer/mount', {
        method: 'POST',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          'Content-type': 'application/json'
        },
        body: JSON.stringify(sampleData)
      }).then((response) => {
        if (response.status >= 400) {
          dispatch(showErrorPanel(true, response.headers.get('message')));
          throw new Error('Server refused to mount sample');
        } else {
          setCurrentSample(sampleData.sampleID);

          response.json().then(contents => { dispatch(setContents(contents)); }
                              ).then(dispatch(refresh()));

          if (successCb) {
            successCb();
          }
        }
      });
    }
  };
}

export function unloadSample(location) {
  let url = '';

  if (location) {
    url = 'mxcube/api/v0.1/sample_changer/unmount';
  } else {
    url = 'mxcube/api/v0.1/sample_changer/unmount_current';
  }


  return function (dispatch) {
    fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      },
      body: JSON.stringify({ location, sampleID: location })
    }).then((response) => {
      if (response.status >= 400) {
        dispatch(showErrorPanel(true, response.headers.get('message')));
        throw new Error('Server refused to unmount sample');
      } else {
        dispatch(clearCurrentSample());
      }
    });
  };
}

export function abort() {
  return function (dispatch) {
    fetch('mxcube/api/v0.1/sample_changer/send_command/abort', {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      },
      credentials: 'include'
    }).then(response => {
      if (response.status < 400) {
        dispatch(showErrorPanel(true, 'action aborted'));
      }
    });
  };
}

export function sendCommand(cmdparts) {
  return function (dispatch) {
    fetch(`mxcube/api/v0.1/sample_changer/send_command/${cmdparts}`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'Content-type': 'application/json'
      },
      credentials: 'include'
    }).then(response => {
      if (response.status >= 400) {
        dispatch(showErrorPanel(true, response.headers.get('message')));
        throw new Error(`Error while  sending command @ ${cmdparts}`);
      }
      response.json().then(answer => { dispatch(setSCCommandResponse(answer)); });
    });
  };
}

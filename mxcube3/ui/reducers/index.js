import { combineReducers } from 'redux';
import { reducer as formReducer } from 'redux-form';
import login from './login';
import queue from './queue';
import queueGUI from './queueGUI';
import sampleGrid from './sampleGrid';
import sampleChanger from './sampleChanger';
import sampleChangerMaintenance from './sampleChangerMaintenance';
import taskForm from './taskForm';
import sampleview from './sampleview';
import general from './general';
import beamline from './beamline';
import logger from './logger';
import contextMenu from './contextMenu';
import remoteAccess from './remoteAccess';
import shapes from './shapes';
import workflow from './workflow';
import taskResult from './taskResult';
import uiproperties from './uiproperties';

const mxcubeReducer = combineReducers({
  login,
  queue,
  uiproperties,
  sampleGrid,
  sampleChanger,
  sampleChangerMaintenance,
  taskForm,
  sampleview,
  logger,
  general,
  beamline,
  remoteAccess,
  contextMenu,
  shapes,
  queueGUI,
  workflow,
  taskResult,
  form: formReducer
});

const rootReducer = (state, action) => {
  if (action.type === 'SIGNOUT') {
    state = undefined; // eslint-disable-line no-param-reassign
  }

  return mxcubeReducer(state, action);
};

export default rootReducer;

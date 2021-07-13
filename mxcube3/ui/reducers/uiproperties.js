import { findIndex, setWith, clone } from 'lodash';

const initialState = {
};

export default (state = initialState, action) => {
  switch (action.type) {
    case 'SET_UI_PROPERTIES':
    {
      return { ...state, ...action.data };
    }
    case 'SET_STEP_SIZE':
    {
      const idx = findIndex(
        state[action.componentName].components,
        (o) => o.attribute === action.name
      );

      return setWith(
        clone(state),
        `${action.componentName}.components[${idx}].step`,
        action.value,
        clone
      );

    }
    case 'SET_INITIAL_STATE':
    {
      return { ...state, ...action.data.uiproperties };
    }
    default:
      return state;
  }
};

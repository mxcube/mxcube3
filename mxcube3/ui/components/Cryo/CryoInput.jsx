import React from 'react';

import { OverlayTrigger, Popover } from 'react-bootstrap';
import { STATE } from '../../actions/beamline';

import DefaultInput from './DefaultInput';
import DefaultBusy from './DefaultBusy';
import './style.css';
import '../input.css';

export default class CryoInput extends React.Component {
  constructor(props) {
    super(props);
    this.save = this.save.bind(this);
    this.cancel = this.cancel.bind(this);
    this.submit = this.submit.bind(this);
  }


  componentWillReceiveProps(nextProps) {
    if (nextProps.data.state !== this.props.data.state) {
      if (this.isIdle(nextProps.data)) {
        this.handleIdle(nextProps.data);
      } else if (this.isAborted(nextProps.data)) {
        this.handleError(nextProps.data);
      } else {
        this.handleError(nextProps.data);
      }
    }
  }


  getChild(key) {
    let children = this.props.children;
    let child;

    // We need to create a real array here since react is so kind to give us
    // undefined if there is no children and an object if there is only one.
    if (this.props.children === undefined) {
      children = [];
    } else if (!Array.isArray(this.props.children)) {
      children = [this.props.children];
    }

    for (const c in children) {
      if (children[c].key === key) {
        child = children[c];
      }
    }

    return child;
  }


  setValue(value) {
    if (this.props.onSave !== undefined) {
      // Only update if value actually changed
      this.props.onSave(this.props.pkey, value);
    }
    if (this.props.data.state === 'IMMEDIATE') {
      this.refs.overlay.hide();
    }
  }


  handleIdle(data) {
    // No message to display to user, hide overlay
    if (data.msg === '') {
      this.refs.overlay.hide();
    }
  }


  handleError(data) {
    // No message to display to user, hide overlay
    if (data.msg === '') {
      this.refs.overlay.hide();
    }
  }


  save() {
    this.setValue(this.refs.input.getValue());
  }


  cancel() {
    if (this.props.onCancel !== undefined) {
      this.props.onCancel(this.props.pkey);
    }

    if (!this.isBusy()) {
      this.refs.overlay.hide();
    }
  }


  submit(event) {
    event.preventDefault();
    this.save();
  }


  inputComponent() {
    const props = { value: this.props.data.value,
      ref: 'input',
      onSubmit: this.submit,
      onCancel: this.cancel,
      onSave: this.save };

    let input = (<DefaultInput dataType={this.props.dataType} inputSize={this.props.inputSize} />);

    input = this.getChild('input') || input;
    input = React.cloneElement(input, props);

    return input;
  }


  busyComponent() {
    const props = { onCancel: this.cancel };
    let input = (<DefaultBusy />);

    input = this.getChild('busy') || input;
    input = React.cloneElement(input, props);

    return input;
  }


  isBusy(data) {
    const state = typeof data !== 'undefined' ? data.state : this.props.data.state;
    return state === STATE.BUSY;
  }


  isIdle(data) {
    const state = typeof data !== 'undefined' ? data.state : this.props.data.state;
    return state === STATE.IDLE;
  }


  isAborted(data) {
    const state = typeof data !== 'undefined' ? data.state : this.props.data.state;
    return state === STATE.ABORT;
  }


  render() {
    const linkClass = 'editable-click';
    const busyVisibility = this.isBusy() ? '' : 'hidden';
    const inputVisibility = !this.isBusy() ? '' : 'hidden';
    const title = (this.props.title === '') ? this.props.name : this.props.title;

    let stateClass = 'value-label-enter-success';

    if (this.isBusy()) {
      stateClass = 'input-bg-moving';
    } else if (this.isAborted()) {
      stateClass = 'input-bg-fault';
    }

    const popover = (
      <Popover id={title} title={title}>
        <div className={`${inputVisibility} popinput-form-container`}>
          {this.inputComponent()}
        </div>
        <div ref="statusMessage" className={inputVisibility} >{this.props.data.msg}</div>
        <div ref="loadingDiv" className={`${busyVisibility} popinput-input-loading`} >
          {this.busyComponent()}
        </div>
      </Popover>);

    return (
      <div className={`${this.props.className} popinput-input-container`}>
        <div className="row">
        <span className={`popinput-input-label ${this.props.ref}`}>
          {this.props.name}:
        </span>
        <span className={`popinput-input-value ${this.props.pkey}`}>
          <OverlayTrigger ref="overlay" trigger="click" rootClose placement={this.props.placement}
            overlay={popover}
          >
            <a ref="valueLabel" key="valueLabel" className={`${linkClass} ${stateClass}`}>
              {this.props.data.value} K
            </a>
          </OverlayTrigger>
        </span>
        </div>
      </div>
    );
  }
}


CryoInput.defaultProps = {
  className: '',
  dataType: 'number',
  inputSize: '100px',
  name: '',
  title: '',
  suffix: '',
  value: 0,
  placement: 'right',
  pkey: undefined,
  onSave: undefined,
  onCancel: undefined,
  data: { value: 0, state: 'ABORTED', msg: '' }
};

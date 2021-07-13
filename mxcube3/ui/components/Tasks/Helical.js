import React from 'react';
import { connect } from 'react-redux';
import { reduxForm, formValueSelector } from 'redux-form';
import {
  Modal, Button, Form, Row, Col, ButtonToolbar
} from 'react-bootstrap';
import { DraggableModal } from '../DraggableModal';
import validate from './validate';
import warn from './warning';

import {
  FieldsHeader,
  StaticField,
  InputField,
  CheckboxField,
  SelectField,
  FieldsRow,
  CollapsableRows
} from './fields';

class Helical extends React.Component {
  constructor(props) {
    super(props);

    this.submitAddToQueue = this.submitAddToQueue.bind(this);
    this.submitRunNow = this.submitRunNow.bind(this);
    this.addToQueue = this.addToQueue.bind(this);
    this.resetParameters = this.resetParameters.bind(this);
    this.defaultParameters = this.defaultParameters.bind(this);
  }

  submitAddToQueue() {
    this.props.handleSubmit(this.addToQueue.bind(this, false))();
  }

  submitRunNow() {
    this.props.handleSubmit(this.addToQueue.bind(this, true))();
  }

  addToQueue(runNow, params) {
    const parameters = {
      ...params,
      type: 'DataCollection',
      label: 'Helical',
      helical: true,
      mesh: false,
      shape: this.props.pointID,
    };

    // Form gives us all parameter values in strings so we need to transform numbers back
    const stringFields = [
      'shutterless',
      'inverse_beam',
      'centringMethod',
      'detector_mode',
      'space_group',
      'prefix',
      'subdir',
      'type',
      'label',
      'helical',
      'shape',
    ];

    this.props.addTask(parameters, stringFields, runNow);
    this.props.hide();
  }

  resetParameters() {
    this.props.reset();
  }

  defaultParameters() {
    this.props.resetTaskParameters();
    const { type } = this.props.taskData.parameters;
    const fieldNames = Object.keys(this.props.initialParameters[type.toLowerCase()]);
    fieldNames.forEach((field) => {
      this.props.autofill(field, this.props.initialParameters[type.toLowerCase()][field]);
    });
  }

  render() {
    return (
      <DraggableModal show={this.props.show} onHide={this.props.hide}>
        <Modal.Header closeButton>
          <Modal.Title>Helical Data Collection</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <FieldsHeader title="Data location" />
          <Form horizontal>
            <StaticField label="Path" data={this.props.path} />
            <Row>
              <Col xs={12}>
                <InputField propName="subdir" label="Subdirectory" col1="4" col2="8" />
              </Col>
            </Row>
            <Row>
              <Col xs={12}>
                <InputField propName="prefix" label="Prefix" col1="4" col2="6" />
              </Col>
              {this.props.taskData.sampleID
                ? (
                  <Col xs={4}>
                    <InputField
                      propName="run_number"
                      disabled
                      label="Run number"
                      col1="4"
                      col2="8"
                    />
                  </Col>
                )
                : null}
            </Row>
            <StaticField label="Filename" data={this.props.filename} />
          </Form>

          <FieldsHeader title="Acquisition" />
          <Form horizontal>
            <FieldsRow>
              <InputField propName="osc_range" type="number" label="Oscillation range" />
              <InputField propName="first_image" type="number" label="First image" />
            </FieldsRow>
            <FieldsRow>
              <InputField propName="osc_start" type="number" label="Oscillation start" />
              <InputField propName="num_images" type="number" label="Number of images" />
            </FieldsRow>
            <FieldsRow>
              <InputField propName="exp_time" type="number" label="Exposure time (s)" />
              <InputField propName="transmission" type="number" label="Transmission" />
            </FieldsRow>
            <FieldsRow>
              <InputField propName="energy" type="number" label="Energy" />
              <InputField propName="resolution" type="number" label="Resolution" />
            </FieldsRow>
            <CollapsableRows>
              <FieldsRow>
                <InputField propName="kappa" type="number" label="Kappa" />
                <InputField propName="kappa_phi" type="number" label="Phi" />
              </FieldsRow>
              <FieldsRow>
                <SelectField
                  propName="beam_size"
                  label="Beam size"
                  list={this.props.apertureList}
                />
                <SelectField
                  propName="detector_mode"
                  label="Detector mode"
                  list={['0', 'C18', 'C2']}
                />
              </FieldsRow>
              <FieldsRow>
                <CheckboxField propName="shutterless" label="Shutterless" />
                <CheckboxField propName="inverse_beam" label="Inverse beam" />
              </FieldsRow>
            </CollapsableRows>
          </Form>

          <FieldsHeader title="Processing" />
        </Modal.Body>
        { this.props.taskData.state ? ''
          : (
            <Modal.Footer>
              <ButtonToolbar className="pull-left">
                <Button
                  bsSize="xsmall"
                  bsStyle="default"
                  onClick={this.defaultParameters}
                >
                 Default Parameters
                </Button>
              </ButtonToolbar>
              <ButtonToolbar className="pull-right">
                <Button
                  bsStyle="success"
                  disabled={this.props.taskData.parameters.shape === -1 || this.props.invalid}
                  onClick={this.submitRunNow}
                >
                 Run Now
                </Button>
                <Button
                  bsStyle="primary"
                  disabled={this.props.invalid}
                  onClick={this.submitAddToQueue}
                >
                  {this.props.taskData.sampleID ? 'Change' : 'Add to Queue'}
                </Button>
              </ButtonToolbar>
            </Modal.Footer>
          )
       }
      </DraggableModal>
    );
  }
}

Helical = reduxForm({
  form: 'helical',
  validate,
  warn
})(Helical);

const selector = formValueSelector('helical');

Helical = connect((state) => {
  const subdir = selector(state, 'subdir');
  let fname = '';

  if (state.taskForm.sampleID) {
    fname = state.taskForm.taskData.parameters.fileName;
  } else {
    const prefix = selector(state, 'prefix');
    fname = `${prefix}_[RUN#]_[IMG#]`;
  }

  return {
    path: `${state.queue.rootPath}/${subdir}`,
    filename: fname,
    acqParametersLimits: state.taskForm.acqParametersLimits,
    beamline: state.beamline,
    initialValues: {
      ...state.taskForm.taskData.parameters,
      beam_size: state.sampleview.currentAperture,
      resolution: (state.taskForm.sampleIds.constructor !== Array
        ? state.taskForm.taskData.parameters.resolution
        : state.beamline.attributes.resolution.value),
      energy: (state.taskForm.sampleIds.constructor !== Array
        ? state.taskForm.taskData.parameters.energy
        : state.beamline.attributes.energy.value),
      transmission: (state.taskForm.sampleIds.constructor !== Array
        ? state.taskForm.taskData.parameters.transmission
        : state.beamline.attributes.transmission.value),
      osc_start: (state.taskForm.sampleIds.constructor !== Array
        ? state.taskForm.taskData.parameters.osc_start
        : state.beamline.attributes.omega.value)
    }
  };
})(Helical);

export default Helical;

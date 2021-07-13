import React from 'react';
import { connect } from 'react-redux';
import { reduxForm, formValueSelector } from 'redux-form';
import {
  Modal, Button, Form, Row, Col, ButtonToolbar, ControlLabel
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

import { SPACE_GROUPS } from '../../constants';

class Characterisation extends React.Component {
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
      type: 'Characterisation',
      label: 'Characterisation',
      shape: this.props.pointID,
      helical: false
    };

    const stringFields = [
      'centringMethod',
      'detector_mode',
      'account_rad_damage',
      'opt_sad',
      'space_group',
      'strategy_complexity',
      'prefix',
      'subdir',
      'type',
      'shape',
      'label',
      'helical',
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
          <Modal.Title>Characterisation</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form horizontal>
            <StaticField label="Path" data={this.props.path} />
            <StaticField label="Filename" data={this.props.filename} />
            <Row>
              <Col xs={12} style={{ marginTop: '10px' }}>
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
          </Form>
          <FieldsHeader title="Reference acquisition" />
          <Form horizontal>
            <FieldsRow>
              <SelectField propName="num_images" label="Number of images" list={[1, 2, 4]} />
              <InputField propName="transmission" type="number" label="Transmission" />
            </FieldsRow>
            <FieldsRow>
              <InputField propName="exp_time" type="number" label="Exposure time (s)" />
              <InputField propName="resolution" type="number" label="Resolution (Å)" />
            </FieldsRow>
            <FieldsRow>
              <InputField propName="osc_range" type="number" label="Oscillation range" />
              <InputField
                disabled={this.props.beamline.attributes.energy.readonly}
                propName="energy"
                type="number"
                label="Energy"
              />
            </FieldsRow>
            <FieldsRow>
              <InputField propName="osc_start" type="number" label="Oscillation start" />
            </FieldsRow>
            <CollapsableRows>
              <FieldsRow>
                <InputField propName="kappa" type="number" label="Kappa" />
                <InputField propName="kappa_phi" type="number" label="Phi" />
              </FieldsRow>
              <FieldsRow>
                <SelectField
                  propName="detector_mode"
                  label="Detector mode"
                  list={['0', 'C18', 'C12', 'C2']}
                />
                <InputField propName="overlap" label="Overlap" />
              </FieldsRow>
            </CollapsableRows>
          </Form>
          <FieldsHeader title="Characterisation" />
          <Form horizontal>
            <FieldsRow>
              <CheckboxField
                propName="account_rad_damage"
                label="Account for radiation damage"
              />
              <CheckboxField
                propName="opt_sad"
                label="Optimised SAD"
              />
            </FieldsRow>
            <SelectField
              col1="4"
              col2="3"
              propName="strategy_complexity"
              label="Strategy complexity"
              list={['SINGLE', 'FEW', 'MANY']}
            />
          </Form>
          <FieldsHeader title="Crystal" />
          <CollapsableRows>
            <Form horizontal>
              <SelectField
                col1="3"
                col2="3"
                propName="space_group"
                label="Space group"
                list={SPACE_GROUPS}
              />
              <ControlLabel>Vertical Crystal dimension:</ControlLabel>
              <FieldsRow>
                <InputField propName="min_crystal_vdim" label="Min" />
                <InputField propName="min_crystal_vphi" label="&omega; at min" />
              </FieldsRow>
              <FieldsRow>
                <InputField propName="max_crystal_vdim" label="Max" />
                <InputField propName="max_crystal_vphi" label="&omega; at max" />
              </FieldsRow>
            </Form>
          </CollapsableRows>
          <FieldsHeader title="Radiation damage model" />
          <CollapsableRows>
            <Form horizontal>
              <FieldsRow>
                <InputField col1="6" col2="5" propName="beta" label="&beta; Å / Mgy" />
                <InputField col1="5" col2="5" propName="gamma" label="&gamma; 1/Mgy" />
                <InputField col1="6" col2="5" propName="rad_suscept" label="Sensetivity" />
              </FieldsRow>
            </Form>
          </CollapsableRows>
          <FieldsHeader title="Optimization parameters" />
          <CollapsableRows>
            <Form horizontal>
              <FieldsRow>
                <InputField
                  col1="6"
                  col2="5"
                  propName="aimed_i_sigma"
                  label="Aimed I/&sigma; at highest resolution"
                />
                <InputField
                  col1="5"
                  col2="5"
                  propName="aimed_completness"
                  label="Aimed completness"
                />
              </FieldsRow>
              <Row>
                <Col xs="8">
                  <CheckboxField
                    propName="use_permitted_rotation"
                    label="Use permitted rotaion range"
                  />
                </Col>
              </Row>
              <FieldsRow>
                <InputField
                  disabled={!this.props.use_permitted_rotation}
                  col1="6"
                  col2="5"
                  propName="permitted_phi_start"
                  label="&omega; start"
                />
                <InputField
                  disabled={!this.props.use_permitted_rotation}
                  col1="5"
                  col2="5"
                  propName="permitted_phi_end"
                  label="&omega; end"
                />
              </FieldsRow>
              <FieldsRow>
                <CheckboxField
                  propName="use_aimed_resolution"
                  label="Maximum resolution"
                />
              </FieldsRow>
              <FieldsRow>
                <CheckboxField
                  propName="use_aimed_multiplicity"
                  label="Aimed Multiplicity"
                />
              </FieldsRow>
              <Row>
                <Col xs="8">
                  <CheckboxField
                    propName="low_res_pass_strat"
                    label="Calculate low resolution pass strategy"
                  />
                </Col>
              </Row>
            </Form>
          </CollapsableRows>
          <FieldsHeader title="Routine DC" />
          <CollapsableRows>
            <Form horizontal>
              <FieldsRow>
                <CheckboxField
                  propName="use_min_dose"
                  disabled={this.props.use_min_time}
                  label="Use min dose"
                />
                <InputField
                  disabled={this.props.use_min_time}
                  col1="6"
                  col2="4"
                  propName="min_dose"
                  label="Dose limit MGy"
                />
              </FieldsRow>
              <FieldsRow>
                <CheckboxField
                  propName="use_min_time"
                  disabled={this.props.use_min_dose}
                  label="Use min time"
                />
                <InputField
                  disabled={this.props.use_min_dose}
                  col1="6"
                  col2="4"
                  propName="min_time"
                  label="Total limit (s)"
                />
              </FieldsRow>
            </Form>
          </CollapsableRows>
          <FieldsHeader title="SAD" />
          <CollapsableRows>
            <Form horizontal>
              <Row>
                <Col xs="10">
                  <CheckboxField
                    propName="auto_res"
                    disabled={this.props.opt_sad}
                    label="Resolution selected automatically, rotation interval 360 &deg;"
                  />
                </Col>
              </Row>
              <Row>
                <Col xs="10">
                  <CheckboxField
                    propName="opt_sad"
                    disabled={this.props.auto_res}
                    label="Optimal SAD for given resolution"
                  />
                </Col>
              </Row>
              <Row>
                <Col xs="8">
                  <InputField
                    disabled={!this.props.opt_sad}
                    col1="4"
                    col2="3"
                    propName="sad_res"
                    label="Resolution"
                  />
                </Col>
              </Row>
            </Form>
          </CollapsableRows>
          <FieldsHeader title="Radiation Damage" />
          <CollapsableRows>
            <Form horizontal>
              <Row>
                <Col xs="10">
                  <CheckboxField
                    propName="determine_rad_params"
                    label="Determine radiation damage parameters"
                  />
                </Col>
              </Row>
              <InputField
                col1="6"
                col2="2"
                propName="burn_osc_start"
                label="Oscillation start for burn strategy"
              />
              <InputField
                col1="6"
                col2="2"
                propName="burn_osc_interval"
                label="Oscillation interval for burn"
              />
            </Form>
          </CollapsableRows>
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

Characterisation = reduxForm({
  form: 'characterisation',
  validate,
  warn
})(Characterisation);

const selector = formValueSelector('characterisation');

Characterisation = connect((state) => {
  const subdir = selector(state, 'subdir');
  let position = state.taskForm.pointID === '' ? 'PX' : state.taskForm.pointID;
  if (typeof position === 'object') {
    const vals = Object.values(position).sort();
    position = `[${vals}]`;
  }

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
    use_permitted_rotation: selector(state, 'use_permitted_rotation'),
    use_aimed_resolution: selector(state, 'use_aimed_resolution'),
    use_aimed_multiplicity: selector(state, 'use_aimed_multiplicity'),
    auto_res: selector(state, 'auto_res'),
    opt_sad: selector(state, 'opt_sad'),
    use_min_dose: selector(state, 'use_min_dose'),
    use_min_time: selector(state, 'use_min_time'),
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
})(Characterisation);

export default Characterisation;

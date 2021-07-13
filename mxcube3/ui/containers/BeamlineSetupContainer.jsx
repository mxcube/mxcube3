import React from 'react';
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';
import { Row, Col, Table, Popover } from 'react-bootstrap';
import PopInput from '../components/PopInput/PopInput';
import BeamlineActions from './BeamlineActionsContainer';
import InOutSwitch from '../components/InOutSwitch/InOutSwitch';
import SampleChangerSwitch from '../components/SampleChangerSwitch/SampleChangerSwitch';
import DeviceState from '../components/DeviceState/DeviceState';
import LabeledValue from '../components/LabeledValue/LabeledValue';
import MachInfo from '../components/MachInfo/MachInfo';
import OneAxisTranslationControl from '../components/MotorInput/OneAxisTranslationControl';
import * as SampleViewActions from '../actions/sampleview';

import { find, filter } from 'lodash';

import {
  sendGetAllAttributes,
  sendSetAttribute,
  sendAbortCurrentAction
} from '../actions/beamline';

import { sendCommand } from '../actions/sampleChanger';

class BeamlineSetupContainer extends React.Component {
  constructor(props) {
    super(props);
    this.onSaveHandler = this.onSaveHandler.bind(this);
    this.setAttribute = this.setAttribute.bind(this);
    this.onCancelHandler = this.onCancelHandler.bind(this);
    this.createActuatorComponent = this.createActuatorComponent.bind(this);
    this.dmState = this.dmState.bind(this);
  }

  // componentDidMount() {
  // this.props.getAllAttributes();
  // }


  onSaveHandler(name, value) {
    this.props.setAttribute(name, value);
  }


  onCancelHandler(name) {
    this.props.abortCurrentAction(name);
  }


  setAttribute(name, value) {
    this.props.setAttribute(name, value);
  }

  beamstopAlignmentOverlay() {
    const attributes = this.props.beamline.attributes;
    const motorInputList = [];
    let popover = null;

    const motor = attributes.beamstop_alignemnt_x;
    const step = this.props.sampleview.motorSteps.beamstop_distance;

    if (motor !== undefined && motor.state !== 0) {
      motorInputList.push((
        <div style={{ marginBottom: '1em' }}>
          <p className="motor-name">Beamstop distance:</p>
          <OneAxisTranslationControl
            save={this.props.sampleViewActions.sendMotorPosition}
            value={motor.position}
            min={motor.limits[0]} max={motor.limits[1]}
            step={step}
            motorName={motor.name}
            suffix="mm"
            decimalPoints="3"
            state={motor.state}
            disabled={this.props.beamline.motorInputDisable}
          />
        </div>
      ));
    }

    if (motorInputList.length > 0) {
      popover = (<Popover>{motorInputList}</Popover>);
    }

    return popover;
  }


  createActuatorComponent() {
    const acts = [];

    const uiproperties = this.props.uiproperties;
    if (uiproperties.hasOwnProperty('beamline_setup')) {
      const blsetup_properties = uiproperties.beamline_setup.components;

      for (const key in this.props.beamline.attributes) {
        if (this.props.beamline.attributes[key] !== undefined) {
          const uiprop = find(blsetup_properties, { attribute: key });

          if (uiprop !== undefined) {
            if (uiprop.value_type === 'NSTATE') {
              if (uiprop.label === 'Beamstop') {
                acts.push(
                <Col key={key} className="pull-right">
                    <InOutSwitch
                      onText={ this.props.beamline.attributes[key].commands[0] }
                      offText={ this.props.beamline.attributes[key].commands[1] }
                      labelText={ uiprop.label }
                      pkey={ key }
                      data={ this.props.beamline.attributes[key] }
                      onSave={ this.setAttribute }
                      optionsOverlay={ this.beamstopAlignmentOverlay() }
                    />
                  </Col>
                );
              } else {
                acts.push(
                  <Col key={key} className="pull-right">
                    <InOutSwitch
                      onText={ this.props.beamline.attributes[key].commands[0] }
                      offText={ this.props.beamline.attributes[key].commands[1] }
                      labelText={ uiprop.label }
                      pkey={ key }
                      data={ this.props.beamline.attributes[key] }
                      onSave={ this.setAttribute }
                    />
                  </Col>
                );
              }
            }
          }
        }
      }
    }
    return acts;
  }


  dmState() {
    return this.props.beamline.attributes.diffractometer.state;
  }

  render_table_row(uiprop_list) {
    const components = [];

    for (const uiprop of uiprop_list) {
      const beamline_attribute = this.props.beamline.attributes[uiprop.attribute];

      components.push(
        <td style={{ paddingLeft: '0.5em' }}>
          { uiprop.label }:
        </td>);
      components.push(
        <td style={{ fontWeight: 'bold', borderRight: '1px solid #ddd', paddingRight: '0.5em' }}>
          { beamline_attribute.readonly ?
            (<LabeledValue
              suffix={ uiprop.suffix }
              precision={ uiprop.precision }
              format={ uiprop.format || '' }
              name=""
              value={beamline_attribute.value}
            />)
            :
            (<PopInput
              name=""
              pkey= {uiprop.attribute}
              suffix={uiprop.suffix }
              precision={ uiprop.precision }
              data={ beamline_attribute }
              onSave= { this.setAttribute }
              onCancel= { this.onCancelHandler }
            />)
          }
        </td>
      );
    }

    return components;
  }

  render() {
    // const blsetup_properties = uiproperties.beamline_setup.components;

    const uiproperties = this.props.uiproperties;

    if (!uiproperties.hasOwnProperty('beamline_setup')) {
      return null;
    }

    const uiprops = this.props.uiproperties.beamline_setup.components;
    const uiprop_list = filter(uiprops, { value_type: 'FLOAT' });

    return (
      <Row style={{
        paddingTop: '0.5em',
        paddingBottom: '0.5em',
        background: '#FAFAFA',
        borderBottom: '1px solid rgb(180,180,180)' }}
      >
        <Col sm={12}>
          <Row style={{ display: 'flex', alignItems: 'center' }}>
            <Col sm={1}>
              <BeamlineActions actionsList={this.props.beamline.beamlineActionsList} />
            </Col>
            <Col sm={5} smPush={1}>
              <Table
                condensed
                style={{ margin: '0px', fontWeight: 'bold',
                  paddingLeft: '7em', paddingRight: '7em' }}
              >
              <tr>
                {this.render_table_row(uiprop_list.slice(0, 4))}
              </tr>
              <tr>
                {this.render_table_row(uiprop_list.slice(4))}
                <td style={{ borderLeft: '1px solid #ddd', paddingLeft: '1em' }}>
                </td>
                <td>
                </td>
              </tr>
            </Table>
            </Col>
            <Col className="device-status-container" sm={5} smPush={1}>
              <Col className="pull-right">
                { this.props.beamline.attributes.machine_info ?
                  <MachInfo
                    info={this.props.beamline.attributes.machine_info.value}
                  />
                  :
                  null
                }
              </Col>
              {this.createActuatorComponent()}
              <Col className="pull-right">
                <SampleChangerSwitch
                  labelText={ 'Sample Changer' }
                  data = { this.props.sampleChanger.state }
                  onSave={ this.props.sendCommand }
                />
              </Col>
              { this.props.beamline.attributes.detector ?
                <Col className="pull-right">
                  <DeviceState
                    labelText={ 'Detector' }
                    data = { this.props.beamline.attributes.detector.state.acq_satus }
                  />
                </Col> : null
              }
            </Col>
          </Row>
        </Col>
      </Row>
    );
  }
}


function mapStateToProps(state) {
  return {
    uiproperties: state.uiproperties,
    beamline: state.beamline,
    sampleview: state.sampleview,
    sampleChanger: state.sampleChanger
  };
}


function mapDispatchToProps(dispatch) {
  return {
    getAllAttributes: bindActionCreators(sendGetAllAttributes, dispatch),
    sampleViewActions: bindActionCreators(SampleViewActions, dispatch),
    setAttribute: bindActionCreators(sendSetAttribute, dispatch),
    sendCommand: bindActionCreators(sendCommand, dispatch),
    abortCurrentAction: bindActionCreators(sendAbortCurrentAction, dispatch)
  };
}


export default connect(
  mapStateToProps,
  mapDispatchToProps
)(BeamlineSetupContainer);

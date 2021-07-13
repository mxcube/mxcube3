import './SampleView.css';
import React from 'react';
import {
  OverlayTrigger, Button, DropdownButton, MenuItem
} from 'react-bootstrap';
import 'fabric';

// config exported by webpack at buildtime
// eslint-disable-next-line import/no-unresolved
import config from 'guiConfig';
import OneAxisTranslationControl from '../MotorInput/OneAxisTranslationControl';
import { MOTOR_STATE } from '../../constants';

import { find } from 'lodash';

const { fabric } = window;

export default class SampleControls extends React.Component {
  constructor(props) {
    super(props);

    this.takeSnapShot = this.takeSnapShot.bind(this);
    this.doTakeSnapshot = this.doTakeSnapshot.bind(this);
    this.setZoom = this.setZoom.bind(this);
    this.toggleFrontLight = this.toggleLight.bind(this, 'frontlight');
    this.toggleBackLight = this.toggleLight.bind(this, 'backlight');
    this.toggleCentring = this.toggleCentring.bind(this);
    this.toggleDrawGrid = this.toggleDrawGrid.bind(this);
    this.availableVideoSizes = this.availableVideoSizes.bind(this);
  }

  componentDidMount() {
    window.takeSnapshot = this.doTakeSnapshot;
  }

  setZoom(option) {
    const newZoom = parseInt(option.target.value, 10);
    this.props.setBeamlineAttribute('zoom', option.target.value);

    if (this.props.attributes.zoom.value !== newZoom) {
      this.props.sendSetAttribute('zoom', newZoom);
    }
  }

  toggleDrawGrid() {
    // Cancel click centering before draw grid is started
    if (this.props.current.sampleID === '') {
      this.props.generalActions.showErrorPanel(true, 'There is no sample mounted');
    } else {
      if (this.props.clickCentring) {
        this.props.sampleActions.sendAbortCentring();
      }

      this.props.sampleActions.toggleDrawGrid();
    }
  }

  doTakeSnapshot() {
    const img = document.getElementById('sample-img');
    const fimg = new fabric.Image(img);
    fimg.scale(this.props.imageRatio);
    let imgDataURI = '';
    this.props.canvas.setBackgroundImage(fimg);
    this.props.canvas.renderAll();
    imgDataURI = this.props.canvas.toDataURL({ format: 'jpeg' });
    this.props.canvas.setBackgroundImage(0);
    this.props.canvas.renderAll();
    return { data: imgDataURI.slice(23), mime: imgDataURI.slice(0, 23) };
  }

  takeSnapShot() {
    const img = this.doTakeSnapshot();
    document.getElementById('downloadLink').href = img.mime + img.data;
    const { sampleName } = this.props.sampleList[this.props.current.sampleID];
    const filename = `${this.props.proposal}-${sampleName}.jpeg`;
    document.getElementById('downloadLink').download = filename;
  }

  toggleCentring() {
    const { sendStartClickCentring, sendAbortCentring } = this.props.sampleActions;
    const { clickCentring } = this.props;

    // If draw grid tool enabled, disable it before starting centering
    if (this.props.drawGrid) {
      this.props.sampleActions.toggleDrawGrid();
    }

    if (clickCentring) {
      sendAbortCentring();
    } else {
      sendStartClickCentring();
    }
  }

  toggleLight(name) {
    const lighstate = this.props.attributes[`${name}_switch`].value;
    const newState = this.props.attributes[`${name}_switch`].
      commands.filter(state => state !== lighstate)[0];
    this.props.sendSetAttribute(`${name}_switch`, newState);
  }


  availableVideoSizes() {
    const items = this.props.videoSizes.map((size) => {
      const sizeGClass = this.props.width === String(size[0]) ? 'fa-dot-circle-o' : 'fa-circle-o';

      return (
        <MenuItem
          key={`${size[0]} x ${size[1]}`}
          eventKey="1"
          onClick={() => this.props.sampleActions.setVideoSize(size[0], size[1])}
        >
          <span className={`fa ${sizeGClass}`} />
          {' '}
          {`${size[0]} x ${size[1]}`}
        </MenuItem>
      );
    });

    const autoScaleGClass = this.props.autoScale ? ' fa-check-square-o' : 'fa-square-o';

    items.push((
      <MenuItem
        eventKey="3"
        key="auto scale"
        onClick={() => {
          const { clientWidth } = document.getElementById('outsideWrapper');
          this.props.sampleActions.toggleAutoScale(clientWidth);
        }}
      >
        <span className={`fa ${autoScaleGClass}`} />
        {' '}
Auto Scale
      </MenuItem>));

    items.push((
      <MenuItem
        eventKey="3"
        key="reset"
        onClick={() => {
          window.initJSMpeg();
          this.props.sampleActions.setVideoSize(this.props.width, this.props.height);
        }}
      >
        <span className="fa fa-redo" />
        {' '}
Reset
      </MenuItem>));

    return items;
  }

  render() {
    const { attributes } = this.props;

    const foucs_motor_uiprop = find(
      this.props.uiproperties.components, { role: 'focus' }
    );

    const foucs_motor = this.props.attributes[foucs_motor_uiprop.attribute];

    return (
      <div style={{ display: 'flex', position: 'absolute', width: '100%' }}>
        <div className="sample-controlls text-center">
          <ul className="bs-glyphicons-list">
            <li>
              <a
                style={{ marginTop: '0.3em' }}
                href="#"
                id="downloadLink"
                data-toggle="tooltip"
                title="Take snapshot"
                className="fa fa-camera sample-controll"
                onClick={this.takeSnapShot}
                download
              />
              <span className="sample-controll-label">Snapshot</span>
            </li>
            <li>
              <Button
                type="button"
                data-toggle="tooltip"
                title="Draw grid"
                className="fa fa-th sample-controll"
                onClick={this.toggleDrawGrid}
                active={this.props.drawGrid}
              />
              <span className="sample-controll-label">Draw grid</span>
            </li>
            <li>
              <Button
                type="button"
                data-toggle="tooltip"
                title="Start 3-click Centring"
                className="fa fa-circle-o-notch sample-controll"
                onClick={this.toggleCentring}
                active={this.props.clickCentring}
              />
              <span className="sample-controll-label">3-click Centring</span>
            </li>
            {config.focusControlOnCanvas
              ? (
                <li>
                  <OverlayTrigger
                    trigger="click"
                    rootClose
                    placement="bottom"
                    overlay={(
                      <span className="slider-overlay" style={{ marginTop: '20px' }}>
                        <OneAxisTranslationControl
                          save={this.props.sendSetAttribute}
                          value={foucs_motor.value}
                          min={foucs_motor.limits[0]}
                          max={foucs_motor.limits[1]}
                          step={this.props.steps.focusStep}
                          motorName={foucs_motor_uiprop.attribute}
                          suffix={foucs_motor_uiprop.suffix}
                          decimalPoints={foucs_motor_uiprop.precision}
                          state={foucs_motor.state}
                          disabled={this.props.motorsDisabled}
                        />
                      </span>
                    )}
                  >
                    <Button
                      name="focus"
                      type="button"
                      data-toggle="tooltip"
                      title="Focus"
                      className="fa fa-adjust sample-controll"
                    />
                  </OverlayTrigger>
                  <span className="sample-controll-label">Focus</span>
                </li>
              ) : null}
            <OverlayTrigger
              trigger="click"
              rootClose
              placement="bottom"
              overlay={(
                <span className="slider-overlay">
                  {attributes.zoom.limits[0]}
                  <input
                    style={{ top: '20px' }}
                    className="bar"
                    type="range"
                    id="zoom-control"
                    min={attributes.zoom.limits[0]}
                    max={attributes.zoom.limits[1]}
                    step="1"
                    value={attributes.zoom.value}
                    disabled={attributes.zoom.state !== MOTOR_STATE.READY}
                    onMouseUp={this.setZoom}
                    onChange={e => this.props.setBeamlineAttribute('zoom', e.target.value)}
                    list="volsettings"
                    name="zoomSlider"
                  />
                  {attributes.zoom.limits[1]}
                </span>
)}
            >
              <li>
                <Button
                  type="button"
                  data-toggle="tooltip"
                  title="Zoom in/out"
                  className="fa fa-search sample-controll"
                  name="zoomOut"
                />
                <datalist id="volsettings">
                  {[...Array(attributes.zoom.limits[1] - attributes.zoom.limits[0]).keys()].map(i =>
                    (<option>{attributes.zoom.limits[0] + i }</option>)
                  )}
                </datalist>
                <span className="sample-controll-label">Zoom</span>
              </li>
            </OverlayTrigger>
            <li>
              <Button
                style={{ paddingRight: '0px' }}
                type="button"
                data-toggle="tooltip"
                title="Backlight On/Off"
                className="fa fa-lightbulb-o sample-controll"
                onClick={this.toggleBackLight}
                active= {
                  attributes.backlight_switch.value === attributes.backlight_switch.commands[0]
                }
              />
              <OverlayTrigger
                trigger="click"
                rootClose
                placement="bottom"
                overlay={(
                  <span className="slider-overlay" style={{ marginTop: '20px' }}>
                    <input
                      style={{ top: '20px' }}
                      className="bar"
                      type="range"
                      step="0.1"
                      min={attributes.backlight.limits[0]}
                      max={attributes.backlight.limits[1]}
                      value={attributes.backlight.value}
                      disabled={attributes.backlight.state !== MOTOR_STATE.READY}
                      onMouseUp={e => this.props.sendSetAttribute('backlight', e.target.value)}
                      onChange={e => this.props.setBeamlineAttribute('backlight', e.target.value)}
                      name="backlightSlider"
                    />
                  </span>
)}
              >
                <Button
                  type="button"
                  style={{ paddingLeft: '0px' }}
                  className="fa fa-sort-desc sample-controll sample-controll-small"
                />
              </OverlayTrigger>
              <span className="sample-controll-label">Backlight</span>
            </li>
            <li>
              <Button
                style={{ paddingRight: '0px' }}
                type="button"
                data-toggle="tooltip"
                title="Front On/Off"
                className="fa fa-lightbulb-o sample-controll"
                onClick={this.toggleFrontLight}
                active={
                  attributes.frontlight_switch.value === attributes.backlight_switch.commands[0]
                }
              />
              <OverlayTrigger
                trigger="click"
                rootClose
                placement="bottom"
                overlay={(
                  <span className="slider-overlay" style={{ marginTop: '20px' }}>
                    <input
                      className="bar"
                      type="range"
                      step="0.1"
                      min={attributes.frontlight.limits[0]}
                      max={attributes.frontlight.limits[1]}
                      value={attributes.frontlight.value}
                      disabled={attributes.frontlight.state !== MOTOR_STATE.READY}
                      onMouseUp={e => this.props.sendSetAttribute('frontlight', e.target.value)}
                      onChange={e => this.props.setBeamlineAttribute('frontlight', e.target.value)}
                      name="frontLightSlider"
                    />
                  </span>
)}
              >
                <Button
                  type="button"
                  style={{ paddingLeft: '0px', fontSize: '1.5em' }}
                  className="fa fa-sort-desc sample-controll sample-controll-small"
                />
              </OverlayTrigger>
              <span className="sample-controll-label">Frontlight</span>
            </li>
            <li>
              <DropdownButton
                style={{ lineHeight: '1.3', padding: '0px' }}
                className="sample-controll"
                bsStyle="default"
                title={(<i className="fa fa-1x fa-video-camera" />)}
                id="video-size-dropdown"
              >
                {this.availableVideoSizes()}
              </DropdownButton>
              <span className="sample-controll-label">Video size</span>
            </li>
          </ul>
        </div>
      </div>
    );
  }
}

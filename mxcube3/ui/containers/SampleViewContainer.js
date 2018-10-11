import React, { Component } from 'react';
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';
import SampleImage from '../components/SampleView/SampleImage';
import MotorControl from '../components/SampleView/MotorControl';
import PhaseInput from '../components/SampleView/PhaseInput';
import ApertureInput from '../components/SampleView/ApertureInput';
import ContextMenu from '../components/SampleView/ContextMenu';
import * as SampleViewActions from '../actions/sampleview';
import * as BeamlineActions from '../actions/beamline';
import { updateTask } from '../actions/queue';
import { showTaskForm } from '../actions/taskForm';
import BeamlineSetupContainer from './BeamlineSetupContainer';
import SampleQueueContainer from './SampleQueueContainer';
import { QUEUE_RUNNING } from '../constants';
import config from 'guiConfig';


class SampleViewContainer extends Component {

  render() {
    const { sourceScale, imageRatio, motorSteps } = this.props.sampleViewState;
    const { setStepSize } = this.props.sampleViewActions;
    const { sendMovablePosition, sendStopMovable } = this.props.beamlineActions;
    const sampleID = this.props.current.sampleID;
    const [points, lines, grids, twoDPoints] = [{}, {}, {}, {}];
    const selectedGrids = [];

    Object.keys(this.props.shapes).forEach((key) => {
      const shape = this.props.shapes[key];
      if (shape.t === 'P') {
        points[shape.id] = shape;
      } else if (shape.t === '2DP') {
        twoDPoints[shape.id] = shape;
      } else if (shape.t === 'L') {
        lines[shape.id] = shape;
      } else if (shape.t === 'G') {
        grids[shape.id] = shape;

        if (shape.selected) {
          selectedGrids.push(shape);
        }
      }
    });
    const phaseControl = (
      <div>
      <p className="motor-name">Phase Control:</p>
      <PhaseInput
        phase={this.props.sampleViewState.currentPhase}
        phaseList={this.props.sampleViewState.phaseList}
        sendPhase={this.props.sampleViewActions.sendCurrentPhase}
      />
      </div>);

    const apertureControl = (
      <div>
      <p className="motor-name">Beam size:</p>
      <ApertureInput
        aperture={this.props.sampleViewState.currentAperture}
        apertureList={this.props.sampleViewState.apertureList}
        sendAperture={this.props.sampleViewActions.sendChangeAperture}
      />
      </div>);

    return (
        <div className="row">
        <div className="col-xs-12">
            <div className="row">
              <div className="col-xs-12" style={{ marginTop: '-10px' }}>
                <BeamlineSetupContainer />
              </div>
            </div>
            <div className="row" style={ { display: 'flex', marginTop: '1em' } }>
              <div className="col-xs-1"
                style={ { paddingRight: '5px', paddingLeft: '1.5em' } }
              >
                {config.phaseControl ? phaseControl : null }
                {apertureControl}
                <MotorControl
                  save={sendMovablePosition}
                  saveStep={setStepSize}
                  movables={this.props.movables}
                  movablesDisabled={ this.props.motorInputDisable ||
                                   this.props.queueState === QUEUE_RUNNING }
                  steps={motorSteps}
                  stop={sendStopMovable}
                />
              </div>
              <div className="col-xs-7">
                <ContextMenu
                  {...this.props.contextMenu}
                  sampleActions={this.props.sampleViewActions}
                  updateTask={this.props.updateTask}
                  availableMethods={this.props.availableMethods}
                  showForm={this.props.showForm}
                  sampleID={sampleID}
                  sampleData={this.props.sampleList[sampleID]}
                  defaultParameters={this.props.defaultParameters}
                  imageRatio={imageRatio * sourceScale}
                  workflows={this.props.workflows}
                  savedPointId={this.props.sampleViewState.savedPointId}
                  groupFolder={this.props.groupFolder}
                  clickCentring={this.props.sampleViewState.clickCentring}
                />
                <SampleImage
                  sampleActions={this.props.sampleViewActions}
                  beamlineActions={this.props.beamlineActions}
                  {...this.props.sampleViewState}
                  movables={this.props.movables}
                  steps={motorSteps}
                  imageRatio={imageRatio * sourceScale}
                  contextMenuVisible={this.props.contextMenu.show}
                  shapes={this.props.shapes}
                  points={points}
                  twoDPoints={twoDPoints}
                  lines={lines}
                  grids={grids}
                  selectedGrids={selectedGrids}
                  cellCounting={this.props.cellCounting}
                  cellSpacing={this.props.cellSpacing}
                  current={this.props.current}
                  sampleList={this.props.sampleList}
                  proposal={this.props.proposal}
                  busy={this.props.queueState === QUEUE_RUNNING}
                />
              </div>
              <div className="col-xs-4" style={ { display: 'flex' } }>
                <SampleQueueContainer />
            </div>
            </div>
        </div>
      </div>
    );
  }
}


function mapStateToProps(state) {
  return {
    sampleList: state.sampleGrid.sampleList,
    current: state.queue.current,
    groupFolder: state.queue.groupFolder,
    queueState: state.queue.queueStatus,
    sampleViewState: state.sampleview,
    contextMenu: state.contextMenu,
    motorInputDisable: state.beamline.motorInputDisable,
    movables: state.beamline.movables,
    availableMethods: state.beamline.availableMethods,
    defaultParameters: state.taskForm.defaultParameters,
    shapes: state.shapes.shapes,
    workflows: state.workflow.workflows,
    cellCounting: state.taskForm.defaultParameters.mesh.cell_counting,
    cellSpacing: state.taskForm.defaultParameters.mesh.cell_spacing,
    proposal: state.login.selectedProposal,
    remoteAccess: state.remoteAccess
  };
}

function mapDispatchToProps(dispatch) {
  return {
    sampleViewActions: bindActionCreators(SampleViewActions, dispatch),
    beamlineActions: bindActionCreators(BeamlineActions, dispatch),
    updateTask: bindActionCreators(updateTask, dispatch),
    showForm: bindActionCreators(showTaskForm, dispatch)
  };
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(SampleViewContainer);

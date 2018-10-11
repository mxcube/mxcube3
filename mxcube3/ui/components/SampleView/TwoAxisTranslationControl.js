import React from 'react';
import { Button, OverlayTrigger, Popover } from 'react-bootstrap';
import MotorInput from './MotorInput';
import './motor.css';

export default class TwoAxisTranslationControl extends React.Component {

  constructor(props) {
    super(props);
    this.stepChange = this.stepChange.bind(this);
  }

  stepChange(name, step, operator) {
    const value = this.props.movables[name].value;
    const newValue = value + step * operator;
    this.props.save(name, newValue);
  }

  renderMotorSettings() {
    return (<Popover title={(<b>Sample alignment movables</b>)}>
              <div>
                <MotorInput
                  save={this.props.save}
                  value={this.props.movables.sample_vertical.value}
                  saveStep={this.props.saveStep}
                  step={this.props.steps.sample_verticalStep}
                  motorName="sample_vertical"
                  label="Vertical"
                  suffix="mm"
                  decimalPoints="3"
                  state={this.props.movables.sample_vertical.state}
                  stop={this.props.stop}
                  disabled={this.props.movablesDisabled}
                  inplace
                />
                <MotorInput
                  save={this.props.save}
                  value={this.props.movables.sample_horizontal.value}
                  saveStep={this.props.saveStep}
                  step={this.props.steps.sample_horizontalStep}
                  motorName="sample_horizontal"
                  label="Horizontal"
                  suffix="mm"
                  decimalPoints="3"
                  state={this.props.movables.sample_horizontal.state}
                  stop={this.props.stop}
                  disabled={this.props.movablesDisabled}
                  inplace
                />
              </div>
            </Popover>);
  }

  render() {
    const {
      sample_verticalStep,
      sample_horizontalStep
    } = this.props.steps;

    return (
      <div className="arrow-control">
        <p className="motor-name">Sample alignment:</p>
        <div style={{ marginBottom: '1em' }}></div>
        <Button
          onClick={() => this.stepChange('sample_vertical', sample_verticalStep, 1)}
          disabled={this.props.movables.sample_vertical.state !== 2 ||
                    this.props.movablesDisabled}
          className="arrow arrow-up"
        >
          <i className="fa fa-angle-up" />
        </Button>
        <Button
          className="arrow arrow-left"
          disabled={this.props.movables.sample_horizontal.state !== 2 ||
                    this.props.movablesDisabled}
          onClick={() => this.stepChange('sample_horizontal', sample_horizontalStep, -1)}
        >
          <i className="fa fa-angle-left" />
        </Button>
        <OverlayTrigger trigger="click" rootClose placement="right"
          overlay={this.renderMotorSettings()}
        >
          <Button
            className="arrow arrow-settings"
          >
            <i className="fa fa-cog" />
          </Button>
        </OverlayTrigger>
        <Button
          className="arrow arrow-right"
          disabled={this.props.movables.sample_horizontal.state !== 2 ||
                    this.props.movablesDisabled}
          onClick={() => this.stepChange('sample_horizontal', sample_horizontalStep, 1)}
        >
          <i className="fa fa-angle-right" />
        </Button>
        <Button
          className="arrow arrow-down"
          disabled={this.props.movables.sample_vertical.state !== 2 ||
                    this.props.movablesDisabled}
          onClick={() => this.stepChange('sample_vertical', sample_verticalStep, -1)}
        >
          <i className="fa fa-angle-down" />
        </Button>
      </div>
    );
  }
}

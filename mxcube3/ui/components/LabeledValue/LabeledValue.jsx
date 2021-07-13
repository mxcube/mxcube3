import React from 'react';
import { Label } from 'react-bootstrap';

import './style.css';


export default class LabeledValue extends React.Component {
  render() {
    let labelStyle = { backgroundColor: 'transparent', display: 'block',
      marginBottom: '3px', color: '#000' };
    let valueStyle = { backgroundColor: 'transparent', display: 'block-inline',
      fontSize: '100%', borderRadius: '0px', color: '#000',
      padding: '0px' };

    if (this.props.look === 'vertical') {
      labelStyle = { display: 'block', marginBottom: '3px' };
      valueStyle = { display: 'block', fontSize: '100%', borderRadius: '0px' };
    }

    let value = this.props.value.toFixed(parseInt(this.props.precision, 10));

    if (this.props.format === 'expo') {
      value = parseFloat(this.props.value).toExponential(this.props.precision);
    }

    return (
      <div>
        <span>
          <div>
            <Label
              bsStyle="default"
              style={ labelStyle }
            >
              {this.props.name}
            </Label>
          </div>
          <div>
            <Label
              bsStyle={this.props.level}
              style={ valueStyle }
            >
              {value} {this.props.suffix}
            </Label>
          </div>
        </span>
      </div>
    );
  }
}

LabeledValue.defaultProps = {
  extraInfo: {},
  value: 0,
  name: '',
  suffix: '',
  precision: '1',
  format: '',
  look: 'horizontal',
  level: 'info'
};

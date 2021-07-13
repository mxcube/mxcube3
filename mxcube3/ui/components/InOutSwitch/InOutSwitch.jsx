import React from 'react';
import { Label, Button, OverlayTrigger, Popover } from 'react-bootstrap';


export default class InOutSwitch extends React.Component {
  constructor(props) {
    super(props);
    this.setOff = this.setOff.bind(this);
    this.setOn = this.setOn.bind(this);
    this.onLinkRightClick = this.onLinkRightClick.bind(this);
    this.onOptionsRightClick = this.onOptionsRightClick.bind(this);
  }


  onLinkRightClick(e) {
    this.refs.overlay.handleToggle();
    e.preventDefault();
  }


  onOptionsRightClick(e) {
    this.refs.optionsOverlay.handleToggle();
    e.preventDefault();
  }

  setOff() {
    if (this.props.onSave !== undefined) {
      this.props.onSave(this.props.pkey, this.props.offText);
    }

    this.refs.overlay.hide();
  }


  setOn() {
    if (this.props.onSave !== undefined) {
      this.props.onSave(this.props.pkey, this.props.onText);
    }

    this.refs.overlay.hide();
  }


  renderLabel() {
    let optionsLabel = (
      <Label
        style={{ display: 'block', marginBottom: '3px' }}
      >
        {this.props.labelText}
      </Label>);

    if (this.props.optionsOverlay) {
      optionsLabel = (
         <OverlayTrigger
           ref="optionsOverlay"
           rootClose
           trigger="click"
           placement="bottom"
           overlay={ this.props.optionsOverlay }
         >
           <div onContextMenu={this.onOptionsRightClick}>
             <Label
               style={{ display: 'block', marginBottom: '3px' }}
             >
               { this.props.labelText }
               <span>
                 <i className="fa fa-cog" />
               </span>
             </Label>
           </div>
        </OverlayTrigger>);
    }

    return optionsLabel;
  }

  render() {
    let msgBgStyle = 'warning';
    if (this.props.data.value === this.props.onText) {
      msgBgStyle = 'success';
    } else if (this.props.data.value === this.props.offText) {
      msgBgStyle = 'danger';
    }

    let btn = <Button block bsSize="small" disabled>---</Button>;

    if (this.props.data.value === this.props.onText) {
      btn = <Button block bsSize="small" onClick={this.setOff}>Set: {this.props.offText}</Button>;
    } else {
      btn = <Button block bsSize="small" onClick={this.setOn}>Set: {this.props.onText}</Button>;
    }

    const msgLabelStyle = { display: 'block', fontSize: '100%',
      borderRadius: '0px', color: '#000' };

    return (
      <div>
       {this.renderLabel()}
        <OverlayTrigger
          ref="overlay"
          rootClose
          trigger="click"
          placement="bottom"
          overlay={(<Popover id={`${this.props.labelText} popover`}>{btn}</Popover>)}
        >
          <div onContextMenu={this.onLinkRightClick}>
            <Label bsStyle={msgBgStyle} style={msgLabelStyle}>{this.props.data.msg}</Label>
          </div>
        </OverlayTrigger>
      </div>
    );
  }
}


InOutSwitch.defaultProps = {
  onText: 'Open',
  offText: 'Close',
  labelText: '',
  pkey: undefined,
  onSave: undefined,
  data: { value: 'undefined', state: 'IN', msg: 'UNKNOWN' }
};

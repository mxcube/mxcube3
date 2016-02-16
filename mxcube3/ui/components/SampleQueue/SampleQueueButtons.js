'use strict';
require("font-awesome-webpack");

import React from 'react'
import "./app.less"

export default class SampleQueueButtons extends React.Component {


     handleSubmit(){
            this.props.checked.map( (queue_id) =>{
                if(this.props.lookup[queue_id]){
                    this.props.addMethod(queue_id, this.props.lookup[queue_id],{Type: "Centring"});
                }
            });

    }


    render() { 
        return (
             <div className='footer-buttons'>

                    <div className='queue-box'>
                        <a className='btn btn-primary queue-button' onClick={() => this.handleSubmit()}>
                            <i className='fa fa-fw fa-plus-square'></i>
                                Centring
                        </a>
                        <a className='btn btn-primary queue-button' onClick={() => this.props.showForm("characterisation")}>
                            <i className='fa fa-fw fa-plus-square'></i>
                                Characterisation
                        </a>
                        <a className='btn btn-primary queue-button' onClick={() => this.props.showForm("datacollection")}>
                            <i className='fa fa-fw fa-plus-square'></i>
                                Datacollection
                        </a>
                    </div>
                    <div className='queue-box'>
                        <button type="button" className="btn queue-controlls" onClick={() => this.props.pauseQueue()}>
                            <i className="fa fa-pause"></i>
                        </button>
                        <button type="button" className="btn queue-controlls" onClick={() => this.props.runQueue()}>
                            <i className="fa fa-play"></i>
                        </button>
                        <button type="button" className="btn queue-controlls" onClick={() => this.props.stopQueue()}>
                            <i className="fa fa-stop"></i>
                        </button>
                    </div>
            </div>
        );
    }
}
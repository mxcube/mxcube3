const warn = (values, props) => {
  const warnings = {};
  if (!props.attributes) {
    // for some reason redux-form is loaded before the initial status
    return warnings;
  }
  const energy = parseFloat(values.energy);
  const blEnergy = parseFloat(props.attributes.energy.value);
  const energyThreshold = blEnergy * 0.01;

  const resolution = parseFloat(values.resolution);
  const blResolution = parseFloat(props.attributes.resolution.value);
  const resThreshold = blResolution * 0.01;

  const trans = parseFloat(values.transmission);
  const blTrans = parseFloat(props.attributes.transmission.value);
  const transThreshold = blTrans * 0.01;

  if (blEnergy - energyThreshold > energy || energy > blEnergy + energyThreshold) {
    warnings.energy = 'Entered energy is different from current energy';
  }

  if (blResolution - resThreshold > resolution || resolution > blResolution + resThreshold) {
    warnings.resolution = 'Entered resolution is different from current resolution';
  }

  if (blTrans - transThreshold > trans || trans > blTrans + transThreshold) {
    warnings.transmission = 'Entered transmission is different from current transmission';
  }

  if (props.beamline.attributes.omega.value !== parseFloat(values.osc_start)) {
    warnings.osc_start = 'Oscillation start angle is different from current omega';
  }

  if (props.pointID !== -1 && props.pointID.includes('2D')
      && (parseFloat(values.osc_range) * parseFloat(values.num_images)) > 5) {
    warnings.osc_range = 'The given oscillation range might be to large for this centering';
  }

  return warnings;
};

export default warn;

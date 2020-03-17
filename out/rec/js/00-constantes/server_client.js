function _swap(json){
  var ret = {};
  for(var key in json){
    ret[json[key]] = key;
  }
  return ret;
}
PARAMS_CLIENT_SERVER = {
    'tepri': 'prim_tmed',
    'prpri': 'prim_prec',
    'temed': 'tmed',
    'temin': 'tmin',
    'temax': 'tmax',
    'tevar': 'tdesviacion',
    'vevie': 'velmedia',
    'ravie': 'racha',
    'prmax': 'presmax',
    'prmin': 'presmin',
    'hurel': 'hr',
    'hrsol': 'sol',
    'prmed': 'prec'
}
PARAMS_SERVER_CLIENT = _swap(PARAMS_CLIENT_SERVER);

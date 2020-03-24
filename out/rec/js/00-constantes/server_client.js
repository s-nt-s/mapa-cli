function _swap(json){
  var ret = {};
  for(var key in json){
    ret[json[key]] = key;
  }
  return ret;
}
PARAMS_CLIENT_SERVER = {
    'prim_tmed': 'prim_tmed',
    'prin_prec': 'prim_prec',
    'temp_medi': 'tmed',
    'temp_mini': 'tmin',
    'temp_maxi': 'tmax',
    'temp_vari': 'tdesviacion',
    'tmin_vari': 'tdesviacion',
    'vien_velm': 'velmedia',
    'vien_rach': 'racha',
    'pres_maxi': 'presmax',
    'pres_mini': 'presmin',
    'hume_rela': 'hr',
    'hora_sol': 'sol',
    'prec_medi': 'prec'
}
PARAMS_SERVER_CLIENT = _swap(PARAMS_CLIENT_SERVER);

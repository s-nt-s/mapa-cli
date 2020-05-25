var prediccion_semanal={};
$.getJSON("https://dataia.mapa.gob.es/data-municipios/aemet/prediccion_semanal.json", function(
  data,
  status,
  http
) {
  prediccion_semanal = data;
  var dtC = http.getResponseHeader("date");
  var dtM = http.getResponseHeader("last-modified");
  dtC = dtC?new Date(dtC):null;
  dtM = dtM?new Date(dtM):null;
  //if (dtC>=fecha || dtM>=fecha) return true;
  if (dtM>=fecha) return http.status;
  if (dtC) dtC = getStrFecha(dtC);
  if (dtM) dtM = getStrFecha(dtM);
  console.log(this.url);
  console.log("date:          "+dtC+"\nlast-modified: "+dtM+"\n"+method+" "+url);
});

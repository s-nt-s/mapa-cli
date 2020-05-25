var prediccion_semanal={};
$.getJSON("https://dataia.mapa.gob.es/data-municipios/aemet/prediccion_semanal.json", function(
  data,
  status,
  http
) {
  prediccion_semanal = data;
  logHttp(this.url, http);
});

var prediccion_semanal={};
$.getJSON("https://dataia.mapa.gob.es/data-municipios/aemet/prediccion_semanal.json", function( data ) {
  prediccion_semanal = data;
});

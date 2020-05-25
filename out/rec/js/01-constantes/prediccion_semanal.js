var prediccion_semanal={};
$.getJSON("https://dataia.mapa.gob.es/data-municipios/aemet/prediccion_semanal.json", function(
  data,
  status,
  http
) {
  prediccion_semanal = data;
  logHttp(this.url, http, prediccion_semanal["__timestamp__"]);
  if (prediccion_semanal["__timestamp__"]) {
    $(document).ready(function() {
        var d=new Date(0)
        d.setUTCSeconds(prediccion_semanal["__timestamp__"]);
        var eq = $("span.datos_aemet_prediccion_semanal");
        eq.html("aemet (obtenidos hace "+intervalo(d, true)+")");
        eq.attr("title", getStrFecha(d))
    });
  }
});

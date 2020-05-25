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
        var hace = seconds_to_hours(intervalo(d, false));
        eq.html("aemet (obtenidos hace <span>"+hace+"</span>)");
        eq.find("span").attr("title", getStrFecha(d))
    });
  }
});

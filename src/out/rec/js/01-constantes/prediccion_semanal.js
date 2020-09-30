var prediccion_semanal={};
$.getJSON("https://dataia.mapa.gob.es/data-municipios/aemet/prediccion_semanal.json", function(
  data,
  status,
  http
) {
  prediccion_semanal = data;
  logHttp(this.url, http, prediccion_semanal["__timestamp__"]);
  var time = prediccion_semanal["__elaborado__"] || prediccion_semanal["__timestamp__"];
  if (time) {
    $(document).ready(function() {
        var d=new Date(0);
        var elab = prediccion_semanal["__elaborado__"];
        var time = elab || prediccion_semanal["__timestamp__"];
        d.setUTCSeconds(time);
        var eq = $("span.datos_aemet_prediccion_semanal");
        var hace = seconds_to_hours(intervalo(d, false));
        if (elab) {
          eq.html("aemet (elaborados hace <span>"+hace+"</span>)");
        } else {
          eq.html("aemet (obtenidos hace <span>"+hace+"</span>)");
        }
        eq.find("span").attr("title", getStrFecha(d))
    });
  }
});

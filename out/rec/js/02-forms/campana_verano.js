function showResultado(html, label) {
  if (!html) html='';
  $("#loading").hide();
  $("#resultado .content").html(html);
  ieDownloadEvent();
  var tResultado = $("#tResultado");
  tResultado.text(label || tResultado.data("default"))
  var i = $("#iResultado").show().find("i");
  if (!$("#resultado .content").is(":visible")) i.click();
  $("#limpiar").show().find("a").show();
}

function inputToHtml(obj) {
  var i, t, c, v;
  var zonas = obj.input.zona.map(function(k) { return TXT.zonas[k] })
  zonas = zonas.join(", ");
  var mode = obj.input.rango_temporal.join(", ")
  var evlu = obj.input.rango_temporal_evaluar?obj.input.rango_temporal_evaluar.join(", "):null;
  var pred = "";
  for (i=0;i<obj.input.check_meteo_param.length;i++) {
    c = obj.input.check_meteo_param[i]
    t = TXT.check_meteo_param[c]
    v = obj.input[c];
    pred = pred + "<li>"+t+": "+v+"</li>";
  }
  var html=`
  <h2>Datos del entrenamiento</h2>
  <ul>
    <li>Región: ${zonas}</li>
    <li>Target: ${TXT.canana_verano_target[obj.input.target]}</li>
    <li>Reg. Ridge (α): ${obj.alpha_ridge}</li>
    <li>Años modelo: ${mode}</li>
    <li>Años evaluciaón: ${evlu}</li>
    <li>Predictores:
      <ul>
        ${pred}
      </ul>
    </li>
  </ul>
  `
  html = html.replace(/^.*\bnull\b.*$/gm, "");
  return html;
}


ON_ENDPOINT["analisis_anual"]=function(data, textStatus, jqXHR) {
    var obj = data;//.status?objForm(form):data;
    if (textStatus!="success") return false;

    var html=inputToHtml(obj)
    showResultado(html);

    return true
}
ON_ENDPOINT["predicion_anual"]=function(data, textStatus, jqXHR) {
    var obj = data;//.status?objForm(form):data;
    if (textStatus!="success") return false;

    var html=inputToHtml(obj)
    showResultado(html);

    return true;
}

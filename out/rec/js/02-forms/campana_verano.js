function getNivelTxt(n) {
  if (n==1) return "muy alto";
  if (n==0) return "alto";
  if (n==-1) return "bajo"
  return "";
}
function getTargetUnidad(t, v) {
  if (v==1) {
    if (t==0) return "hectárea";
    return "incendio";
  }
  if (t==0) return "hectáreas";
  return "incendios";
}
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

function inputToHtml(obj, _class) {
  if (!_class) _class='';
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
  <ul class='${_class}'>
    <li>Región: ${zonas}</li>
    <li>Target: ${TXT.capana_verano_target[obj.input.target]}</li>
    <li>Reg. Ridge (α): ${spanNumber(obj.alpha_ridge,2)}</li>
    <li class="annos_modelo">Años modelo: ${mode}</li>
    <li>Años evaluciaón: ${evlu}</li>
    <li class='hide'>Predictores:
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

    var i, c, p, table, cels;
    var html="";

    html = html + `
      <h2>Error absoluto</h2>
      <ul class='big dosEnteros dosDecimales'>
        <li title='Precisión de la predicción probabilística (sin tener en cuenta ningún parámetro)'><code>${spanNumber(obj.baseline, 2)}</code> <b>baseline</b></li>
        <li title=''><code>${spanNumber(obj.mae, 2)}</code> <b>error medio</b></li>
        <li title='Porcentaje explicado por el modelo'><code>${spanNumber(obj.cargaexplicativa, 2)}%</code> <b>carga explicativa</b></li>
      </ul>
      <h2>Acierto relativo</h2>
      <ul class='big dosEnteros dosDecimales'>
        <li title=''><code>${spanNumber(obj.spearman, 2)}</code> <b>spearman</b></li>
        <li title=''><code>${spanNumber(obj.pvalor, 2)}</code> <b>p-valor</b></li>
        <li title=''>Nivel de significancia ${getNivelTxt(obj.nivel_significativo)}</li>
      </ul>
    `;

    html = html + "<h2>Predicción vs realidad</h2>"

    cels = [
      "Año", "Predicción", "Valor real"
    ];
    for (i=0; i<obj.annos.length; i++) {
      cels.push(obj.annos[i]);
      cels.push(`<code>${spanNumber(obj.prediccion[i], 2)}</code>`);
      cels.push(`<code>${spanNumber(obj.valor_real[i], 2)}</code>`);
    }

    table = buildTable("numbers"+(obj.input.target==0?" dosDecimales":""), 3, cels);
    table = table.replace("<thead>", "<thead><tr><th ></th><th colspan='2' style='text-align: center;'>"+getTargetUnidad(obj.input.target).toCapitalize()+"</th></tr>");
    html = html + table;

    cels = [
      {"class":"txt", "txt": "Predictor"}, "Valor usado",
    ];
    for (i=0; i<obj.annos.length; i++) {
      cels.push(obj.annos[i])
    }
    var row_size = cels.length;
    for (c=0; c<obj.predictores.length;c++) {
      p = obj.predictores[c];
      cels.push(TXT.check_meteo_param[p]);
      cels.push(`<code>${obj.input[p]}</code> <span class='unidades'>${TXT.unidad[p]}</span>`);
      for (i=0; i<obj.annos.length; i++) {
        cels.push(`<code>${spanNumber(obj.coeficientes[i][c], 2)}</code>`);
      }
    }
    table = buildTable("numbers dosDecimales tableScroll", row_size, cels);
    table = table.replace("<thead>", "<thead><tr><th colspan='2'></th><th colspan='"+(obj.annos.length)+"' style='text-align: center;'>Coeficiente</th></tr>");
    html = html + table;

    html = html + inputToHtml(obj, "analisis")

    showResultado(html, "Resultado análisis anual");

    return true
}
ON_ENDPOINT["prediccion_anual"]=function(data, textStatus, jqXHR) {
    var obj = data;//.status?objForm(form):data;
    if (textStatus!="success") return false;

    var cels = null;
    var html="";

    html = html + `
      <p><strong>Predicción:</strong> ${spanNumber(obj.prediccion, 0)} ${getTargetUnidad(obj.input.target, obj.prediccion)}</p>
    `;
    cels = [
      {"class":"txt", "txt": "Predictor"}, "Valor usado", "Coeficiente"
    ];
    for (var [key, value] of Object.entries(obj.coeficientes)) {
      cels.push(TXT.check_meteo_param[key]);
      cels.push(`<code>${obj.input[key]}</code> <span class='unidades'>${TXT.unidad[key]}</span>`);
      cels.push(`<code>${spanNumber(value, 2)}</code>`);
    }
    html = html + buildTable("numbers", 3, cels);
    html = html + inputToHtml(obj, "prediccion");

    html = html + "<p>Años del modelo y "+(obj.input.target==0?"las hectareas quemadas":"el número de incendios")+" en dicho año:</p>";

    cels = [
      "Año", getTargetUnidad(obj.input.target).toCapitalize()
    ]
    for (var [key, value] of Object.entries(obj.valor_real)) {
      cels.push(key);
      cels.push(`<code>${spanNumber(value, 2)}</code>`);
    }
    html = html + buildTable("numbers", 2, cels);

    showResultado(html, "Resultado predicción anual");

    return true;
}

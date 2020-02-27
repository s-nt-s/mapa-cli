function setBarChar(id, title, labels, dataset) {
    var elem = document.getElementById(id)
    var ctx = elem.getContext('2d');
    var dat = {
        type: 'bar',
        data: {
            labels: labels,
            datasets: dataset
        },
        options: {
            title: {
              display: title!=null,
              text: title,
            },
            tooltips: {
              mode: 'index',
              intersect: false
            },
            responsive: true,
            scales: {
              xAxes: [{
                stacked: true,
              }],
              yAxes: [{
                ticks: {
                    beginAtZero: true
                }
              }]
            },
            onResize: function(ch, sz)  {
              var div = $(ch.canvas).closest("div.canvas_wrapper");
              if (div.length == 0) return;
              var max_height = $("#sidebar").height() - 300;
              if (sz.height>max_height) {
                var ratio = sz.width / sz.height;
                var max_width = max_height * ratio;
                div.css("width", max_width+"px");
              }
              else div.css("width", "");
            }
        }
    };
    var i;
    for (i=0; i<dataset.length && !dat.options.legend;i++) {
      if (dataset[i].label==null) dat.options.legend={display:false};
    }
    var myChart = new Chart(ctx, dat);
    if (dataset.length>1) myChart.options.scales.yAxes[0].ticks.max = myChart.scales["y-axis-0"].max;
    $(elem).data("chart", myChart);
    return myChart;
}

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
function showResultado(html, label, descarga) {
  if (!html) html='';
  if (descarga) {
      var strAhora = getStrFecha();
      var md = html_to_md(`<h1>${label} ${strAhora}</h1>${html}`);
      md = md.replace(/℃/g, "*").replace(/°/g, "*").replace(/\s*\(α\)/g, "").replace(/\*CC/g, "*C");
      var _md = btoa(toWin(md));
      //var _csv = btoa(toWin(csv));
      var strAhora = getPthFecha();
      html = html + `
      <p class='avoidDwn'>
        <a class="aButton" download="${descarga}_${strAhora}.txt" href="data:text/plain;base64,`+_md+`" class="button"><button>Descargar resumen (txt)</button></a>
      </p>
      `;
  }
  $("#loading").hide();
  $("#resultado .content").html(html);
  ieDownloadEvent();
  var tResultado = $("#tResultado");
  tResultado.html(label || tResultado.data("default"))
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
    <li class='hide avoidMd'>Predictores:
      <ul>
        ${pred}
      </ul>
    </li>
  </ul>
  `
  html = html.replace(/^.*\bnull\b.*$/gm, "");
  return html;
}

function datoToPoints() {
  var data = arguments[0].data;

  var backgroundColor, borderColor;
  var points=[];
  var i, c, point, field;
  for (i=0; i<data.labels.length; i++) {
    point = {"label":data.labels[i]};
    for (c=1; c<arguments.length; c++) {
      field = arguments[c];
      point[field] = data.datasets[c-1].data[i];
      backgroundColor = data.datasets[c-1].backgroundColor;
      borderColor = data.datasets[c-1].borderColor;
      if (Array.isArray(backgroundColor)) point[field+"_backgroundColor"] = backgroundColor[i];
      if (Array.isArray(borderColor)) point[field+"_borderColor"] = borderColor[i];
    }
    points.push(point)
  }
  return points;
}

function pointToData(points) {
  var data={}
  var k, i, p;
  for (k in points[0]) data[k]=[];
  for (i=0;i<points.length;i++) {
    p=points[i];
    for (k in p) {
      data[k].push(p[k]);
    }
  }
  return data;
}

function reorderVeranoChart(btn) {
  btn = $(btn);
  var defTxt = btn.data("deftxt");
  if (!defTxt) {
    defTxt = btn.text().trim()
    btn.data("deftxt", defTxt);
  }
  btn.prop("disabled", true);
  var myChart = $("#myChart").data("chart");
  var _text = null;
  var _ordr = btn.data("order");
  if (_ordr) {
    _text = "Ordenar por año";
    _ordr = myChart.options.data_order[_ordr];
  } else {
    _text = defTxt;
    _ordr = myChart.options.data_order[_ordr];
  }
  var dt;
  var index=0;
  myChart.data.labels = _ordr.label;
  if (_ordr.predi) {
    dt = myChart.data.datasets[index++]
    dt.data = _ordr.predi;
    if (_ordr.predi_backgroundColor) dt.backgroundColor = _ordr.predi_backgroundColor;
    if (_ordr.predi_borderColor) dt.borderColor = _ordr.predi_borderColor;
  }
  if (_ordr.varel) {
    dt = myChart.data.datasets[index++]
    dt.data = _ordr.varel;
    if (_ordr.varel_backgroundColor) dt.backgroundColor = _ordr.varel_backgroundColor;
    if (_ordr.varel_borderColor) dt.borderColor = _ordr.varel_borderColor;
  }
  myChart.update();
  btn.text(_text);
  btn.data("order", (btn.data("order") + 1) % 2);
  btn.prop("disabled", false);
}

$(document).ready(function() {
  $("button[name='set_meteo_param_val']").click(function(){
    var t=$(this).closest("form");
    var z=t.find("select[name='zona[]']").val();
    var isSpain=(z.length==1)?(z[0]=="ESP"):false;
    var obj={}
    var v, k;
    for (const [key, value] of Object.entries(meta_info["ultimo_meteo"])) {
      if (isSpain || z.includes(key)) {
        for (const [prm, val] of Object.entries(value)) {
          v = obj[prm] || [];
          v.push(val);
          obj[prm] = v;
        }
      }
    }
    var _getSum = function getSum(total, num) {return total + num;}
    for (const [key, value] of Object.entries(obj)) {
      k = PARAMS_SERVER_CLIENT[key] || key;
      v = value.reduce(_getSum, 0) / value.length;
      v = Math.round(v*100)/100;
      obj[k] = v;
    }
    t.find(".meteo_predictores input[type=number]").each(function(){
      var e=$(this);
      var v = obj[e.attr("name")];
      if (v!=null) e.val(v);
    })
  });
  $("select[name='predecir_o_analizar']").change(function(){
    if (!this.value) return;
    var t = $(this);
    var predi = t.find_in_parents(".meteo_predictores");
    var annos = t.find_in_parents("select[name='rango_temporal[]']");
    predi.removeClass("meteo_predictores_a meteo_predictores_p")
    predi.addClass("meteo_predictores_"+this.value);
    if (this.value == "a") {
      annos.data("min", 10);
      predi.find("input[type='number']").prop("required", false);
    }
    else if (this.value == "p") {
      annos.data("min", 3);
      predi.find("input[type='number']").prop("required", true);
    }
    annos.change();
  }).change()
});



ON_ENDPOINT["analisis_anual"]=function(data, textStatus, jqXHR) {
    var obj = data;//.status?objForm(form):data;
    if (textStatus!="success") return false;

    var i, c, p, table, cels, v;
    var html="";

    html = html + `
      <h2>Error absoluto</h2>
      <ul class='big dosEnteros dosDecimales'>
        <li title='Error medio  de los valores reales respecto al valor medio'><b>Baseline</b>: <code>${spanNumber(obj.baseline, 2)}</code> ${getTargetUnidad(obj.input.target, obj.baseline).toCapitalize()}</li>
        <li title='Error medio de los valores reales respecto a las predicciones'><b>Error medio</b>: <code>${spanNumber(obj.mae, 2)}</code> ${getTargetUnidad(obj.input.target, obj.mae).toCapitalize()}</li>
        <li title='Porcentaje explicado por el modelo'><b>Carga explicativa</b>: <code>${spanNumber(obj.cargaexplicativa, 2)}%</code> </li>
      </ul>
    `;
    if (obj.pvalor != null) {
    html = html + `
      <h2>Acierto relativo</h2>
      <ul class='big dosEnteros dosDecimales'>
        <li title='Valor de correlación entre valor real y predicción para los años evaluados'><code>${spanNumber(obj.spearman, 2)}</code> <b>spearman</b></li>
        <li title='Valor de significancia de la correlación de Spearman'><code>${spanNumber(obj.pvalor, 2)}</code> <b>p-valor</b></li>
        <li title=''>Nivel de significancia ${getNivelTxt(obj.nivel_significativo)}</li>
      </ul>
    `;
    }

    html = html + "<h2>Predicción vs realidad</h2>"

    cels = [
      "Año", "Predicción", "Valor real"
    ];
    var prediccion=[];
    var valor_real=[];
    for (i=0; i<obj.annos.length; i++) {
      p = Math.round(obj.prediccion[i]*100)/100
      v = Math.round(obj.valor_real[i]*100)/100;
      prediccion.push(p);
      valor_real.push(v);
      cels.push(obj.annos[i]);
      cels.push(`<code>${spanNumber(obj.prediccion[i], 2)}</code>`);
      cels.push(`<code>${spanNumber(obj.valor_real[i], 2)}</code>`);
    }

    table = buildTable("numbers"+(obj.input.target==0?" dosDecimales":""), 3, cels);
    table = table.replace("<thead>", "<thead><tr><th></th><th colspan='2' style='text-align: center;'>"+getTargetUnidad(obj.input.target).toCapitalize()+"</th></tr>");
    html = html + table + `
      <div class="canvas_wrapper">
        <canvas id="myChart"></canvas>
      </div>
      <button onclick="reorderVeranoChart(this)" data-order="1">Ordenar por valor real</button>
    `;

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

    showResultado(html, "Resultado análisis <abbr title='campaña'>c.</abbr> verano", "analisis");

    var myChart = setBarChar('myChart', getTargetUnidad(obj.input.target).toCapitalize(), obj.annos, [{
          label: "Predicción",
          data: prediccion,
          backgroundColor: 'rgba(255, 99, 132, 0.2)',
          borderColor: 'rgba(255, 99, 132, 1)',
          borderWidth: 1
      },{
          label: "Valor real",
          data: valor_real,
          backgroundColor: 'rgba(54, 162, 235, 0.2)',
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1
    }]);
    var points = datoToPoints(myChart, "predi", "varel");
    myChart.options.data_order = [
      pointToData(points.sort(function(a, b) {return a.label - b.label;})),
      pointToData(points.sort(function(a, b) {
        var x = a.varel - b.varel;
        if (x!=0) return -x;
        return a.label - b.label;
      }))
    ]
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
    html = html + buildTable("numbers dosDecimales", 3, cels) + `
      <div class="canvas_wrapper">
        <canvas id="myChart"></canvas>
      </div>
      <button onclick="reorderVeranoChart(this)" data-order="1">Ordenar por ${getTargetUnidad(obj.input.target)}</button>
    `;

    html = html + inputToHtml(obj, "prediccion");

    html = html + "<p>Años del modelo y "+(obj.input.target==0?"las hectareas quemadas":"el número de incendios")+" en dicho año:</p>";

    cels = [
      "Año", getTargetUnidad(obj.input.target).toCapitalize()
    ]
    var annos=[];
    var valre=[];
    var backgroundColor=[];
    var borderColor=[];
    for (var [key, value] of Object.entries(obj.valor_real)) {
      annos.push(key);
      valre.push(Math.round(value*100)/100);
      cels.push(key);
      cels.push(`<code>${spanNumber(value, 2)}</code>`);
      backgroundColor.push('rgba(54, 162, 235, 0.2)');
      borderColor.push('rgba(54, 162, 235, 1)');
    }
    annos.push("predicción");
    valre.push(Math.round(obj.prediccion*100)/100);
    backgroundColor.push('rgba(255, 99, 132, 0.2)');
    borderColor.push('rgba(255, 99, 132, 1)');
    html = html + buildTable("numbers dosDecimales", 2, cels);

    showResultado(html, "Resultado predicción <abbr title='campaña'>c.</abbr> verano", "prediccion");

    var myChart = setBarChar('myChart', getTargetUnidad(obj.input.target).toCapitalize(), annos, [{
        label: null,
        data: valre,
        backgroundColor: backgroundColor,
        borderColor: borderColor,
        borderWidth: 1
    }]);
    var points = datoToPoints(myChart, "varel");
    myChart.options.data_order = [
      pointToData(points.sort(function(a, b) {return a.label - b.label;})),
      pointToData(points.sort(function(a, b) {
        var x = a.varel - b.varel;
        if (x!=0) return -x;
        return a.label - b.label;
      }))
    ]
    return true;
}

ON_ENDPOINT["prediccion_semana_provincia"]=function(data, textStatus, jqXHR) {
  var obj = data;//.status?objForm(form):data;
  if (textStatus!="success") return false;
  var html = "";
  if (obj.input.semana) {
    html = html + `
    <ul>
      <li><b>Semana</b>: ${obj.input.semana}</li>
      <li title='Error medio de los valores reales respecto a las predicciones'><b>Error medio</b>: <code>${spanNumber(obj.mae, 2)}</code> ${getTargetUnidad(obj.input.target, obj.mae).toCapitalize()}</li>
    </ul>
    `
  }

  var cels=[
    {"class":"txt", "txt": "Provincia"},
    getTargetUnidad(obj.input.target).toCapitalize()
  ]
  if (obj.input.semana) {
    cels.push("Valor real");
  }

  for (var [key, value] of Object.entries(obj.prediccion)) {
    cels.push(TXT.zonas[key]);
    cels.push(`<code>${spanNumber(value, obj.input.target==0?2:0)}</code>`);
    if (obj.input.semana) {
      cels.push(`<code>${spanNumber(obj.valor_real[key], obj.input.target==0?2:0)}</code>`);
    }
  }
  html = html + buildTable("numbers greycero "+(obj.input.target==0?"dosDecimales":""), obj.input.semana?3:2, cels);

  if (!obj.input.semana) {
    html = html + `
      <p class="avoidMd show_hide_cero">
        <input type='checkbox' onclick="$('tr.is_cero').toggleClass('hide')" id='show_hide_cero'>
        <label for='show_hide_cero'>
          Mostrar provincias con predicción igual a <code>0</code>
        </label>
      </p>
    `
  }
  showResultado(html, "Resultado predicción semanal", "prediccion");

  if (!obj.input.semana) {
    var trs = $("#resultado .content table tr:has(span.sig_cero)")
    if (trs.length) {
      trs.addClass("is_cero").addClass("hide");
    } else {
        $("p.show_hide_cero").remove();
    }
  }

  return true;
}

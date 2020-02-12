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

function reorderAnalisisChart(btn) {
  btn = $(btn);
  btn.prop("disabled", true);
  var myChart = $("#myChart").data("chart");
  var points=[];
  var i;
  for (i=0; i<myChart.data.labels.length; i++) {
    points.push({
        "label": myChart.data.labels[i],
        "predi": myChart.data.datasets[0].data[i],
        "varel": myChart.data.datasets[1].data[i]
    })
  }
  var _text = null;
  var _sort = null;
  if (btn.data("order")) {
    _sort = function(a, b) {
      var x = a.varel - b.varel;
      if (x!=0) return -x;
      return a.label - b.label;
    }
    _text = "Ordenar por año";
  } else {
    _sort = function(a, b) {
      return a.label - b.label;
    }
    _text = "Ordenar por valor real";
  }
  points = points.sort(_sort);
  var p;
  for (i=0; i<points.length; i++) {
    p = points[i];
    myChart.data.labels[i] = p.label;
    myChart.data.datasets[0].data[i] = p.predi;
    myChart.data.datasets[1].data[i] = p.varel;
  }
  myChart.update();
  btn.text(_text);
  btn.data("order", !btn.data("order"));
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
  })
});


ON_ENDPOINT["analisis_anual"]=function(data, textStatus, jqXHR) {
    var obj = data;//.status?objForm(form):data;
    if (textStatus!="success") return false;

    var i, c, p, table, cels, v;
    var html="";

    html = html + `
      <h2>Error absoluto</h2>
      <ul class='big dosEnteros dosDecimales'>
        <li title='Precisión de la predicción probabilística (sin tener en cuenta ningún parámetro)'><code>${spanNumber(obj.baseline, 2)}</code> <b>baseline</b></li>
        <li title=''><code>${spanNumber(obj.mae, 2)}</code> <b>error medio</b></li>
        <li title='Porcentaje explicado por el modelo'><code>${spanNumber(obj.cargaexplicativa, 2)}%</code> <b>carga explicativa</b></li>
      </ul>
    `;
    if (obj.pvalor != null) {
    html = html + `
      <h2>Acierto relativo</h2>
      <ul class='big dosEnteros dosDecimales'>
        <li title=''><code>${spanNumber(obj.spearman, 2)}</code> <b>spearman</b></li>
        <li title=''><code>${spanNumber(obj.pvalor, 2)}</code> <b>p-valor</b></li>
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
    var max_value=obj.prediccion[0];
    var min_value=obj.prediccion[0];
    for (i=0; i<obj.annos.length; i++) {
      p = Math.round(obj.prediccion[i]*100)/100
      v = Math.round(obj.valor_real[i]*100)/100;
      max_value = Math.max(max_value, p, v);
      min_value = Math.min(min_value, p, v);
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
      <button onclick="reorderAnalisisChart(this)" data-order="1">Ordenar por valor real</button>
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

    showResultado(html, "Resultado análisis anual", "analisis");

    var ctx = document.getElementById('myChart').getContext('2d');
    var dat = {
        type: 'bar',
        data: {
            labels: obj.annos,
            datasets: [{
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
            }]
        },
        options: {
  					title: {
  						display: true,
  						text: getTargetUnidad(obj.input.target).toCapitalize()
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
                    /*max: Math.ceil(max_value),*/
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
    var myChart = new Chart(ctx, dat);
    myChart.options.scales.yAxes[0].ticks.max = myChart.scales["y-axis-0"].max;
    $("#myChart").data("chart", myChart);
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
    html = html + buildTable("numbers dosDecimales", 3, cels);
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


    showResultado(html, "Resultado predicción anual", "prediccion");

    return true;
}

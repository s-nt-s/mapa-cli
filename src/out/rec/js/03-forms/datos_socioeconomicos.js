var geomunicipios = null;
function riesgoTxt(v) {
  if (v==0) return "bajo";
  if (v==1) return "medio";
  if (v==2) return "alto";
  if (v==3) return "muy alto";
}


ON_ENDPOINT["__predecir"]=function(data, textStatus, jqXHR) {
    ON_ENDPOINT["predecir"]=ON_ENDPOINT["__predecir"];
    var obj = data;//.status?objForm(form):data;
    if (textStatus!="success") return false;
    this.form.find("input[type=submit]").attr("disabled", true).val("Renderizando...");
    //$("#resultado .ld_footer").removeClass("hide").text("Renderizando");
    if (layers.municipios) mymap.removeLayer(layers.municipios);
    layers.municipios={"riesgos":data}
    TXT["municipios"]={}
    var ly = L.geoJSON(geomunicipios, {
        style: function(f, l) {
          var p = f.geometry.properties;
          var v = layers.municipios.riesgos.mun[p.i].riesgo;
          var color="red";
          if (v==0) {
              color="green"
          } else if (v==1) {
              color="yellow"
          } else if (v==2) {
              color="orange"
          }
          return {
            "color": color,
            "weight": 0.5,
            "opacity": 0.7
          }
        },
        onEachFeature: function(f, l) {
          var rsg = layers.municipios.riesgos.mun[f.properties.i]
          var v = riesgoTxt(rsg.riesgo);
          l.bindTooltip(f.properties.n);
          TXT.municipios[f.properties.i]=f.properties.n;
          var hide = rsg.orden.length?"":"hide";
          var html=["<h1>"+f.properties.n+"</h1>", "<p>Riesgo <b>"+v+"</b></p>",
            `<table class='numbers dosDecimales'>
              <thead>
                <tr>
                  <th title='Orden de influencia'><abbr title='Orden de importancia'>#</abbr></th>
                  <th class='txt'>Parámetro</th>
                  <th title='Vacío cuando se ha usado un valor inferido'>Valor real</th>
                  <th>Percentil (%)</th>
                  <th class='${hide}'>Influencia (%)</th>
                </tr>
                <tbody>
            `,
          ];
          var vp = meta_info.p4.ultimo_parametros[f.properties.i];
          var orden = rsg.orden.length?rsg.orden:layers.municipios.riesgos.orden;
          orden.forEach(function(k, index) {
              var pr=TXT.params[k];
              var vr = (vp && vp.hasOwnProperty(k))?vp[k]:"";
              var v_p = `<code>${spanNumber(rsg.percentil[k])}</code>`
              var v_i = `<code>${spanNumber(rsg.influencia[k])}</code>`;
              html.push(`<tr><td class='ord'>${index+1}</td><td class='txt'>${pr}</td><td><code>${vr}</code></td><td>${v_p}</td><td class="inf ${hide}">${v_i}</td></tr>`);
          });
          html.push("</tbody></thead></table>");
          l.bindPopup(html.join("\n"), {
              "maxWidth":560
          });
        },
        filter: function (f, layer) {
          var p = f.properties;
          return p.i in layers.municipios.riesgos.mun;
        }
    });
    ly.on({
      mouseover: function(e) {
        e.originalEvent.preventDefault();
        e.originalEvent.stopPropagation();
        e.originalEvent.stopImmediatePropagation();
        e.layer.setStyle({opacity: 1, weight: 2});
      },
      mouseout: function(e) {
        e.originalEvent.preventDefault();
        e.originalEvent.stopPropagation();
        e.originalEvent.stopImmediatePropagation();
        layers.municipios.resetStyle(e.layer);
        if (e.layer._contextmenu) e.layer.setStyle({fillOpacity: 0.6});
      },
      contextmenu: function(e){
        var preTable = $("#preTable");
        if (preTable.length==0) return;
        e.originalEvent.preventDefault();
        e.originalEvent.stopPropagation();
        e.originalEvent.stopImmediatePropagation();
        var p = e.layer.feature.geometry.properties;
        var tdMun = preTable.find(".mun"+p.i);
        if (tdMun.length) {
          e.layer._contextmenu=false;
          tdMun.remove();
          layers.municipios.resetStyle(e.layer);
          if (preTable.find(".mun").length==0) preTable.find(".modelogeneral").hide();
          return;
        }
        e.layer._contextmenu=true;
        e.layer.setStyle({fillOpacity: 0.6});
        if (!(p.i in layers.municipios.riesgos.mun)) return;
        var rsg = layers.municipios.riesgos.mun[p.i];
        var hide = rsg.orden.length?"":"hide";
        var colspan = rsg.orden.length?3:2;
        var v = riesgoTxt(rsg.riesgo);
        preTable.find("thead tr:eq(0)").append("<th colspan='"+colspan+"' class='mun mun"+p.i+"' style='text-align: center;'>"+p.n+"<br/><small>(riesgo "+v+")</small></th>");
        preTable.find("thead tr:eq(1)").append("<th class='mun"+p.i+"' title='Vacío cuando se ha usado un valor inferido'>Valor real</th><th class='mun"+p.i+"'>Percentil (%)</th><th class='mun"+p.i+" "+hide+"'>Influencia (%)</th>");
        var vp = meta_info.p4.ultimo_parametros[p.i];
        var trs = preTable.find("tbody tr");
        layers.municipios.riesgos.orden.forEach(function(k, index) {
            var tr = trs.eq(index);
            var pr=TXT.params[k];
            var vr = (vp && vp.hasOwnProperty(k))?vp[k]:"";
            var v_p = `<code>${spanNumber(rsg.percentil[k])}</code>`;
            var v_i = `<code>${spanNumber(rsg.influencia[k])}</code>`;
            tr.append(`<td class='mun${p.i}'><code>${vr}</code></td><td class='mun${p.i}'>${v_p}</td><td class='mun${p.i} inf ${hide}'>${v_i}</td>`);
        });
        preTable.find(".modelogeneral").removeClass("hide").show();
      }
    });
    if (layers.provincias) mymap.removeLayer(layers.provincias)
    mymap.addLayer(ly);
    layers.municipios=ly;
    layers.municipios.riesgos=data;

    centerMap(layers.municipios);

    var html = `
    <p class='avoidMd'>Haga click con el botón secundario en los municipios que desee comparar para agregarlos a la tabla que ve aquí abajo.</p>
    <h2>Influencia de características</h2>
    <table class='numbers dosDecimales tableScroll' id='preTable'>
      <thead>
        <tr class='hide avoidMd modelogeneral'>
          <th colspan='3' style='text-align: center'>Modelo general</th>
        </tr>
        <tr>
          <th title='Orden de importancia'><abbr title='Orden de importancia'>#</abbr></th>
          <th class='txt'>Parámetro</th>
          <th>Importancia (%)</th>
        </tr>
      </thead>
      <tbody>
    `;
    obj.orden.forEach(function(k, index) {
        var pr=TXT.params[k];
        var v=obj.importancia[k]
        v = Math.round(v*100)/100;
        v = v.toString();
        var sp = v.split(/\./);
        var dc = sp.length==2?sp[1].length:0;
        var en = sp[0].length;
        v = `<code><span class="nm en${en} dc${dc}">${v}</span></code>`
        html = html + (`<tr><td class='ord'>${index+1}</td><td class='txt'>${pr}</td><td>${v}</td></tr>`);
    });
    html = html + "</tbody></table>";
    html = html + "<h2>Datos del entrenamiento</h2>";
    var zonas = obj.input.zona.map(function(k) { return TXT.zonas[k] })
    zonas = zonas.join(", ")
    var causas = obj.input.causas.map(function(k) { return "<span title='"+TXT.causas[k]+"'>"+k+"</span>" })
    causas = causas.join(", ")
    html = html + "<ul>";
    var strAhora = getStrFecha();
    html = html + `
      <li>Región: ${zonas}</li>
      <li>Causas: ${causas}</li>
      <li>Radio de influencia: ${obj.input.radio} km</li>
      <li>Rango temporal: de ${obj.input.ini} a ${obj.input.fin}</li>
      <li>Riesgo:
        <ul>
          <li>Bajo: de 0 a ${obj.input.rbajo} incendios</li>
          <li>Medio: de ${obj.input.rbajo+1} a ${obj.input.rmedio} incendios</li>
          <li>Alto: de ${obj.input.rmedio+1} a ${obj.input.ralto} incendios</li>
          <li>Muy alto: ${obj.input.ralto+1} incendios o más</li>
        </ul>
      </li>
    </ul>
    <p>Se han usado ${obj.inc_usados} incendios para realizar esta predicción.</p>
    `;

    var md = html_to_md(`<h1>Predicción ${strAhora}</h1>${html}`);

    causas=$(causas).text()
    var csv = `
Fecha;${strAhora}
Región;${zonas}
Causas;${causas}
Radio de influencia;${obj.input.radio} km
Año inicio;${obj.input.ini}
Año fin;${obj.input.fin}

Riesgo;de;a
Bajo;0;${obj.input.rbajo}
Medio;${obj.input.rbajo+1};${obj.input.rmedio}
Alto;${obj.input.rmedio+1};${obj.input.ralto}
Muy alto;${obj.input.ralto+1}

Incendios;${obj.inc_usados}

;;
    `.trim();
    var mun1 = Object.values(layers.municipios.riesgos.mun)[0];
    var infl = mun1 && mun1.orden && mun1.orden.length;
    var k,m;
    for (k in layers.municipios.riesgos.mun) {
      csv = csv+";"+k+";";
      if (infl) csv = csv + ";";
    }
    csv = csv+"\n;;"
    for (k in layers.municipios.riesgos.mun) {
      csv = csv+";"+TXT["municipios"][k]+";";

      if (infl) csv = csv + ";";
    }
    csv = csv+"\n;;"
    for (k in layers.municipios.riesgos.mun) {
      csv = csv+";riesgo "+riesgoTxt(layers.municipios.riesgos.mun[k].riesgo)+";";
      if (infl) csv = csv + ";";
    }
    csv = csv+"\n#;Parámetro;Importancia (%)"
    for (k in layers.municipios.riesgos) {
      csv = csv+";Valor real;Percentil (%)";
      if (infl) csv = csv + ";Influencia (%)";
    }
    obj.orden.forEach(function(k, index) {
        var pr=TXT.params[k];
        var v=obj.importancia[k];
        csv = csv+"\n"+(index+1)+";"+pr+";"+v;
        for (m in layers.municipios.riesgos.mun) {
          var vp = meta_info.p4.ultimo_parametros[m];
          var vr = (vp && vp.hasOwnProperty(k))?vp[k]:"";
          csv = csv+";"+vr+";"+layers.municipios.riesgos.mun[m].percentil[k];
          if (infl) csv = csv +";"+layers.municipios.riesgos.mun[m].influencia[k];
        }
    });
    csv = csv.replace(/\./g, ",");

    var strAhora = getPthFecha();
    var _md = btoa(toWin(md));
    var _csv = btoa(toWin(csv));
    html = html + `
    <p class='avoidDwn'>
      <a class="aButton" download="prediccion_${strAhora}.txt" href="data:text/plain;base64,`+_md+`" class="button"><button>Descargar resumen (txt)</button></a>
      <a class="aButton" download="prediccion_${strAhora}.csv" href="data:text/csv;base64,`+_csv+`" class="button"><button>Descargar informe (csv)</button></a>
    </p>
    `;


    $("#loading").hide();
    $("#resultado .content").html(html);
    ieDownloadEvent();
    var tResultado = $("#tResultado");
    tResultado.text($("#fSocialPrediccion").data("resultado") || tResultado.data("default"))
    var i = $("#iResultado").show().find("i");
    if (!$("#resultado .content").is(":visible")) i.click();

    $("#limpiar").show().find("a").show();
    restoreForm(this.form);
    return true;
}
ON_ENDPOINT["predecir"]=function(data, textStatus, jqXHR) {
  if (typeof geomunicipios != "undefined" && geomunicipios!=null) {
    return ON_ENDPOINT["__predecir"].apply(this, arguments);
  }
  //$("#resultado .ld_footer").removeClass("hide").text("Renderizando");
  /*
  $.getJSON("https://dataia.mapa.gob.es/data-municipios/geo/municipios.js", function( data ) {
    prediccion_semanal = data;
  });
  */
  $.ajax({
    url: "https://dataia.mapa.gob.es/data-municipios/geo/municipios.js",//myroot+"geo/municipios.js",
    dataType: "json",
    cache: true,
    origin: [this, arguments],
    success: function(
      data,
      status,
      http
    ) {
      geomunicipios=data;
      logHttp(this.url, http);
      return ON_ENDPOINT["__predecir"].apply(this.origin[0], this.origin[1]);
    }
  });
  return true;
}

ON_ENDPOINT["analisis"]=function(data, textStatus, jqXHR) {
    var obj = data;//.status?objForm(form):data;
    if (typeof obj == "object") {
      var html = `<ul class='big dosEnteros dosDecimales'>
        <li title='Precisión de la predicción probabilística (sin tener en cuenta ningún parámetro)'><code>${spanNumber(obj.baseline)}%</code> <b>baseline</b></li>
        <li title='Precisión de la predicción con los parámetros seleccionados'><code>${spanNumber(obj.accuracy)}%</code> <b>accuracy</b></li>
        <li title='Aporte bruto de la predicción con parámetros'><code>${spanNumber(obj.improvement)}%</code> <b>mejora</b></li>
        <li title='Porcentaje de la ocurrencia de incencios explicada por el modelo'><code>${spanNumber(obj.cargaexplicativa)}%</code> <b>carga explicativa</b></li>
      </ul>
      <h2>Influencia de características</h2>
      <table class='numbers dosDecimales'>
        <thead>
          <tr>
            <th title='Orden de importancia'><abbr title='Orden de importancia'>#</abbr></th>
            <th class='txt'>Parámetro</th>
            <th>Importancia (%)</th>
          </tr>
        </thead>
        <tbody>
      `;
      obj.orden.forEach(function(k, index) {
          var pr=TXT.params[k];
          var v=obj.importancia[k]
          v = Math.round(v*100)/100;
          v = v.toString();
          var sp = v.split(/\./);
          var dc = sp.length==2?sp[1].length:0;
          var en = sp[0].length;
          v = `<code><span class="nm en${en} dc${dc}">${v}</span></code>`
          html = html + (`<tr><td class='ord'>${index+1}</td><td class='txt'>${pr}</td><td>${v}</td></tr>`);
      });
      html = html + "</tbody></table>";
      html = html + "<h2>Datos del entrenamiento</h2>";
      var zonas = obj.input.zona.map(function(k) { return TXT.zonas[k] })
      zonas = zonas.join(", ")
      var causas = obj.input.causas.map(function(k) { return "<span title='"+TXT.causas[k]+"'>"+k+"</span>" })
      causas = causas.join(", ")
      html = html + `<ul>
        <li>Tipo: ${TXT.entrenamiento[obj.input.tEntrenamiento].toLowerCase()}`
      if (obj.input.tEntrenamiento=="dbToda") {
        html = html + `<ul>
          <li>hasta: ${obj.input.fin}</li>
          <li>entrenamiento: ${obj.input.prc} %</li>
          <li>test: ${100-obj.input.prc} %</li>
          <li>iteraciones: ${obj.input.folds}</li>
        </ul>`
      } else if (obj.input.tEntrenamiento=="dbPersonalizada") {
        html = html + `<ul>
          <li>de ${obj.input.ini} hasta ${obj.input.fin}</li>
          <li>año para el test: ${obj.input.test}</li>
        </ul>`
      }
      var strAhora = getStrFecha();
      html = html + `
        <li>Región: ${zonas}</li>
        <li>Causas: ${causas}</li>
        <li>Radio de influencia: ${obj.input.radio} km</li>
        <li>Riesgo:
          <ul>
            <li>Bajo: de 0 a ${obj.input.rbajo} incendios</li>
            <li>Medio: de ${obj.input.rbajo+1} a ${obj.input.rmedio} incendios</li>
            <li>Alto: de ${obj.input.rmedio+1} a ${obj.input.ralto+1} incendios</li>
            <li>Muy alto: ${obj.input.ralto+1} incendios o más</li>
          </ul>
        </li>
      </ul>
      <p>Se han usado ${obj.inc_usados} incendios para realizar este análisis.</p>
      `;

      var md = html_to_md(`<h1>Análisis ${strAhora}</h1>${html}`);
      var _md = btoa(toWin(md));
      var strAhora = getPthFecha();
      html = html + `
      <p class='avoidDwn'>
        <a class="aButton" download="analisis_${strAhora}.txt" href="data:text/plain;base64,`+_md+`" class="button"><button>Descargar informe (txt)</button></a>
      </p>
      `
      obj = html;
      //if (obj.hasOwnProperty("html")) obj = obj.html;
      //else obj="<pre>"+JSON.stringify(obj, null, 2)+"</pre>";
    }
    //$("#popup").find("div:first").html(obj);
    //$("body").addClass("showPopup");
    $("#loading").hide();
    $("#resultado .content").html(obj);
    ieDownloadEvent();
    var tResultado = $("#tResultado");
    tResultado.text($("#fSocialAnalisis").data("resultado") || tResultado.data("default"))
    var i = $("#iResultado").show().find("i");
    if (!$("#resultado .content").is(":visible")) i.click();
    return true;
}

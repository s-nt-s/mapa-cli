var now=new Date();
var hayDatosHasta=now.getFullYear()-4;
var mymap;
var layers={}
var marcas=null;
var _debug_mode=false;

var myweb = window.location.href;
myweb = myweb.substr(document.location.protocol.length+2)
if (myweb.endsWith("/")) myweb = myweb.substr(0, myweb.length-1);

var sidebar_observer = new MutationObserver(function(mutations) {
  mutations.forEach(function(mutation) {
    if (mutation.attributeName === "class") {
      elem = $(mutation.target);
      if (elem.is(".collapsed")) elem.removeClass("expanded");
      if (elem.is(".expanded")) elem.css("width", "");
    }
  });
});

function riesgoTxt(v) {
  if (v==0) return "bajo";
  if (v==1) return "medio";
  if (v==2) return "alto";
  if (v==3) return "muy alto";
}

function spanNumber(v) {
  if (v==null || v==="") return "";
  var sig="sig_cero";
  if(v<0) sig="neg";
  else if (v>0) sig="pos";
  v=v.toString();
  var sp = v.split(/\./);
  var dc = sp.length==2?sp[1].length:0;
  var en = sp[0].length;
  v = `<span class='bfr'></span><span class="nm en${en} dc${dc} ${sig}">${v}</span><span class='aft'></span>`
  return v;
}

function toUrl(url, txt, title) {
  var s_url=url.split(/:\/\//)[1];
  if (!txt) txt = s_url;
  if (title==null) title = " title='"+s_url+"'";
  return `<a href="${url}"${title}>${txt}</a>`;
}

function setIfNull(e, a, v) {
	if (v && !e.attr(a)) e.attr(a, v);
}

function set_max(selector, maximum, value, placeholder) {
  var es = $(selector);
  var i,e;
  for (i=0;i<es.length;i++) {
    e = es.eq(i);
    setIfNull(e, "placeholder", placeholder);
    setIfNull(e, "value", value);
    setIfNull(e, "max", maximum);
  }
}

function selectProvincia(e) {
  e.originalEvent.preventDefault();
  e.originalEvent.stopPropagation();
  e.originalEvent.stopImmediatePropagation();
  var p = e.layer.feature.geometry.properties;
  var zonas = $("select[name='zona[]']").eq(0);
  selected=p.i && zonas.val().indexOf(p.i)>=0;
  selected = !selected;
  if (selected) {
    zonas.find("option[value='"+p.i+"']").prop("selected", true);
  } else {
    zonas.find("option[value='"+p.i+"']").prop("selected", false);
  }
  zonas.change();
}

function layerProvincias(old) {
  var ly = L.geoJSON(geoprovincias, {
      style: function(f, l) {
        var fp = f.properties;
        var gp = f.geometry.properties;
        selected=gp.i && $("select[name='zona[]']:eq(0)").val().indexOf(gp.i)>=0;
        var color=(selected)?"blue":"green";
        return {
          "color": color,
          "weight": 5,
          "opacity": 0.10
        }
      },
      onEachFeature: function(f, l) {
        l.bindTooltip(f.properties.n);
      }
    }
  );
  ly.on({
    mouseover: function(e) {
      e.layer.setStyle({opacity: 1});
    },
    mouseout: function(e) {
      layers.provincias.resetStyle(e.layer);
    },
    click: function(e){
      var ctrl = (e && e.originalEvent && e.originalEvent.ctrlKey);
      if (ctrl) {
        selectProvincia.apply(this, arguments);
        return;
      }
      e.originalEvent.preventDefault();
      e.originalEvent.stopPropagation();
      e.originalEvent.stopImmediatePropagation();
      var p = e.layer.feature.geometry.properties;
      var zonas = $("select[name='zona[]']").eq(0);
      selected=p.i && zonas.val().indexOf(p.i)>=0;
      selected = !selected;
      zonas.find("option").prop("selected", false);
      if (selected) {
        zonas.find("option[value='"+p.i+"']").prop("selected", true);
      }
      zonas.change();
    },
    contextmenu: function(e) {
      selectProvincia.apply(this, arguments);
    }
  });
  ly.selected=[];
  layers.provincias=ly;
  return ly;
}

function centerMap(ly) {
  var bounds = (ly || layers.provincias).getBounds();
  if (Object.keys(bounds).length) {
    var bottom = Math.floor($(".leaflet-bottom.leaflet-right").height());
    var left = Math.floor($("#sidebar").width()/3);
    var opt = {"paddingTopLeft": [left, 0], "paddingBottomRight": [bottom, bottom]};
    //alert(JSON.stringify(opt, null, 2));
    mymap.fitBounds(bounds, opt);
  }
  else mymap.setView([40.4165000, -3.7025600], 6)
}

$(document).ready(function() {
/** INI READY **/
// $(".sidebar-pane").each(function(){
//   observer.observe(this, {attributes: true});
// });
sidebar_observer.observe(document.getElementById("sidebar"), {attributes: true});
mymap = L.map("map");
L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
    attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
    maxZoom: 18,
    id: 'mapbox.streets',
    accessToken: 'pk.eyJ1Ijoia2lkdHVuZXJvIiwiYSI6ImNqeTBjeG8zaTAwcWYzZG9oY2N1Z3VnazgifQ.HKixpk5HNX-svbNYxYSpsw'
}).addTo(mymap);
mymap.addLayer(layerProvincias());
centerMap();
L.control.sidebar('sidebar').addTo(mymap);

$("#tEntrenamiento").change(function() {
  var v=this.value;
  var hide;
  var show=$([]);
  var divs=$(this).closest("fieldset").find(">div");
  if (v) {
    show = divs.filter("."+v);
    hide = divs.not("."+v);
  } else{
    hide = divs;
  }
  show.show().find("input").not(".disabled").prop("disabled", false);
  hide.hide().find("input").prop("disabled", true);
}).change();
$(".fRangos input[type=range]").bind("change input",function(){
    var v = Number(this.value);
    var i=$(this);
    var ch=$([])
    var _next = i.nextAll("input[type=range]")
    var ot=_next.eq(0);
    if (ot.length && Number(ot.val())<=v) {
      var nv = v+Number(ot.attr("step"));
      ot.val(nv);
      ch = ch.add(ot);
    }
    var _prev=i.prevAll("input[type=range]")
    var ot=_prev.eq(0);
    if (ot.length && Number(ot.val())>=v) {
      var nv = v+Number(ot.attr("step"));
      ot.val(v)
      ch = ch.add(ot)
    }
    ch.change();
})
// maximum, value, placeholder
set_max("#ttEnd,#prTest,#yEnd", meta_info["p4_year"], meta_info["egif_year"], meta_info["egif_year"]);
set_max("#prEnd,#yBgn", meta_info["p4_year"]-1, meta_info["egif_year"]-1, meta_info["egif_year"]-1);
set_max("#prBng", meta_info["p4_year"]-2);
if (meta_info["p4_year"]>meta_info["egif_year"]) {
	$(".fTemporal,.dbToda,.dbPersonalizada").append("<p>(*) Tenga en cuenta que solo hay datos EGIF consolidados hasta "+meta_info["egif_year"]+", por lo tanto, cualquier rango que supere ese año trabajará con datos incompletos.</p>");
}
$("input[name='ini']").change(function(){
  var v = Number(this.value)+1;
  var e=$(this).closest("fieldset").find("input[name='fin']");
  e.attr("min", v);
  if (Number(e.val())<e.attr("min")) e.val(v).change();
}).change();
$("#prEnd").change(function(){
  var v = Number(this.value)+1;
  var e=$("#prTest");
  e.attr("min", v);
  if (Number(e.val())<e.attr("min")) e.val(v).change();
}).change();
$("#ttPrc").change(function(){
  var v = parseInt(this.value, 10);
  if (!Number.isNaN(v)) $("#ttTest").val(100-v);
}).change();

$("#fPrediccion").data("submitted", function(data, textStatus, jqXHR) {
    var obj = data;//.status?objForm(form):data;
    if (textStatus!="success") return false;
    $(this).find("input[type=submit]").attr("disabled", true).val("Renderizando...");
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
            `<table class='ordper'>
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
          var vp = valor_parametros[f.properties.i];
          var k;
          var orden = rsg.orden.length?rsg.orden:layers.municipios.riesgos.orden;
          orden.forEach(function(k, index) {
              var pr=TXT.params[k];
              var vr = vp.hasOwnProperty(k)?vp[k]:"";
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
        var vp = valor_parametros[p.i];
        var k;
        var trs = preTable.find("tbody tr");
        layers.municipios.riesgos.orden.forEach(function(k, index) {
            var tr = trs.eq(index);
            var pr=TXT.params[k];
            var vr = vp.hasOwnProperty(k)?vp[k]:"";
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
    <table class='ordper' id='preTable'>
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
    var ahora =  new Date();
    var strAhora = ahora.toLocaleDateString("es-ES", {month: '2-digit', year: 'numeric', day: '2-digit', hour:'2-digit',minute:'2-digit'});
    strAhora = strAhora.replace(/[^ \d:]+/g, "");
    html = html + `
      </li>
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
          var vp = valor_parametros[m];
          var vr = vp.hasOwnProperty(k)?vp[k]:"";
          csv = csv+";"+vr+";"+layers.municipios.riesgos.mun[m].percentil[k];
          if (infl) csv = csv +";"+layers.municipios.riesgos.mun[m].influencia[k];
        }
    });
    csv = csv.replace(/\./g, ",");


    var strAhora = ahora.getFullYear() + "." + ahora.getMonth().pad(2) + "." + ahora.getDate().pad(2)+"_"+ahora.getHours().pad(2)+"."+ahora.getMinutes().pad(2);
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
    tResultado.text($("#fPrediccion").data("resultado") || tResultado.data("default"))
    var i = $("#iResultado").show().find("i");
    if (!$("#resultado .content").is(":visible")) i.click();

    $("#limpiar").show().find("a").show();
    return true;
})
$("#fAnalisis").data("submitted", function(data, textStatus, jqXHR) {
    var obj = data;//.status?objForm(form):data;
    if (typeof obj == "object") {
      var html = `<ul class='big rAnalisis'>
        <li title='Precisión de la predicción probabilística (sin tener en cuenta ningún parámetro)'><code>${spanNumber(obj.baseline)}%</code> <b>baseline</b></li>
        <li title='Precisión de la predicción con los parámetros seleccionados'><code>${spanNumber(obj.accuracy)}%</code> <b>accuracy</b></li>
        <li title='Aporte bruto de la predicción con parámetros'><code>${spanNumber(obj.improvement)}%</code> <b>mejora</b></li>
        <li title='Porcentaje de la ocurrencia de incencios explicada por el modelo'><code>${spanNumber(obj.cargaexplicativa)}%</code> <b>carga explicativa</b></li>
      </ul>
      <h2>Influencia de características</h2>
      <table class='ordper'>
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
      var ahora =  new Date();
      var strAhora = ahora.toLocaleDateString("es-ES", {month: '2-digit', year: 'numeric', day: '2-digit', hour:'2-digit',minute:'2-digit'});
      html = html + `
        </li>
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
      var strAhora = ahora.getFullYear() + "." + ahora.getMonth().pad(2) + "." + ahora.getDate().pad(2)+"_"+ahora.getHours().pad(2)+"."+ahora.getMinutes().pad(2);
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
    tResultado.text($("#fAnalisis").data("resultado") || tResultado.data("default"))
    var i = $("#iResultado").show().find("i");
    if (!$("#resultado .content").is(":visible")) i.click();
    return true;
});
$("#resultado").bind("mouseenter", function() {
  if ($(".sidebar-contract").is(":visible")) return;
  var dv=$("#sidebar");
  var tb=dv.find("#preTable:visible");
  if (tb.length==0) {
    dv.css("width", "");
    return;
  }
  var wd = Math.max(tb.width(), tb[0].scrollWidth);
  var wR = dv.find("#resultado").width();
  if (wd<=wR) {
    dv.css("width", "");
    return;
  }
  wd = wd + (dv.width()-wR)+15;
  wd = Math.min(wd, $("body").innerWidth()-30);
  if (wd<=dv.width()) {
    dv.css("width", "");
    return;
  }
  dv.css("width", wd);
}).bind("mouseleave", function() {
  if ($(".sidebar-contract").is(":visible")) return;
  $("#sidebar").css("width", "");
});
$(".sidebar-close").click(function(){
  $("#sidebar").removeClass("expanded");
})
$("form").submit(function(e) {
    e.preventDefault(); // avoid to execute the actual submit of the form.
    var form = $(this);
    form.find("input[type=submit]").attr("disabled", true).val("Cargando...");
    var resultado=$("#resultado");
    resultado.find(".content").html("");
    resultado.find("#loading").show();
    var tResultado = $("#tResultado");
    tResultado.text(tResultado.data("default"))
    var i = $("#iResultado").show().find("i");
    if (!$("#resultado .content").is(":visible")) i.click();
    var url = form.attr('action');
    var store_in = form.find("input.store_in");
    if (store_in.length) {
      store_in.val("");
      var ahora = new Date();
      var fn = form.serialize();
      fn = btoa(fn);
      fn = encodeURIComponent(fn);
      ahora = ahora.getFullYear() + "-" + ahora.getMonth().pad(2) + "-" + ahora.getDate().pad(2);
      fn = ahora + "_" + fn + ".json";
      store_in.val(fn);
      var _url = "/rec/api/"+fn;
      if (isUrlOnline(_url)) url = _url;
    }
    $.ajax({
      type: "POST",
      url: url,
      data: form.serialize(), // serializes the form's elements.
      context: form
    }).always(function(data, textStatus, jqXHR) {
        if (this.data("submitted")) {
            var ok = this.data("submitted").apply(this, arguments);
            if (ok) return;
        }
      var obj = data.status?objForm(this):data;
      if (typeof obj == "object") {
        if (obj.hasOwnProperty("html")) obj = obj.html;
        else obj="<pre>"+JSON.stringify(obj, null, 2)+"</pre>";
      }
      $("#popup").find("div:first").html(obj);
      $("body").addClass("showPopup");
    }).always(function(data, textStatus, jqXHR) {
        var btn = this.find("input[type=submit]");
        btn.prop("disabled", false).each(function(){this.value=$(this).data("defval");});
    });
});

$("select.oneGroup").change(function(){
  var t=$(this);
  var arr=t.data("slc") || [];
  if (arr.length>0 && arr.length<t.val().length) {
    var diff=t.val().diff(arr);
    var opt = t.find("option[value='"+diff[0]+"']").closest("optgroup");
    t.find("optgroup").not(opt).find("option").prop("selected", false);
  }
  t.data("slc", t.val());
})
$("select[name='zona[]']").change(function(){
  var aVals=$(this).val();
  var other=$("select[name='zona[]']").not(this);
  var bVals=other.eq(0).val();
  other.val(aVals);
  var df = aVals.diff(bVals);
  layers.provincias.eachLayer(function(l){
    var p = l.feature.geometry.properties;
    if (p.i && df.indexOf(p.i)>=0) {
      layers.provincias.resetStyle(l);
    }
  })
})

$("select[name='zona[]'],select.oneGroup").change();
$("button.cerrar").click(function(){
    $("body").removeClass("showPopup");
});


$("#limpiar a").bind("click", function(e){
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    $("#limpiar").hide();
    var rst = $("#iResultado");
    if (rst.is(".active")) rst.find("i").click();
    rst.hide();
    if (layers.municipios) mymap.removeLayer(layers.municipios);
    if (layers.provincias) mymap.removeLayer(layers.provincias)
    mymap.addLayer(layerProvincias(layers.provincias));
    centerMap();
    return false;
})

$(".sidebar-expand").click(function(){
  var dv=$("#sidebar");
  dv.addClass("expanded");
})

$(".sidebar-contract").click(function(){
  var dv=$("#sidebar");
  dv.removeClass("expanded");
})

/** FIN READY **/
})

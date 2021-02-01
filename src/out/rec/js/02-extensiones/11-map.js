LAYERSvar mymap=null;
var LAYERS={}

function geoJSON(geo, conf) {
  if (geo==null || conf==null) throw "geoJSON: faltan parametros";
  if (conf.id==null)  throw "geoJSON: faltan id";
  var options={};
  var events={};
  ["pointToLayer", "style", "onEachFeature", "filter", "coordsToLatLng", "markersInheritOptions"].forEach((k, i) => {
    if (k in conf) {
      var v=conf[k];
      //delete conf[k];
      if (typeof v === "function") v = v.bind(conf);
      options[k]=v;
    }
  });
  ["mouseover", "mouseout", "click", "contextmenu"].forEach((k, i) => {
    if (k in conf) {
      var v=conf[k];
      //delete conf[k];
      if (typeof v === "function") v = v.bind(conf);
      events[k]=v;
    }
  });
  var ly = L.geoJSON(geo, options);
  conf.layer = ly;
  if (Object.keys(events).length) ly.on(events)
  LAYERS[conf.id]=ly;
  return ly;
}

function buildLayer(geo, conf) {
  return geoJSON(geo, Object.assign({}, conf, {
      style: function(f, l) {
        var fp = f.properties;
        var selected=fp.i && $(this.selected).eq(0).val().indexOf(fp.i)>=0;
        var color=(selected)?"blue":"green";
        return {
          "color": color,
          "weight": 5,
          "opacity": 0.10
        }
      },
      onEachFeature: function(f, l) {
        l.bindTooltip(f.properties.n);
      },
      mouseover: function(e) {
        e.layer.setStyle({opacity: 1});
      },
      mouseout: function(e) {
        this.layer.resetStyle(e.layer);
      },
      click: function(e){
        var ctrl = (e && e.originalEvent && e.originalEvent.ctrlKey);
        if (ctrl) {
          console.log(this.layer._events)
          this.contextmenu.apply(this, arguments);
          return;
        }
        e.originalEvent.preventDefault();
        e.originalEvent.stopPropagation();
        e.originalEvent.stopImmediatePropagation();
        var p = e.layer.feature.properties;
        var zonas = $(this.selected).eq(0);
        var selected=p.i && zonas.val().indexOf(p.i)>=0;
        selected = !selected;
        zonas.find("option").prop("selected", false);
        if (selected) {
          zonas.find("option[value='"+p.i+"']").prop("selected", true);
        }
        zonas.change();
      },
      contextmenu: function(e) {
        e.originalEvent.preventDefault();
        e.originalEvent.stopPropagation();
        e.originalEvent.stopImmediatePropagation();
        var p = e.layer.feature.properties;
        var zonas = $(this.selected).eq(0);
        var selected=p.i && zonas.val().indexOf(p.i)>=0;
        selected = !selected;
        if (selected) {
          zonas.find("option[value='"+p.i+"']").prop("selected", true);
        } else {
          zonas.find("option[value='"+p.i+"']").prop("selected", false);
        }
        zonas.change();
      }
    })
  )
}

function selectProvincia(e) {
  e.originalEvent.preventDefault();
  e.originalEvent.stopPropagation();
  e.originalEvent.stopImmediatePropagation();
  var p = e.layer.feature.properties;
  var zonas = $("select[name='zona[]']").eq(0);
  var selected=p.i && zonas.val().indexOf(p.i)>=0;
  selected = !selected;
  if (selected) {
    zonas.find("option[value='"+p.i+"']").prop("selected", true);
  } else {
    zonas.find("option[value='"+p.i+"']").prop("selected", false);
  }
  zonas.change();
}

function centerMap(ly) {
  var bounds = (ly || LAYERS.provincias).getBounds();
  if (Object.keys(bounds).length) {
    var bottom = Math.floor($(".leaflet-bottom.leaflet-right").height());
    var left = Math.floor($("#sidebar").width()/3);
    var opt = {"paddingTopLeft": [left, 0], "paddingBottomRight": [bottom, bottom]};
    //alert(JSON.stringify(opt, null, 2));
    mymap.fitBounds(bounds, opt);
  }
  else mymap.setView([40.4165000, -3.7025600], 6)
}

function clearMap() {
    var ok=["mapbox.streets", "capa.base"];
    mymap.eachLayer(function (layer) {
        if (ok.indexOf(layer.options.id)==-1) mymap.removeLayer(layer);
    });
}

function resetMap() {
    if (mymap==null) {
        mymap = L.map("map");
        /*
        L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
            attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
            maxZoom: 18,
            id: 'mapbox.streets',
            accessToken:  'pk.eyJ1IjoiZGF0YWlhIiwiYSI6ImNrNWdmazA4bjA2cGczanBib2F4MDNxd3EifQ.ScOIk2EYiQ9qYWBWJmjB2w'
        }).addTo(mymap);
        */
        /* https://www.ign.es/wmts/ign-base?request=GetCapabilities&service=WMTS */
        /*var ign = */
        new L.TileLayer.WMTS("https://www.ign.es/wmts/ign-base", {
          id: 'capa.base',
        	layer: "IGNBaseTodo",
        	tilematrixSet: "GoogleMapsCompatible",
        	format: "image/png",
        	attribution: "CC BY 4.0 <a target='_blank' href='http://www.scne.es/'>SCNE</a>, <a target='_blank' href='http://www.ign.es'>IGN</a>",
        	maxZoom: 20,
        	crossOrigin: true
        }).addTo(mymap);
        if (mymap.attributionControl && mymap.attributionControl.options && mymap.attributionControl.options.prefix) {
          mymap.attributionControl.options.prefix = mymap.attributionControl.options.prefix.replace(/ href=/g, ' target="_blank" href=');
        }
        L.control.sidebar('sidebar').addTo(mymap);
    } else clearMap();
    mymap.addLayer(buildLayer(geoprovincias, {
      "selected": "select[name='zona[]']",
      "id": "provincias"
    }));
    centerMap();
}

var tab_sidebar_observer = new MutationObserver(function(mutations) {
  mutations.forEach(function(mutation) {
    if (mutation.attributeName === "class") {
      elem = $(mutation.target);
      if (elem.is(".active")) {
        var ly = elem.data("layer");
        if (ly!=null) {

        }
      }
    }
  });
});


$(document).ready(function() {
/** READY: INI **/
$("div.sidebar-tabs li").each(function() {
  var li=$(this);
  var ly = li.data("layer");
  if (ly==null) {
    ly = li.parents("[data-layer]").data("layer");
    if (ly!=null) li.data("layer", ly);
  }
  if (ly!=null) tab_sidebar_observer.observe(this, {attributes: true});
});
resetMap();

$("select[name='zona[]']").change(function(){
  var aVals=$(this).val();
  var other=$("select[name='zona[]']").not(this);
  var bVals=other.eq(0).val();
  other.val(aVals);
  var df = aVals.diff(bVals);
  LAYERS.provincias.eachLayer(function(l){
    var p = l.feature.properties;
    if (p.i && df.indexOf(p.i)>=0) {
      LAYERS.provincias.resetStyle(l);
    }
  })
}).change();
/** READY: FIN **/
})

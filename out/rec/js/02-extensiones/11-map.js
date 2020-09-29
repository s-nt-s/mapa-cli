var mymap=null;
var layers={}

function selectProvincia(e) {
  e.originalEvent.preventDefault();
  e.originalEvent.stopPropagation();
  e.originalEvent.stopImmediatePropagation();
  var p = e.layer.feature.geometry.properties;
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

function layerProvincias() {
  var ly = L.geoJSON(geoprovincias, {
      style: function(f, l) {
        var fp = f.properties;
        var gp = f.geometry.properties;
        var selected=gp.i && $("select[name='zona[]']:eq(0)").val().indexOf(gp.i)>=0;
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
      var selected=p.i && zonas.val().indexOf(p.i)>=0;
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

function clearMap() {
    mymap.eachLayer(function (layer) {
        if (layer.options.id != "mapbox.streets") mymap.removeLayer(layer);
    });
}

function resetMap() {
    if (mymap==null) {
        mymap = L.map("map");
        L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
            attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
            maxZoom: 18,
            id: 'mapbox.streets',
            accessToken:  'pk.eyJ1Ijoia2lkdHVuZXJvIiwiYSI6ImNqeTBjeG8zaTAwcWYzZG9oY2N1Z3VnazgifQ.HKixpk5HNX-svbNYxYSpsw'
            //'pk.eyJ1IjoiZGF0YWlhIiwiYSI6ImNrNWdmazA4bjA2cGczanBib2F4MDNxd3EifQ.ScOIk2EYiQ9qYWBWJmjB2w'
        }).addTo(mymap);
        L.control.sidebar('sidebar').addTo(mymap);
    } else clearMap();
    mymap.addLayer(layerProvincias());
    centerMap();
}

$(document).ready(function() {
/** READY: INI **/
resetMap();

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
}).change();
/** READY: FIN **/
})

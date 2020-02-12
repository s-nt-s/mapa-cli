var sidebar_observer = new MutationObserver(function(mutations) {
  mutations.forEach(function(mutation) {
    if (mutation.attributeName === "class") {
      elem = $(mutation.target);
      if (elem.is(".collapsed")) elem.removeClass("expanded");
      if (elem.is(".expanded")) elem.css("width", "");
    }
  });
});

function joinJQ(arr) {
  var i;
  var c = arr[0];
  for (i=1; i<arr.length; i++) c=c.add(arr[i]);
  return c;
}

function showhide(ok, ko, root) {
  var ok_show = ok.joinJqData("show");
  var ko_show = ko.joinJqData("hide");
  var ok_hide = ok.joinJqData("hide");
  var ko_hide = ko.joinJqData("show");

  var hide = ko_hide.not(ok_show).add(ok_hide);
  var show = ko_show.not(ok_hide).add(ok_show);

  if (root) {
    var h = root.joinJqData("hide");
    hide = hide.add(h.not(show));
  }

  show.add(show.find(".hidebyinput")).removeClass("hidebyinput");
  show.add(show.find(".disablebyinput")).filter(".disablebyinput").prop("disabled", false).removeClass("disablebyinput");
  hide.addClass("hidebyinput");
  hide.add(hide.find("select, input, label")).filter("select, input, label").not(":disabled").filter(
    function() {
      return $(this).closest(".notDisabled").length==0;
    }
  ).prop("disabled", true).addClass("disablebyinput");

  show.add(hide).parents("[data-count]").each(function(){
    var t=$(this);
    var count = t.find(t.data("count")).length
    t.attr("class").split(/\s+/).forEach(function(c){
      if (c.startsWith("items_")) t.removeClass(c);
    });
    t.addClass("items_"+count)
  })
}

$(document).ready(function(){
  /** SIDEBAR */
  sidebar_observer.observe(document.getElementById("sidebar"), {attributes: true});
  $(".sidebar-expand").click(function(){
    var dv=$("#sidebar");
    dv.addClass("expanded");
  });
  $(".sidebar-contract").click(function(){
    var dv=$("#sidebar");
    dv.removeClass("expanded");
  });
  $("#resultado").bind("mouseenter", function() {
    if ($(".sidebar-contract").is(":visible")) return;
    var dv=$("#sidebar");
    var tb=dv.find(".tableScroll:visible");
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
  /* ONCHANGE */
  var fCg = [];
  var eq = $("*[data-show],*[data-hide]").each(function(){
    var t=$(this);
    var hide=t.data("hide");
    var show=t.data("show");
    if(hide) {
      var sel = t.find_in_parents_with_comma(hide);
      sel = sel.add(sel.getLabel());
      sel.each(function(){
        var t=$(this);
        if (t.closest(".greyinhide").length) t.addClass("greyinhide")
      });
      t.data("hide", sel.add(sel.getLabel()));
    }
    if(show) {
      var sel = t.find_in_parents_with_comma(show);
      sel = sel.add(sel.getLabel());
      sel.each(function(){
        var t=$(this);
        if (t.closest(".greyinhide").length) t.addClass("greyinhide")
      });
      t.data("show", sel);
    }
  });
  fCg[fCg.length] = eq.filter("option").closest("select").add(eq.filter("select")).change(function(){
    var t = $(this);
    var o = t.find("option");
    var ok = o.filter(":selected");
    var ko = o.not(":selected");
    showhide.apply(t, [o.filter(":selected"), o.not(":selected"),t]);
  });
  fCg[fCg.length] = eq.filter("input[type=checkbox], input[type=radio]").change(function(){
    var o = $(this);
    var nm = o.attr("name");
    if (nm) {
      var x = o.closest("fieldset").find("input[name='"+nm+"']");
      if (x.length) o = x;
    }
    showhide.apply(o, [o.filter(":checked"), o.not(":checked")]);
  });
  fCg[fCg.length] = $("*[data-desplaza]").change(function(){
    var v = parseInt(this.value, 10);
    if (Number.isNaN(v)) return;
    v = v+1;
    var e=$(this).data("desplaza");
    if (!e || !e.length) return;
    e.attr("min", v);
    var x = parseInt(e.val(), 10);
    if (Number.isNaN(x) || x<v) e.val(v).change();
  });
  fCg[fCg.length] = $("*[data-opuesto]").not("select").change(function(){
    var v = parseInt(this.value, 10);
    if (Number.isNaN(v)) return;
    var e=$(this).data("opuesto");
    if (!e || !e.length) return;
    var mx = e.attr("max");
    var mx = parseInt(mx, 10);
    if (Number.isNaN(mx)) return;
    e.val(mx-v).change();
  });
  fCg[fCg.length] = $("select[data-opuesto]").change(function(){
    var t=$(this);
    var e=t.data("opuesto");
    if (!e || !e.length) return;
    var v = t.val();
    if (typeof v == "string") v = [v];
    e.find("option").prop("disabled", false).filter(function(index, element){
      return (v.includes(element.value))
    }).prop("disabled", true).prop("selected", false);
  });
  fCg[fCg.length] = $("select[data-marcar],select[data-desmarcar]").change(function() {
    var t=$(this);
    var cond = t.data("marca-if");
    if (cond && cond.length && !cond.is(":checked")) return;
    var marcar = t.data("marcar") || $([]);
    var desmrc = t.data("desmarcar") || $([]);
    t.find("option[data-marcar]:selected").each(function(){
      marcar = marcar.add($(this).data("marcar"));
    })
    desmrc.not(marcar).filter(":checked").prop("checked", false).change();
    marcar.not(":checked").prop("checked", true).change();
  });
  fCg[fCg.length] = $("input[data-bloquear]").change(function() {
    var t=$(this);
    var blq = t.is(":checked");
    var chk = t.data("bloquear").prop("readonly", blq).filter("[type=checkbox],[type=radio]").removeAttr("onclick");
    if (blq) chk.attr("onclick", "return false;");
  });
  fCg[fCg.length] = $("*[data-fire-change]").change(function() {
    $(this).data("fire-change").change();
  });
  fCg[fCg.length] = $(".fRangos input[type=range]").bind("change input",function(){
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

  $(".multirango").each(function(){
      var rgs=$(this).find("input[type=range]");
      var tt=rgs.length-1;
      rgs.each(function(i, elem) {
          var t=$(elem);
          var _min = Number(t.attr("min"));
          var _max = Number(t.attr("max"));
          var _step= Number(t.attr("step"));
          t.data("min", _min+(_step*i));
          t.data("max", _max-(_step*(tt-i)));
     });
     rgs.bind("input",function(e){
          var v = Number(this.value);
          var i=$(this);
          var _min=i.data("min");
          var _max=i.data("max");
          if (_min>=v || _max>=v) return true;
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          this.value=(_min>v)?_min:_max;
          return false;
      })
  });
  $("input[type=range]").each(function(){
    var sp = $("span.count."+this.id);
    var i = $(this);
    i.data("span", sp);
    fCg[fCg.length] = i.bind("change input",function(){
      $(this).data("span").text(this.value);
      $(this).data("span").filter("[data-add]").each(function(){
          var t=$(this);
          var n = parseInt(t.text(), 10);
          if (!Number.isNaN(n)) t.text(n+t.data("add"));
      });
    });
  });
  $("input[type=checkbox]:not(.opcional)").map(function(){return this.name}).get().uniq().forEach(function(n){
    var i;
    var forms=$("form");
    for (i=0; i<forms.length;i++) {
      var chk=forms.eq(i).find("input[name='"+n+"']:not(.opcional)");
      if (chk.length<2) continue;
      chk.data("group", chk);
      chk.change(function(){
        var group=$(this).data("group");
        if (group.filter(":checked").length==0) {
          group.eq(0).prop("required", true);
          group[0].setCustomValidity("Debe seleccionar al menos un elemento de esta lista");
        } else {
          group.eq(0).prop("required", false);
          group[0].setCustomValidity("");
        }
      });
      fCg[fCg.length] = chk.eq(0);
    }
  });
  fCg[fCg.length] = $("select.oneGroup").change(function(){
    var t=$(this);
    var arr=t.data("slc") || [];
    if (arr.length>0 && arr.length<t.val().length) {
      var diff= t.val().diff(arr);
      var opt = t.find("option[value='"+diff[0]+"']").closest("optgroup");
      t.find("optgroup").not(opt).find("option").prop("selected", false);
    }
    t.data("slc", t.val());
  });
  joinJQ(fCg).change();
  /* VALUES */
  set_max(".ttEnd,.prTest,.yEnd", meta_info["p4_year"], meta_info["egif_year"], meta_info["egif_year"]);
  set_max(".prEnd,.yBgn", meta_info["p4_year"]-1, meta_info["egif_year"]-1, meta_info["egif_year"]-1);
  set_max(".prBng", meta_info["p4_year"]-2);
  if (meta_info["p4_year"]>meta_info["egif_year"]) {
  	$(".fTemporal,.dbToda,.dbPersonalizada,.meteo_modelo_years")
    .append("<p class='egifWarning'>(*) Tenga en cuenta que solo hay datos EGIF consolidados hasta "+meta_info["egif_year"]+", por lo tanto, cualquier rango que supere ese año trabajará con datos incompletos.</p>")
    .change();
  }
})

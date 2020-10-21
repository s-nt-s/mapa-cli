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

  show.add(show.not(".onlyMe").find(".hidebyinput")).removeClass("hidebyinput");
  show.add(show.not(".onlyMe").find(".disablebyinput")).filter(".disablebyinput").prop("disabled", false).removeClass("disablebyinput");
  hide.addClass("hidebyinput");
  hide.add(hide.not(".onlyMe").find("select, input, label")).filter("select, input, label").not(":disabled").filter(
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


function getFieldSetRangos(obj) {
  var plan_b=false;
  var i, id, v, a, l, c;
  if (obj.values!=null) {
    obj.values = [...new Set(obj.values)].sort(function(a, b){return a-b});
    obj.diff_values = obj.values.slice();
  }
  if (!obj.title) obj.title = "Rangos"
  if (!obj.idprefix) obj.idprefix = "";
  if (obj.step == null) obj.step=1;
  if (obj.min == null) obj.min = Math.ceil(obj.values[0])-obj.step;
  if (obj.max == null) obj.max = Math.ceil(obj.values[obj.values.length-1]);
  if (obj.values && obj.values.length) {
    if (obj.values[0]==obj.min) obj.values.shift();
    if (obj.values[obj.values.length-1]==obj.max) obj.values.pop();
  }
  if (obj.unidades == null) obj.unidades="unidades"
  if (obj.rangos) {
    if (typeof obj.rangos == "number") {
      obj.rangos=new Array(obj.rangos);
      for (i=0; i<obj.rangos.length;i++) obj.rangos[i]="Rango "+(i+1);
    }
    var paso = Math.floor((obj.step + obj.max - obj.min)/(obj.rangos.length+1));
    if (paso==0) plan_b=true;
    obj.values=[];
    v=obj.min+paso;
    while (v<=obj.max && obj.values.length<obj.rangos.length) {obj.values.push(v); v=v+paso}
    if (obj.values.length<obj.rangos.length) plan_b=true;
  }
  if (obj.values.length<1) plan_b=true;
  if (obj.add==null) obj.add=obj.step;
  console.log(JSON.stringify(obj, null, ' '));
  var fls=$(`<fieldset class="fRangos multirango"><legend>${obj.title}</legend></fieldset>`);
  if (obj.class) fls.addClass(obj.class);
  if (obj.globalchange) fls.addClass("globalchange");
  if (obj.pre) {
    fls.append(obj.pre);
  }
  if (plan_b) {
    if (!obj.diff_values || !obj.rangos) return null;
    var options="";
    for (i=0; i<obj.rangos.length; i++) {
      options=options+`<option value='rng${i}'>${obj.rangos[i]}</option>`
    }
    for (i=0; i<obj.diff_values.length;i++) {
      id = obj.idprefix + "rng" + i;
      v = obj.diff_values[i];
      if (obj.decimales!=null) v = spanNumber(v, obj.decimales);
      fls.append(`<p>
        <label for='${id}'><code>${v}</code> ${obj.unidades}:</label>
        <select id="${id}" name="val${obj.diff_values[i]}">
          ${options}
        </select>
        </p>
      `)
      fls.find("select:last").find("option").eq(Math.min(i, obj.rangos.length-1)).prop("selected", true);
      fls.addClass("plan_b")
    }
  } else {
    for (i=0; i<obj.values.length;i++){
      if (i==0) {
        a=obj.min;
      } else {
        a = obj.values[i-1]+obj.step;
        id = obj.idprefix + "rng" + (i-1)
        a = `<span class="count ${id}" data-add="${obj.add}">${a}</span>`
      }
      v = obj.values[i];
      id = obj.idprefix + "rng" + i;
      l = obj.rangos?obj.rangos[i]:("Rango "+(i+1));
      c = "rng_" + l.replace(/\s+/g, "_").toLowerCase();
      if (i<obj.values.length-1) {
        fls.append(`
          <p class='rng${i} ${c}'>
            <label for="${id}">${l}:</label> de ${a} a <span class="count ${id}">${v}</span> ${obj.unidades}
            <input id="${id}" name="rng${i}" min="${obj.min}" max="${obj.max}" step="${obj.step}" type="range" value="${v}" data-showvalue=".count.${id}">
          </p>
        `)
      } else {
        var pre=obj.idprefix + "rng" + (i-1);
        fls.append(`
          <p class='rng${i} ${c}'>
            <span class="label">${l}:</span> ${a} ${obj.unidades} o más
            <!--input type="hidden" id="${id}" name="rng${i}" value="${v}" class="count ${pre} pseudorange" data-add="${obj.add}"-->
            <!--input type="hidden" id="${id}" name="rng${i}" value="" class="pseudorange"-->
          </p>
        `)
      }
      //if (i<obj.values.length) fls.append("<br/>");
    }
  }
  if (obj.post) {
    fls.append(obj.post);
  }
  if (obj.globalchange) fls.on("globalchange", obj.globalchange);
  fls.data("range_config", obj);
  var div=$("<div></div>");
  div.append(fls);
  mkDataJq(div);
  mkChangeUi(div);
  return fls
}
function sort_table_by_me() {
  var t = $(this);
  var isReversed = (!t.is(".isSortedByMe") || t.is(".isReversed"));
  t.closest("tr").find("th").removeClass("isSortedByMe isReversed");
  t.addClass("isSortedByMe");
  var table = t.closest("table").find("tbody");
  var index = t.closest("tr").find("th").index(t);
  var tdsel = "td:eq("+index+")";
  var isStr = t.is(".txt");
  var i=0;
  var switching = true;
  var shouldSwitch = false;
  while (switching) {
    switching = false;
    var rows = table.find("tr");
    for (i = 0; i < (rows.length - 1); i++) {
      shouldSwitch = false;
      var rowA = rows.eq(i);
      var rowB = rows.eq(i+1);
      var x = rowA.find(tdsel).text().trim();
      var y = rowB.find(tdsel).text().trim();
      if (isStr) {
        x = x.toLowerCase();
        y = y.toLowerCase();
      } else {
        x = Number(x);
        y = Number(y);
      }
      if (x > y) {
        shouldSwitch = true;
        rowB.insertBefore(rowA);
        //table[0].insertBefore(rowB[0], rowA[0]);
        switching = true;
        break;
      }
    }
  }
  if (!isReversed) {
    t.addClass("isReversed");
    var trs = table.find("tr");
    for (i=1;i<=trs.length;i++) {
      trs.eq(trs.length-i).insertAfter(table.find("tr").last());
    }
  } else {
    t.removeClass("isReversed");
  }
}

function mkTableSortable(scope) {
  if (!scope) scope=$("body");
  scope = scope.filter("table:has(.isSortable)").add(scope.find("table:has(.isSortable)"));
  scope.find("thead th.isSortable").each(function(){
    var t=$(this);
    var cl = t.column().map(function(){ return this.textContent.trim() })
    var dif = [...new Set(cl.get())]
    if (dif.length<2) {
      t.removeClass("isSortable");
    }
  })
  scope.find("th.isSortable").click(sort_table_by_me).each(function(){
    if (this.title && this.title.trim().length) {
        this.title = this.title + " (haz click para ordenar)"
    } else {
        this.title = "Haz click para ordenar"
    }
  });
}

function mkChangeUi(scope) {
  if (!scope) scope=$("body");

  /* ONCHANGE */
  var fCg = [];
  var eq = scope.find("*[data-show],*[data-hide]").each(function(){
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
  fCg[fCg.length] = scope.find("*[data-desplaza]").change(function(){
    var v = parseInt(this.value, 10);
    if (Number.isNaN(v)) return;
    v = v+1;
    var e=$(this).data("desplaza");
    if (!e || !e.length) return;
    e.attr("min", v);
    var x = parseInt(e.val(), 10);
    if (Number.isNaN(x) || x<v) e.val(v).change();
  });
  fCg[fCg.length] = scope.find("*[data-opuesto]").not("select").change(function(){
    var v = parseInt(this.value, 10);
    if (Number.isNaN(v)) return;
    var e=$(this).data("opuesto");
    if (!e || !e.length) return;
    var mx = e.attr("max");
    var mx = parseInt(mx, 10);
    if (Number.isNaN(mx)) return;
    e.val(mx-v).change();
  });
  fCg[fCg.length] = scope.find("select[data-opuesto]").change(function(){
    var t=$(this);
    var e=t.data("opuesto");
    if (!e || !e.length) return;
    var v = t.val();
    if (typeof v == "string") v = [v];
    e.find("option").prop("disabled", false).filter(function(index, element){
      return (v.includes(element.value))
    }).prop("disabled", true).prop("selected", false);
  });
  fCg[fCg.length] = scope.find("select[data-marcar],select[data-desmarcar]").change(function() {
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
  fCg[fCg.length] = scope.find("input[data-bloquear]").change(function() {
    var t=$(this);
    var blq = t.is(":checked");
    var chk = t.data("bloquear").prop("readonly", blq).filter("[type=checkbox],[type=radio]").removeAttr("onclick");
    if (blq) chk.attr("onclick", "return false;");
  });
  fCg[fCg.length] = scope.find("*[data-fire-change]").change(function() {
    $(this).data("fire-change").change();
  });
  scope.find(".multirango").each(function(){
      var rgs=$(this).find("input[type=range]");
      var tt=rgs.length-1;
      rgs.each(function(i, elem) {
          var t=$(elem);
          var _min = Number(t.attr("min"));
          var _max = Number(t.attr("max"));
          var _step= Number(t.attr("step"));
          //t.attr("min", _min);
          //t.attr("max", _max);
          //var v = Number(this.value);
          //this.value=(_min>v)?_min:_max;
          t.data("min", _min+(_step*i));
          t.data("max", _max-(_step*(tt-i)));
          if (i>0) {
            t.data("rango_pre", rgs.eq(i-1));
          }
          if (i<rgs.length) {
            t.data("rango_sig", rgs.eq(i+1));
          }
     });
     rgs.bind("input",function(e){
          var v = Number(this.value);
          var i=$(this);
          var _min=i.data("min");
          var _max=i.data("max");
          if (v>=_min && _max>=v) return true;
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          this.value=(_min>v)?_min:_max;
          return false;
      });
  });
  fCg[fCg.length] = scope.find(".multirango input[type=range]").bind("change input",function(){
      var i=$(this).addClass("changing");
      var v = Number(this.value);
      var prevVal = i.data("prevVal");
      if (prevVal==null) prevVal = this.defaultValue;
      if (prevVal!=null) prevVal = Number(prevVal);
      i.data("prevVal", v);
      var ch=$([])
      if (prevVal==null || prevVal<v) {
        /* Desplazado a la derecha */
        var ot = i.data("rango_sig");
        if (ot) {
          var nv = v+Number(ot.attr("step"));
          if (ot.length && Number(ot.val())<nv) {
            ot.data("prevVal", ot.val());
            ot.val(nv);
            ch = ch.add(ot);
          }
        }
      }
      if (prevVal==null || prevVal>v) {
        /* Desplazado a la izquierda */
        var ot = i.data("rango_pre");
        if (ot) {
          var nv = v-Number(ot.attr("step"));
          if (ot.length && Number(ot.val())>nv) {
            ot.data("prevVal", ot.val());
            ot.val(nv)
            ch = ch.add(ot)
          }
        }
      }
      ch.change();
      i.removeClass("changing");
  })
  scope.find(".multirango.globalchange input[type=range]").bind("change",function(){
    var p = $(this).closest(".multirango");
    var r = p.find("input[type=range],.pseudorange");
    if (r.not(this).filter(".changing").length) return;
    var new_val = r.map(function(){return this.value==""?null:Number(this.value)}).get();
    var str_val = JSON.stringify(new_val);
    if (p.val() == str_val) return;
    p.val(str_val);
    p.trigger("globalchange", [new_val]);
  })
  fCg[fCg.length] = scope.find(".multirango.globalchange.plan_b select").bind("change",function(){
    var p = $(this).closest(".multirango");
    var values = p.serializeArray();
    var i, v, r;
    var new_val={}
    for (i=0; i<values.length; i++) {
      v = values[i];
      if (!v.name.startsWith("val") || !v.value.startsWith("rng")) continue;
      r = Number(v.value.substr(3));
      v = Number(v.name.substr(3));
      if (isNaN(r) || isNaN(v)) continue;
      new_val[v]=r;
    }
    var str_val = JSON.stringify(new_val);
    if (p.val() == str_val) return;
    p.val(str_val);
    p.trigger("globalchange", [new_val]);
  })

  fCg[fCg.length] = scope.find("input[type=range][data-showvalue]").bind("change input",function(){
    var sh = $(this).data("showvalue");
    sh.textval(this.value);
    sh.filter("[data-add]").each(function(){
        var t=$(this);
        var n = parseInt(t.textval(), 10);
        if (!Number.isNaN(n)) {
          n = n+t.data("add")
          t.textval(n);
        }
    });
  });
  scope.find("input[type=checkbox]:not(.opcional)").map(function(){return this.name}).get().uniq().forEach(function(n){
    var i;
    var forms=scope.find("form");
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
  fCg[fCg.length] = scope.find("select.oneGroup").change(function(){
    var t=$(this);
    var arr=t.data("slc") || [];
    if (arr.length>0 && arr.length<t.val().length) {
      var diff= t.val().diff(arr);
      var opt = t.find("option[value='"+diff[0]+"']").closest("optgroup");
      t.find("optgroup").not(opt).find("option").prop("selected", false);
    }
    t.data("slc", t.val());
  });
  fCg[fCg.length] = scope.find("select[data-min]").change(function(){
    var t=$(this);
    var m=t.data("min");
    if (t.find("option:selected").length>=m) this.setCustomValidity("");
    else this.setCustomValidity("Debe seleccionar al menos "+m+" elementos de esta lista");
  })
  joinJQ(fCg).change();
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
      resetMap();
      return false;
  })
  mkChangeUi();
  /* VALUES */
  set_max(".ttEnd,.prTest,.yEnd", meta_info.p4.max_year, meta_info.egif.max_year, meta_info.egif.max_year);
  set_max(".prEnd,.yBgn", meta_info.p4.max_year-1, meta_info.egif.max_year-1, meta_info.egif.max_year-1);
  set_max(".prBng", meta_info.p4.max_year-2);
  var wrn=$("p.egifWarning");
  if (meta_info.p4.max_year>meta_info.egif.max_year) {
    var txt = "(*) Tenga en cuenta que solo hay datos EGIF consolidados hasta "+meta_info.egif.max_year+", por lo tanto, cualquier rango que supere ese año trabajará con datos incompletos."
    wrn.text(txt).removeClass("hide");
  } else {
    txt.remove();
  }
})

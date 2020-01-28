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
  eq.filter("option").closest("select").add(eq.filter("select")).change(function(){
    var t = $(this);
    var o = t.find("option");
    var ok = o.filter(":selected");
    var ko = o.not(":selected");
    showhide.apply(t, [o.filter(":selected"), o.not(":selected"),t]);
  });
  eq.filter("input[type=checkbox], input[type=radio]").change(function(){
    var o = $(this);
    var nm = o.attr("name");
    if (nm) {
      var x = o.closest("fieldset").find("input[name='"+nm+"']");
      if (x.length) o = x;
    }
    showhide.apply(o, [o.filter(":checked"), o.not(":checked")]);
  });
  eq.change();
  $("*[data-desplaza]").change(function(){
    var v = parseInt(this.value, 10);
    if (Number.isNaN(v)) return;
    v = v+1;
    var e=$(this).data("desplaza");
    if (!e || !e.length) return;
    e.attr("min", v);
    var x = parseInt(e.val(), 10);
    if (Number.isNaN(x) || x<v) e.val(v).change();
  }).change();
  $("*[data-opuesto]").not("select").change(function(){
    var v = parseInt(this.value, 10);
    if (Number.isNaN(v)) return;
    var e=$(this).data("opuesto");
    if (!e || !e.length) return;
    var mx = e.attr("max");
    var mx = parseInt(mx, 10);
    if (Number.isNaN(mx)) return;
    e.val(mx-v).change();
  }).change();
  $("select[data-opuesto]").change(function(){
    var t=$(this);
    var e=t.data("opuesto");
    if (!e || !e.length) return;
    var v = t.val();
    if (typeof v == "string") v = [v];
    e.find("option").prop("disabled", false).filter(function(index, element){
      return (v.includes(element.value))
    }).prop("disabled", true).prop("selected", false);
  }).change();
  $("select[data-marcar],select[data-desmarcar]").change(function() {
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
  }).change();
  $("*[data-fire-change]").change(function() {
    $(this).data("fire-change").change();
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
    i.bind("change input",function(){
      $(this).data("span").text(this.value);
      $(this).data("span").filter("[data-add]").each(function(){
          var t=$(this);
          var n = parseInt(t.text(), 10);
          if (!Number.isNaN(n)) t.text(n+t.data("add"));
      });
    }).change();
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
        } else{
          group.eq(0).prop("required", false);
          group[0].setCustomValidity("");
        }
      });
      chk.eq(0).change();
    }
  });
})

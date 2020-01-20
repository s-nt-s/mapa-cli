function showhide(ok, ko) {
  var ok_show = ok.joinJqData("show");
  var ko_show = ko.joinJqData("hide");
  var ok_hide = ok.joinJqData("hide");
  var ko_hide = ko.joinJqData("show");

  var hide = ko_hide.not(ok_show).add(ok_hide);
  var show = ko_show.not(ok_hide).add(ok_show);

  show.removeClass("hidebyinput").filter(".disablebyinput").prop("disabled", false).removeClass("disablebyinput");
  hide.addClass("hidebyinput").filter("select, input, label").not(":disabled").prop("disabled", true).addClass("disablebyinput");
}

$(document).ready(function(){
  var eq = $("*[data-show],*[data-hide]").each(function(){
    var t=$(this);
    var p=t.closest("fieldset");
    var hide=t.data("hide");
    var show=t.data("show");
    if(hide) {
      var sel = p.find(hide);
      sel = sel.add(sel.getLabel());
      sel.each(function(){
        var t=$(this);
        if (t.closest(".greyinhide").length) t.addClass("greyinhide")
      });
      t.data("hide", sel.add(sel.getLabel()));
    }
    if(show) {
      var sel = p.find(show);
      sel = sel.add(sel.getLabel());
      sel.each(function(){
        var t=$(this);
        if (t.closest(".greyinhide").length) t.addClass("greyinhide")
      });
      t.data("show", sel);
    }
  });
  eq.filter("option").closest("select").change(function(){
    var t = $(this);
    var o = t.find("option");
    var ok = o.filter(":selected");
    var ko = o.not(":selected");
    showhide(o.filter(":selected"), o.not(":selected"));
  });
  eq.filter("input[type=checkbox], input[type=radio]").change(function(){
    var o = $(this);
    var nm = o.attr("name");
    if (nm) {
      var x = o.closest("fieldset").find("input[name='"+nm+"']");
      if (x.length) o = x;
    }
    showhide(o.filter(":checked"), o.not(":checked"))
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
    var marcar = t.data("marcar") || $([]);
    var desmrc = t.data("desmarcar") || $([]);
    t.find("option[data-marcar]:selected").each(function(){
      marcar = marcar.add($(this).data("marcar"));
    })
    desmrc.not(marcar).filter(":checked").prop("checked", false).change();
    marcar.not(":checked").prop("checked", true).change();
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
})

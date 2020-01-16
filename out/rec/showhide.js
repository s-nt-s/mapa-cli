function showhide(ok, ko) {
  var eq;
  var show = $([]);
  ko.filter("[data-hide]").each(function(){
    eq = $(this).data("hide");
    show = show.add(eq);
  });
  ok.filter("[data-show]").each(function(){
    eq = $(this).data("show");
    show = show.add(eq);
  });
  var hide = $([]);
  ok.filter("[data-hide]").each(function(){
    eq = $(this).data("hide");
    hide = hide.add(eq);
    show = show.not(eq);
  });
  ko.filter("[data-show]").each(function(){
    eq = $(this).data("show");
    hide = hide.add(eq);
  });
  hide = hide.not(show);
  show.removeClass("hidebyinput").find(".disablebyinput").prop("disabled", false).removeClass("disablebyinput");
  hide.addClass("hidebyinput").find("select, input, label").not(":disabled").prop("disabled", true).addClass("disablebyinput")
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
      sel.each(function(){var t=$(this); if (t.closest("greyinhide").length) t.addClass("greyinhide")});
      t.data("hide", sel.add(sel.getLabel()));
    }
    if(show) {
      var sel = p.find(show);
      sel = sel.add(sel.getLabel());
      sel.each(function(){var t=$(this); if (t.closest("greyinhide").length) t.addClass("greyinhide")});
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
})

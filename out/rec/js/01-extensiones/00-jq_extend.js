jQuery.fn.extend({
  getLabel: function() {
    var sl = this.map(function(){
      return this.id && this.id.length?"label[for='"+this.id+"']":null
    }).get().join(", ")
    return $(sl);
  },
  joinJqData: function(dt) {
    var eq = $([]);
    this.filter("[data-"+dt+"]").each(function(index, element){
      eq = eq.add($(element).data(dt));
    });
    return eq;
  },
  find_in_parents: function(sel) {
    var i, r;
    var prs = $(this).parents();
    for (i=0; i<prs.length; i++) {
      r=prs.eq(i).find(sel);
      if (r.length) return r;
    }
    return $([]);
  },
  find_in_parents_with_comma: function(sel) {
    var sels = sel.split(/,/);
    if (sels.length<2) return this.find_in_parents(sel);
    var r = $([]);
    var i;
    for (i=0;i<sels.length; i++) {
      r = r.add(this.find_in_parents(sels[i]))
    }
    return r;
  },
  textval: function(val) {
    var isVal="input,select"
    if (val==null) {
      var i = this.eq(0);
      if (i.is(isVal)) return i.val();
      return i.text();
    }
    var i=this.filter(isVal);
    i.val(val);
    this.not(i).text(val);
    return this;
  },
  column: function() {
    if (this.length!=1 && !this.is("th")) return null;
    var index=this.closest("tr").find("th").index(this);
    return this.closest("table").find("tbody tr").find("td:eq("+index+")");
  },
  reverse: Array.prototype.reverse,
});

function mkDataJq(scope) {
  if (!scope) scope=$("body");
  ["desplaza", "opuesto", "obligatorio", "opcional", "marcar", "desmarcar", "fire-change", "marca-if", "bloquear", "showvalue"].forEach(function(k){
    var eq = scope.find("*[data-"+k+"]");
    var i, t, target;
    for (i=0; i<eq.length; i++) {
      t = eq.eq(i);
      var sel=t.data(k);
      if (k=="showvalue") {
        var mr = t.closest(".multirango");
        if (mr.length>0) {
          target = mr.find(sel);
          t.data(k, target);
          continue;
        }
      }
      target = t.find_in_parents_with_comma(sel);
      t.data(k, target);
    }
  })
}

$(document).ready(function(){
  mkDataJq();
});

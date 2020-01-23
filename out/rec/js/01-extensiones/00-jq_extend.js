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
  }
});

$(document).ready(function(){
  ["desplaza", "opuesto", "obligatorio", "opcional", "marcar", "desmarcar", "fire-change", "marca-if"].forEach(function(k){
    var eq = $("*[data-"+k+"]");
    var i, t;
    for (i=0; i<eq.length; i++) {
      t = eq.eq(i);
      var sel=t.data(k);
      var target = t.find_in_parents(sel);
      t.data(k, target);
    }
  })
});

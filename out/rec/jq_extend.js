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
  }
});

$(document).ready(function(){
  ["desplaza", "opuesto", "obligatorio", "opcional", "marcar", "desmarcar"].forEach(function(k){
    var eq = $("*[data-"+k+"]");
    var i, t;
    for (i=0; i<eq.length; i++) {
      t = eq.eq(i);
      var sel=t.data(k);
      var target = t.closest("fieldset").find(sel);
      if (target.length==0) target = t.closest("form").find(sel);
      t.data(k, target);
    }
  })
});

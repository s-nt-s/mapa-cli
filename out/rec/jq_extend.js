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

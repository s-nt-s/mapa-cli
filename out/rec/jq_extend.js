jQuery.fn.extend({
  getLabel: function() {
    var sl = this.map(function(){
      return this.id && this.id.length?"label[for='"+this.id+"']":null
    }).get().join(", ")
    return $(sl);
  }
});

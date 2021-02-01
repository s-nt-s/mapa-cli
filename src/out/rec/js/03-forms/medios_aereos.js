$(document).ready(function(){
  $("#medios-aereos select[name='zona[]']").change(function() {
    var slc = $("#medios-aereos .predictor_zona");
    var val = slc.val()
    slc.find("option").show();
    var vals = $(this).val();
    if (vals.indexOf("ESP")==-1) {
      slc.find("option").filter(function(){return this.value && vals.indexOf(this.value)==-1}).hide();
      if (vals.indexOf(val)==-1) {
        slc.val("").change();
      }
    }
  }).change();
})

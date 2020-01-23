$(document).ready(function(){
  var submit = $("input[type='submit']");
  submit.filter("[data-obligatorio]").click(function() {
    var t=$(this);
    var e=t.data("obligatorio");
    if (!e || !e.length) return;
    e.prop("required", true);
  })
  submit.filter("[data-opcional]").click(function() {
    var t=$(this);
    var e=t.data("opcional");
    if (!e || !e.length) return;
    e.prop("required", false);
  })
  submit.click(function(){
    this.form.__submited=this;
  });
  $("form").submit(function(e) {
      e.preventDefault(); // avoid to execute the actual submit of the form.
      var form = $(this);
      //if (this.__submited)
      var sb = form.find("input[type=submit]").attr("disabled", true)
      if (this.__submited) $(this.__submited).val("Cargando...");
      else sb.val("Cargando...");
      var resultado=$("#resultado");
      resultado.find(".content").html("");
      resultado.find("#loading").show();
      var tResultado = $("#tResultado");
      tResultado.text(tResultado.data("default"))
      var i = $("#iResultado").show().find("i");
      if (!$("#resultado .content").is(":visible")) i.click();
      var action = form.attr('action');
      if (this.__submited && this.__submited.formAction && document.location.href!=this.__submited.formAction) action=this.__submited.formAction;
      var url = action;
      var store_in = form.find("input.store_in");
      var _url=null;
      if (store_in.length) {
        store_in.val("");
        var fn = form.serialize()+" "+action;
        fn = fn.hashCode().toString();
        fn = form.attr("id") + "_" + fn + ".json";
        //store_in.val(fn);
        _url = window.location.pathname+"rec/api/"+fn;
        store_in.val(_url);
      }
      var settings = {
        type: "POST",
        url: url,
        data: form.serialize(), // serializes the form's elements.
        form: form,
        submited: this.__submited,
        success: function(data, textStatus, jqXHR) {
            if (typeof data == "object") {
               if (data["__timestamp__"]) {
                 var d=new Date(0)
                 d.setUTCSeconds(data["__timestamp__"]);
                 console.log("Recuperado json de "+getStrFecha(d)+" [hace "+intervalo(d, true)+"]");
              }
              if (data["__timespent__"]) {
                console.log("Timepo de servidor: "+seconds_to_string(data["__timespent__"]));
              }
            }
            this.form.data("submitted").apply(this, arguments);
            var btn = this.form.find("input[type=submit]");
            btn.prop("disabled", false).each(function(){this.value=$(this).data("defval");});
        }
      };
      my_ajax(_url, settings);
  });
});

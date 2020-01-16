Number.prototype.pad = function(size) {
  if (size==null) size=2;
  var s = String(this);
  while (s.length < size) {s = "0" + s;}
  return s;
}
Array.prototype.uniq = function(){
  return this.filter(
      function(a){return !this[a] ? this[a] = true : false;}, {}
  );
}
Array.prototype.del = function(e) {
  var i = this.indexOf(e);
  if (i>=0) delete this[i];
  return this;
}
Array.prototype.diff = function(o) {
  var i, v;
  var arr=[];
  for (i=0; i<this.length;i++) {
    v = this[i];
    if (o.indexOf(v)==-1) arr.push(v);
  }
  for (i=0; i<o.length;i++) {
    v = o[i];
    if (this.indexOf(v)==-1) arr.push(v);
  }
  return arr;
}

function getStrFecha(dt) {
  if (dt==null) dt =  new Date();
  var s = dt.toLocaleDateString("es-ES", {month: '2-digit', year: 'numeric', day: '2-digit', hour:'2-digit',minute:'2-digit'});
  s = s.replace(/[^ \d:\/\._]+/g, "");
  return s;
}
function getPthFecha(dt) {
  if (dt==null) dt =  new Date();
  var s = dt.getFullYear() + "." + dt.getMonth().pad(2) + "." + dt.getDate().pad(2)+"_"+dt.getHours().pad(2)+"."+dt.getMinutes().pad(2);
  s = s.replace(/[^ \d:\/\._]+/g, "");
  return s;
}


function objForm(f) {
  if (!f) f=$("form:visible");
  var obj={};
  var unindexed_array = f.serializeArray();
  $.map(unindexed_array, function(n, i){
    var name = n['name'];
    var value = n['value'];
    var nv = parseInt(value, 10);
    if (!Number.isNaN(nv)) value = nv;
    if (name.endsWith("[]")) {
      //name = name.substr(0, name.length-2);
      var ar = obj[name] || [];
      ar.push(value);
      obj[name]=ar;
    } else {
      obj[name] = value;
    }
  });
  return obj;
}

function toWin(txt) {
  txt = txt.trim();
  txt = txt.replace(/\r\n/g, "\n");
  txt = txt.replace(/\n\n\n+/g, "\n\n");
  txt = txt.replace(/\n/g, "\r\n");
  return txt;
}

$(document).ready(function() {
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
    $("input[type=checkbox]").map(function(){return this.name}).get().uniq().forEach(function(n){
      var i;
      var forms=$("form");
      for (i=0; i<forms.length;i++) {
        var chk=forms.eq(i).find("input[name='"+n+"']");
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
});

function ieDownloadEvent() {
  if (!window.top.navigator.msSaveOrOpenBlob) return;
  var re_base64 = /^data:(.+);base64,(.+)/;
  $("a").not(".ieDwn").filter(function(){
    var name = this.download;
    if (!name) return false;
    var file = this.href;
    var mtch = file.match(re_base64);
    if (!mtch) return false;
    var cnty = mtch[1];
    var bs64 = mtch[2];
    file = atob(bs64);
    const byteNumbers = new Array(file.length);
    for (let i = 0; i < file.length; i++) {
        byteNumbers[i] = file.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], {type: cnty});
    $(this).data("blob", blob);
    return true;
  }).click(function(e){
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    window.top.navigator.msSaveOrOpenBlob($(this).data("blob"), this.download);
  }).addClass("ieDwn");
}

function isUrlOnline(url, status, fecha) {
  if (status == null) status = 200;
  if (fecha == null) {
    fecha = new Date();
    fecha.setHours(0,0,0,0);
  }
  var http = new XMLHttpRequest();
  http.open('HEAD', url, false);
  http.send();
  if (http.status != status) {
    console.log(http.status+" "+url);
    return false;
  }
  var dtC = http.getResponseHeader("date");
  var dtM = http.getResponseHeader("last-modified");
  var dtC = dtC?new Date(dtC):null;
  var dtM = dtM?new Date(dtM):null;
  if (dtC>=fecha || dtM>=fecha) return true;
  console.log(dtC+"\n"+dtM+"\n"+url);
  return false;
}

String.prototype.hashCode = function() {
  var hash = 0, i, chr;
  if (this.length === 0) return hash;
  for (i = 0; i < this.length; i++) {
    chr   = this.charCodeAt(i);
    hash  = ((hash << 5) - hash) + chr;
    hash |= 0; // Convert to 32bit integer
  }
  return hash;
};

TimeoutIDS={}

class WhenUrlExist {
    constructor(id, url, time) {
        if (time == null) time = 5000;
        this.id = id;
        this.time = time;
        this.opt = null;
        this.intentos = 1;
        this.start = new Date();
        this.url = url;
        if (this.url.endsWith(".json")) {
          var fecha = new Date();
          fecha.setHours(0,0,0,0);
          this.url=this.url+"?dt="+fecha.getTime();
        }
        this.opt={
          url: this.url,
          type: "GET",
          dataType: "json",
          when_url_exist: this,
          data: null
        }
        this.clear();
    };
    fire(opt) {
      console.log(this.intentos+" "+this.id+" -> "+this.tiempo(true))
      if (opt!=null) this.opt = Object.assign({}, opt, this.opt);
      if (isUrlOnline(this.url)) {
        return $.ajax(this.opt).always(function(){
          this.when_url_exist.clear();
        });
      } else {
        this.intentos = this.intentos + 1;
        var tt = this.intentos<2?(this.time*2):this.time;
        TimeoutIDS[this.id] = setTimeout(function(a) {a.fire();}, tt, this);
      }
      return null;
    };
    clear() {
      if (TimeoutIDS[this.id]) clearTimeout(TimeoutIDS[this.id]);
    };
    tiempo(to_string) {
      var timeDiff = new Date() - this.start;
      timeDiff /= 1000;
      var seconds = Math.round(timeDiff);
      if (!to_string) return seconds;
      if (seconds==1) return "un segundo";
      if (seconds<60) return seconds+" segundos"
      var m = Math.floor(seconds/60);
      var s = seconds - (m*60);
      if (m==1) m="un minuto";
      else m=m+" minutos";
      if (s<2) return m;
      return m+" y "+s+" segundos";
    }
}

function my_ajax(url, opt) {
  if (!url) return $.ajax(opt);
  opt.when_url_exist = new WhenUrlExist(opt.form.attr("id"), url, null);
  if (isUrlOnline(opt.when_url_exist.url)) return opt.when_url_exist.fire(opt);
  return $.ajax(opt).fail(function(data, textStatus, jqXHR) {
    //if (textStatus!="timeout") return;
    if (this.when_url_exist) {
      this.when_url_exist.fire(this);
    }
  });
}

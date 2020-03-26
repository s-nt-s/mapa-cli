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

function toUrl(url, txt, title) {
  var s_url=url.split(/:\/\//)[1];
  if (!txt) txt = s_url;
  if (title==null) title = " title='"+s_url+"'";
  return `<a href="${url}"${title}>${txt}</a>`;
}

function setIfNull(e, a, v) {
	if (v && !e.attr(a)) e.attr(a, v);
}

function set_max(selector, maximum, value, placeholder) {
  var es = $(selector);
  var i,e;
  for (i=0;i<es.length;i++) {
    e = es.eq(i);
    setIfNull(e, "placeholder", placeholder);
    setIfNull(e, "value", value);
    setIfNull(e, "max", maximum);
  }
}

function getStrFecha(dt) {
  if (dt==null) dt = new Date();
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

function seconds_to_string(seconds) {
  seconds = Math.round(seconds);
  if (seconds==1) return "un segundo";
  if (seconds<60) return seconds+" segundos"
  var m = Math.floor(seconds/60);
  var s = seconds - (m*60);
  var h = "";
  if (m>=60) {
      h = Math.floor(m/60);
      m = m - (h*60);
      if (h==1) h="1 hora y ";
      else h = h+"h y ";
  }
  if (m==1) m="un minuto";
  else m=m+" minutos";
  if (s<2) return h+m;
  return h+m+" y "+s+" segundos";
}

function intervalo(start, to_string) {
  var timeDiff = new Date() - start;
  timeDiff /= 1000;
  var seconds = Math.round(timeDiff);
  if (!to_string) return seconds;
  return seconds_to_string(seconds);
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

function isUrlOnline(url, status, fecha, method) {
  if (method == null) method = 'HEAD';
  if (status == null) status = [200];
  else if (!Array.isArray(status)) status = [status];
  if (fecha == null) {
    fecha = new Date();
    fecha.setHours(0,0,0,0);
  }
  var http = new XMLHttpRequest();
  /*
  if (url.indexOf(".json")) {
      if (url.indexOf("?")) url = url + "&rd="+Math.random();
      else url = url + "?rd="+Math.random();
  }
  */
  http.open(method, url, false);
  http.setRequestHeader('cache-control', 'no-cache, no-store, must-revalidate, post-check=0, pre-check=0');
  http.setRequestHeader('cache-control', 'max-age=0');
  http.send();
  if (!status.includes(http.status)) {
    console.log(http.status+" "+method+" "+url);
    return http.status;
  }
  var dtC = http.getResponseHeader("date");
  var dtM = http.getResponseHeader("last-modified");
  dtC = dtC?new Date(dtC):null;
  dtM = dtM?new Date(dtM):null;
  //if (dtC>=fecha || dtM>=fecha) return true;
  if (dtM>=fecha) return http.status;
  if (dtC) dtC = getStrFecha(dtC);
  if (dtM) dtM = getStrFecha(dtM);
  console.log("date:          "+dtC+"\nlast-modified: "+dtM+"\n"+method+" "+url);
  return -http.status;
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

String.prototype.toCapitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

TimeoutIDS={}

class WhenUrlExist {
    constructor(id, url, time, from_enpoint) {
        if (time == null) time = 5000;
        this.id = id;
        this.time = time;
        this.opt = null;
        this.intentos = 1;
        this.start = new Date();
        this.url = url;
        this.status = null;
        this.ok_status = [200, 304];
        if (url.startsWith("/")) url = document.location.origin + url;
        console.log("WhenUrlExist para "+url);
        /*
        if (this.url.endsWith(".json")) {
          var fecha = new Date();
          fecha.setHours(0,0,0,0);
          this.url=this.url+"?dt="+fecha.getTime();
        }
        */
        this.opt={
          url: this.url,
          type: "GET",
          dataType: "json",
          when_url_exist: this,
          data: null,
          from_enpoint: from_enpoint
        }
        this.clear();
    };
    fire(opt) {
      console.log(this.intentos+" "+this.id+" -> "+this.tiempo(true))
      if (opt!=null) this.opt = Object.assign({}, opt, this.opt);
      if (this.testUrl()) {
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
      return intervalo(this.start, to_string);
    };
    testUrl() {
      var method = null; //this.status == 404?'GET':'HEAD';
      this.status = isUrlOnline(this.url, this.ok_status, null, method);
      return this.ok_status.includes(this.status);
    };
}

function my_ajax(url, opt) {
  if (!url) return $.ajax(opt);
  opt.when_url_exist = new WhenUrlExist(opt.form.attr("id"), url, null, opt.url);
  if (opt.when_url_exist.testUrl()) return opt.when_url_exist.fire(opt);
  return $.ajax(opt).fail(function(data, textStatus, jqXHR) {
    //if (textStatus!="timeout") return;
    if (this.when_url_exist) {
      this.when_url_exist.fire(this);
    }
  });
}


function spanNumber(v, decimales) {
  if (v==null || v==="") return "";
  if (decimales != null) {
    var d = Math.pow(10, decimales)
    v = Math.round(v*d)/d;
  }
  var sig="sig_cero";
  if(v<0) sig="neg";
  else if (v>0) sig="pos";
  v=v.toString();
  var sp = v.split(/\./);
  var dc = sp.length==2?sp[1].length:0;
  var en = sp[0].length;
  v = `<span class='bfr'></span><span class="nm en${en} dc${dc} ${sig}">${v}</span><span class='aft'></span>`
  return v;
}

function buildTable(table_class, row_size, cels) {
  var t = `
    <table class='${table_class}'>
    <thead>
      <tr>`;
  var i, th, td, txt;
  for (i=0; i<cels.length; i++) {
    td = cels[i];
    if (typeof td != "object") {
      txt = td;
      td = {}
      if (i>=row_size) {
          th = cels[i % row_size];
          if (typeof th == "object") td = th;
      }
      td.txt = txt;
      td.title = null;
    }
    if (i == row_size) {
      t = t + `
      </tr>
    </thead>
    <tbody>
      <tr>`;
    }
    t = t + "\n       ";
    if (i<row_size) {
      t = t + `<th class='${td.class || ''}' title='${td.title || ''}'>${td.txt}</th>`;
    } else {
      t = t + `<td class='${td.class || ''}' title='${td.title || ''}'>${td.txt}</td>`;
    }
    if (((i+1) % row_size == 0) && !(i==0 || i == row_size)) {
      t = t + `
      </tr>`;
    }
  }
  if (cels.length>row_size) {
    t = t + `
    <tbody>
  </table>`;
  }
  t = t.replace(/\s*class=''/g, "");
  return t;
}

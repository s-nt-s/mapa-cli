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

String.prototype.toCapitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
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

function logHttp(url, http) {
  var dtC = http.getResponseHeader("date");
  var dtM = http.getResponseHeader("last-modified");
  dtC = dtC?new Date(dtC):null;
  dtM = dtM?new Date(dtM):null;
  //if (dtC>=fecha || dtM>=fecha) return true;
  if (dtM>=fecha) return http.status;
  if (dtC) dtC = getStrFecha(dtC);
  if (dtM) dtM = getStrFecha(dtM);
  console.log(url);
  console.log("date:          "+dtC+"\nlast-modified: "+dtM+"\n"+method+" "+url);
}

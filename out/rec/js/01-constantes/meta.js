var meta_info={};
$.getJSON("https://dataia.mapa.gob.es/egif/meta.json", function(
  data,
  status,
  http
) {
  meta_info = data;
  logHttp(this.url, http);
});

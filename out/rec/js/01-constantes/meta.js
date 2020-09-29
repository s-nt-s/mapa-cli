var meta_info={};
/*
$.getJSON("https://dataia.mapa.gob.es/egif/meta.json", function(
  data,
  status,
  http
) {
  meta_info = data;
  logHttp(this.url, http);
});
*/
$.ajax({
  url: "https://dataia.mapa.gob.es/egif/meta.json",
  dataType: 'json',
  async: false,
  success: function(
    data,
    status,
    http
  ) {
    meta_info = data;
    logHttp(this.url, http);
  }
});

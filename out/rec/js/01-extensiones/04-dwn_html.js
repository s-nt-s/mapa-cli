function html_to_md(elms, opt) {
  if (!opt) opt={};
  if (opt.level==null) opt.level=0;
  if (typeof elms == "string") elms = $("<div>"+elms+"</div>").find(">*");
  elms = elms.clone().not(".avoidMd");
  elms.find(".avoidMd").remove();
  var i,c, d;
  var html='';
  elms.each(function(){
    html = html + "\n";
    var tag = this.tagName.toLowerCase();
    if (tag=="p") {
        html = html + "\n\n" + this.textContent.trim()+"\n\n";
    } else if (tag[0]=="h") {
      html = html + "\n";
      for (i=0; i<parseInt(tag[1],10);i++) html = html + "#";
      html = html + " " + this.textContent.trim()+"\n";
    } else if (tag == "ul" || tag == "ol") {
      var t = $(this).clone()
      html = html + html_to_md(t.find(">li"), {level:opt.level})
      if (opt.level==0) html = html + "\n";
    } else if (tag == "li") {
      var t = $(this).clone()
      t.find("ul,ol").remove()
      for (i=0; i<opt.level*4;i++) html = html + " ";
      html = html + "* "+t.text().trim();
      var ul = $(this).find(">ul, >ol")
      if (ul.length>0) html = html + "\n" + html_to_md(ul, {level:opt.level+1})
    } else if (tag == "table") {
      html = html + "\n";
      var wdt=null;
      var t = $(this);
      var isDosDecimales = t.is(".dosDecimales");
      var alg = t.find(".txt").length>0 || t.is(".numbers");
      var trs = t.find("tr");
      for (i=0; i<trs.length; i++) {
        var _wdt= trs.eq(i).find("td,th").map(function(j, e){return e.textContent.trim().length})
        if (!wdt) wdt=_wdt;
        else {
          for (c=0;c<wdt.length;c++) wdt[c]=Math.max(wdt[c],_wdt[c]);
        }
      }
      var fTd=false;
      for (i=0; i<trs.length; i++) {
        html = html + "|";
        var tds = trs.eq(i).find("td,th");
        if (!fTd && i>0 && tds.filter("td").length) {
          fTd=true;
          for (c=0;c<tds.length;c++) {
            var txt = "-";
            while (txt.length<wdt[c]) {
              if (alg && !tds.eq(c).is(".txt")) txt = "-"+txt;
              else txt = txt+"-";
            }
            html = html + "-" + txt+"-|";
          }
          html = html + "\n|";
        }
        for (c=0;c<tds.length;c++) {
          var td = tds.eq(c);
          var txt = td.text().trim();
          if (isDosDecimales && c==tds.length-1) {
            if (td.find(".dc1").length) txt = txt + " ";
            else if (td.find(".dc0").length) txt = txt + "   ";
          }
          while (txt.length<wdt[c]) {
            if (alg && !td.is(".txt")) txt = " "+txt;
            else txt = txt+" ";
          }
          html = html + " " + txt+" |";
        }
        html = html + "\n";
      }

      html = html + "\n";
    }
  })
  html = html.replace(/^\n+|\n+$/g, "");
  return html;
}

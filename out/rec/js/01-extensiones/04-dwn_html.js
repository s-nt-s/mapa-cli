function html_to_md(elms, opt) {
  if (!opt) opt={};
  if (opt.level==null) opt.level=0;
  if (typeof elms == "string") elms = $("<div>"+elms+"</div>").find(">*");
  elms = elms.clone().not(".avoidMd");
  elms.find(".avoidMd, strike").remove();
  var i,c,d,j;
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
      var dosDecimales = t.find(".dosDecimales");
      if (t.is(".dosDecimales")) dosDecimales = dosDecimales.add(t);
      dosDecimales.find(".dc1").each(function(){
        this.textContent = this.textContent.trim()+"_";
      })
      dosDecimales.find(".dc0").each(function(){
        this.textContent = this.textContent.trim()+"___";
      })
      var alg = t.find(".txt").length>0 || t.is(".numbers");
      var trs = t.find("tr");
      var _tr = trs.filter(function(){return $(this).find("*[colspan]").length==0});
      for (i=0; i<_tr.length; i++) {
        var _wdt= _tr.eq(i).find("td,th").map(function(j, e){return e.textContent.trim().length})
        if (!wdt) wdt=_wdt;
        else {
          for (c=0;c<wdt.length;c++) wdt[c]=Math.max(wdt[c],_wdt[c]);
        }
      }
      for (i=0; i<trs.length; i++) {
        html = html + "|";
        var tds = trs.eq(i).find("td,th");
        var divisorA = "";
        var divisorB = "";
        var cur = trs.eq(i).closest("tbody,thead,tfoot").prop("tagName").toLowerCase();
        if (i>0 && cur=="tbody") {
          var pre = trs.eq(i-1).closest("tbody,thead,tfoot").prop("tagName");
          var nex = trs.eq(i+1).closest("tbody,thead,tfoot").prop("tagName");
          if (pre) pre=pre.toLowerCase();
          if (nex) nex=nex.toLowerCase();
          var divisor="";
          for (c=0;c<tds.length;c++) {
            var txt = "-";
            while (txt.length<wdt[c]) txt = txt+"-";
            divisor = divisor + "-" + txt + "-|";
          }
          if (pre!="tbody") divisorA=divisor+ "\n|";
          if (nex!="tbody") divisorB="|"+divisor+ "\n";

        }
        if (divisorA.length) html = html + divisorA;
        var desfase = 0;
        for (c=0;c<tds.length;c++) {
          var td = tds.eq(c);
          var txt = td.text().trim();
          var td_wdt=wdt[desfase+c];
          var colspan = parseInt(td.attr("colspan"));
          if (!isNaN(colspan) && colspan>1) {
            for(j=1; j<colspan; j++) td_wdt = td_wdt + wdt[desfase+c+j]+3;
            desfase = desfase + colspan -1;
          }
          while (txt.length<td_wdt) {
            if (td.css("text-align") == "center") {
              if (txt.length % 2) txt = " "+txt;
              else txt = txt+" ";
            } else {
              if (alg && !td.is(".txt")) txt = " "+txt;
              else txt = txt+" ";
            }
          }
          html = html + " " + txt.replace(/_/g, " ")+" |";
        }
        html = html + "\n";
        if (divisorB.length) html = html + divisorB;
      }
      html = html + "\n";
    }
  })
  html = html.replace(/^\n+|\n+$/g, "");
  return html;
}

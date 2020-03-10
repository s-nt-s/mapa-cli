var myweb = window.location.href;
myweb = myweb.substr(document.location.protocol.length+2)
if (myweb.endsWith("/")) myweb = myweb.substr(0, myweb.length-1);

var myroot = window.location.href;
if (!myroot.endsWith("/")) myroot = myroot+"/";

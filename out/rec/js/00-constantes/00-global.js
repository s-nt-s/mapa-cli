var myweb = window.location.href;

var tail = myweb.split(/\//);
tail = tail[tail.length-1];
if (tail.length>0 && tail.indexOf(".")==-1) {
    window.location.href = window.location.href + "/";
}

if (myweb.endsWith("/index.html")) myweb = myweb.substr(0, myweb.length-11);
myweb = myweb.substr(document.location.protocol.length+2)
if (myweb.endsWith("/")) myweb = myweb.substr(0, myweb.length-1);

var myroot = window.location.href;
if (myroot.endsWith("/index.html")) myroot = myroot.substr(0, myweb.length-10);
if (!myroot.endsWith("/")) myroot = myroot+"/";

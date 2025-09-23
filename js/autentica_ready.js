(()=>{
    if (window.document.readyState !== "complete") return false;
    if (document.querySelector("img[src$='ajax-loader.gif']") != null) return false;
    if (document.querySelector("#username,#password,#submitAutentica,#grabar,#modal-btn-si,#btnTypeAuthentication,p") == null) return false;
    const slc = [
        "#btnTypeAuthentication[value='lvlThree']",
        "#btnTypeAuthentication[value='lvlOne']",
    ];
    let n;
    for (let i = 0; i < slc.length; i++) {
        n = document.querySelector(slc[i]);
        if (n != null) {
            n.click();
            return false;
        }
    }
    return true;
})();
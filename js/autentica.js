
(() => {
    const slc = [
        "#btnTypeAuthentication[value='lvlThree']",
        "#btnTypeAuthentication[value='lvlOne']",
        "#loginAutentica a"
    ];
    let n;
    for (let i = 0; i < slc.length; i++) {
        n = document.querySelector(slc[i]);
        if (n != null) {
            n.click();
            return;
        }
    }
})();
var basepath = document.currentScript.src.replace("menu.js", "");
if(false){ //"IBC" in uapi.KeyValueStringParserJs() || "NAB" in uapi.KeyValueStringParserJs()){
    (function(){
        var demos = {
            "USP Features": basepath + "../features/",
            "CPIX": basepath + "../cpix/",
            "Keyrotation": basepath+ "../keyrotation/",
            "SCTE 35": basepath + "../scte35/",
            "nPVR": basepath + "../npvr/"
        }
        var a = [];
        for(k in demos){
            var cs = "";
            if(location.href.indexOf(uapi.absUrl(demos[k])) != -1)
                cs = " active";
            a.push(`<li class="nav-item"><a class="nav-link${cs}" href="${demos[k]}">${k}</a></li>`)
        }
        uapi.write(`
        <ul class="navbar-nav ml-auto">             
            ${a.join("\n")}
        </ul>
        `);
    })();
}else
    uapi.write(`
    <ul class="navbar-nav ml-auto">             
        <li class="nav-item"><a class="nav-link" href="http://docs.unified-streaming.com/documentation/package/index.html">Packager</a></li>
        <li class="nav-item"><a class="nav-link" href="http://docs.unified-streaming.com/documentation/vod/index.html">VOD</a></li>
        <li class="nav-item"><a class="nav-link" href="http://docs.unified-streaming.com/documentation/live/index.html">LIVE</a></li>
        <li class="nav-item"><a class="nav-link" href="http://docs.unified-streaming.com/documentation/drm/index.html">DRM</a></li>
        <li class="nav-item"><a class="nav-link" href="http://docs.unified-streaming.com/documentation/capture/live-to-vod.html">LIVE to VOD</a></li>
        <li class="nav-item"><a class="nav-link" href="http://docs.unified-streaming.com/documentation/remix/index.html">Remix</a></li>
    </ul>
    `);
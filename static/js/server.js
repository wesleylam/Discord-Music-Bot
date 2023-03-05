function fetchServer(showingVid, setShowingVid) { 
    console.log(showingVid)
    fetch(fetchServerUrl, {
        "method": "POST",
        "body": showingVid
    })
    .then(response => response.json())
    .then(data => {
        // data is a parsed JSON object
        console.log("DATA")
        console.log(data)
        if (!data.playing) {
            document.getElementById("nowplaying_h1").innerHTML = "Not Playing";
            document.getElementById("playing_div").hidden = true;
        }

        if (data.needUpdate) {
            document.getElementById("nowplaying_h1").innerHTML = "Now Playing";
            document.getElementById("playing_div").hidden = false;
            document.getElementById("title_h2").innerHTML = data.songData.title;
            document.getElementById("vid_iframe").src = data.songData.embedUrl;
            document.getElementById("info_div").innerHTML = data.queue.join("\n");
            // update showing vid to prevent excessive updates
            setShowingVid(data.songData.vID)
        }
    })
}

function onClickAction(actionId) {
    fetch(actionUrl, 
        { 
            "method": "POST",
            "body": actionId
        }
        )
        .then(response => response.json())
        .then(data => {
            // data is a parsed JSON object
            console.log(actionId)
            console.log(data)
            document.getElementById(actionId).disabled = false;
        })
}
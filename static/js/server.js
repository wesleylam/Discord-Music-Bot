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

            // SONG INFO
            document.getElementById("info_div").innerHTML = '';
            document.getElementById("info_div").append(data.songData.djable);
            document.getElementById("info_div").append(data.songData.duration);
            
            // QUEUE INFO
            document.getElementById("queue_div").innerHTML = '';
            let i = 0
            data.queue.forEach(s => {
                i += 1;
                document.getElementById("queue_div").append(s);
                document.getElementById("queue_div").append(document.createElement('br'));
            });
            if (i == 0) {
                document.getElementById("queue_div").append("Empty queue...");
            }
            
            // update showing vid to prevent excessive updates
            setShowingVid(data.songData.vID)
        }
    })
}

function onClickAction(actionId) {
    fetch(actionUrl, 
        { 
            "method": "POST",
            // will decoded as text, might need better encoding
            "body": [actionId, showingVid]
        }
        )
        .then(response => response.json())
        .then(data => {
            // data is a parsed JSON object
            console.log(actionId)
            console.log(data)
            document.getElementById('response').innerHTML = data.response
            document.getElementById(actionId).disabled = false;
        })
}
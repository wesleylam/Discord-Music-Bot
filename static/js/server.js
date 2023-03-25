function showNotPlaying() {
    document.getElementById("nowplaying_h1").innerHTML = "Not Playing";
    document.getElementById("playbox").hidden = true;
    document.getElementById("join").classList.remove("hidden");
}

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
            showNotPlaying();
        } else {
            document.getElementById("join").classList.add("hidden");
        }

        if (data.needUpdate) {
            document.getElementById("nowplaying_h1").innerHTML = "Now Playing";
            document.getElementById("playbox").hidden = false;
            document.getElementById("title_h2").innerHTML = data.songData.Title;
            document.getElementById("vid_iframe").src = data.songData.embedUrl;

            // SONG INFO
            const info_table = document.getElementById("info_table")
            info_table.innerHTML = '';
            info_table.append(data.songData.vID);
            info_table.append(document.createElement('br'));
            info_table.append(data.songData.Title);
            info_table.append(document.createElement('br'));
            info_table.append(data.songData.DJable);
            
            if (data.songData.DJable === true) {
                document.getElementById("djable").classList.add("hidden");
                document.getElementById("notdjable").classList.remove("hidden");
                document.getElementById("notdjable__skip").classList.remove("hidden");
            } else {
                document.getElementById("djable").classList.remove("hidden");
                document.getElementById("notdjable").classList.add("hidden");
                document.getElementById("notdjable__skip").classList.add("hidden");
            }
            info_table.append(document.createElement('br'));
            info_table.append(data.songData.Duration);
            
            // QUEUE INFO
            document.getElementById("queue_list").innerHTML = '';
            let i = 0
            data.queue.forEach(s => {
                i += 1;
                document.getElementById("queue_list").append(s);
                document.getElementById("queue_list").append(document.createElement('br'));
            });
            if (i == 0) {
                document.getElementById("queue_div").hidden = true;
            } else {
                document.getElementById("queue_div").hidden = false;
            }
            
            // update showing vid to prevent excessive updates
            setShowingVid(data.songData.vID)
        }
    })
}

function onClickAction(actionId) {
    if (actionId === "join") {
        // or add loading
        document.getElementById('response').innerHTML = "JOINING"
    }

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
            console.log("ONCLICK REPLY")
            console.log(actionId)
            console.log(data)
            document.getElementById('response').innerHTML = data.response
            document.getElementById(actionId).disabled = false;
            doFetchServer()
        })
}
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

        if (data.needUpdate) {
            document.getElementById("title_h2").innerHTML = data.songData.title;
            document.getElementById("vid_iframe").src = data.songData.embedUrl;
            document.getElementById("info_div").innerHTML = data.songData.songInfoStr;
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
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
            info_table.append('\t|\t');
            info_table.append(data.songData.DJable ? 'DJable' : 'non-DJable');
            info_table.append('\t|\t');
            info_table.append(data.songData.Duration);
            
            if (data.songData.DJable === true) {
                document.getElementById("djable").classList.add("hidden");
                document.getElementById("notdjable").classList.remove("hidden");
                document.getElementById("notdjable__skip").classList.remove("hidden");
            } else {
                document.getElementById("djable").classList.remove("hidden");
                document.getElementById("notdjable").classList.add("hidden");
                document.getElementById("notdjable__skip").classList.add("hidden");
            }

            const songinfo_link_btn = document.getElementById("songInfo_a")
            songinfo_link_btn.href = "http://weslam.ddns.net/song/" + data.songData.vID
            
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


// ----------------------------------- ACTIONS --------------------------------- //
function baseOnClickCallback(data) {
    // data is a parsed JSON object
    console.log("ONCLICK REPLY")
    console.log(data)
    document.getElementById('response').innerHTML = data.response.top_notify;
    doFetchServer();
}

function onClickPlay(vid) {
    result_div = document.getElementById('search_result_div');
    result_div.innerHTML = "";

    return actionFetch('play', vid, (data) => {
        baseOnClickCallback(data);
    })
}

function onClickAction(actionId) {
    if (actionId === "join") {
        // or add loading
        document.getElementById('response').innerHTML = "JOINING"
    }
    
    let action_input = null;
    if (actionId === "search") {
        action_input = document.getElementById('search_input').value
    }
    console.log('input value: ')
    console.log(action_input)

    return actionFetch(actionId, action_input, (data) => {
        console.log(actionId)
        baseOnClickCallback(data);
        document.getElementById(actionId).disabled = false;

        if (data.response.song_choices != "null") { updateSongChoices(data.response.song_choices) };
    });
}

function actionFetch(actionId, action_input, callback) {
    fetch(actionUrl, 
        { 
            "method": "POST",
            // will decoded as text, might need better encoding
            "body": [actionId, showingVid, action_input]
        }
        )
        .then(response => response.json())
        .then(callback)
}

function updateSongChoices(songs) {
    result_div = document.getElementById('search_result_div');
    result_div.innerHTML = "";
    const p = document.createElement('p');
    p.innerHTML = "Search Results: ";
    result_div.append(p)
    for (let vid in songs) {
        result_div.append(createSongChoice(vid, songs[vid]))
    }
}

function createSongChoice(vid, title) {
    // {vID: Title} 
    const flex_div = document.createElement('div');
    flex_div.classList.add('flex');

    const p = document.createElement('p');
    p.innerHTML = title;
    flex_div.append(p)
    
    const btn = document.createElement('button')
    btn.classList.add('btn')
    btn.id = 'play'
    btn.onclick = function() { onClickPlay(vid) }
    btn.innerHTML = "Play"
    flex_div.append(btn)

    return flex_div
}

function inputSubmit(elem) {
    if(event.key === 'Enter') {
        onClickAction('search')
    }
}
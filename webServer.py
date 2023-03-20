from flask import Flask, render_template, jsonify, request
from flask_bootstrap import Bootstrap
from ServersHub import ServersHub
from DBFields import SongAttr
import random
from helper import vid_to_thumbnail, vid_to_embed_url
import asyncio
from waitress import serve
import ServerControl

app = Flask(__name__)
Bootstrap(app)


# POST
@app.post('/server/playing/<guildId>')
def serverPlaying(guildId):
    showingVid = request.data.decode()
    # print(showingVid)
    serverControl: ServerControl.ServerControl = ServersHub.getControl(guildId)
    songInfo = serverControl.getNowplaying()
    
    songData = constructSongData(songInfo)
    
    # not playing
    if songInfo == None:
        return constructReplyJSON({
            'needUpdate': False,
            'playing': False,
            'songData': None
        })
        
    # no update needed
    update = needUpdate(showingVid, songInfo, serverControl)
    if not update:
        return constructReplyJSON({
            'needUpdate': False
        })
       
    # actual update
    return constructReplyJSON({
        'needUpdate': True,
        'playing': True,
        'songData': songData,
        'queue': [ f"{author}: {info.Title}" for source, info, author in serverControl.getQueue() ],
    })
    
def needUpdate(showingVid, songInfo, serverControl):
    
    return showingVid != songInfo.vID or \
        len(onGoingJSON['queue']) != len(serverControl.getQueue())
    

def constructSongData(songInfo):
    return {
        'title': songInfo.Title,
        'vID': songInfo.vID,
        'thumbnailUrl': vid_to_thumbnail(songInfo.vID),
        'embedUrl': vid_to_embed_url(songInfo.vID), 
        'songInfoStr': str(songInfo)
    } if songInfo else None

def constructReplyJSON(added):
    global onGoingJSON
    onGoingJSON = onGoingJSON | added
    return jsonify(onGoingJSON)
    
    

@app.post('/server/action/<guildId>')
def djAction(guildId):
    print("DJACTION ")
    print(guildId)
    actions = ['skip', 'leave']
    actionId = request.data.decode()
    print(actionId)
    if actionId == 'skip':
        ServersHub.getControl(guildId).skip("WEB")
    if actionId == 'leave':
        ServersHub.getControl(guildId).disconnect()
    data = {'name': random.randint(100, 200)}
    
    return jsonify(data)



# GET
@app.route('/server/<guildId>')
def server(guildId):
    return render_template('server.html', guildId = guildId)

@app.route('/song/<vID>')
def song(vID):
    item = ServersHub.djdb.db_get(vID)
    info = [ {"title": attr, "value": item.get(attr)} for attr in SongAttr.get_all() ]
    info.append({"title": "Played count", "value": ServersHub.djdb.get_hist_count(vID, dj=False)})
    info.append({"title": "DJ Played count", "value": ServersHub.djdb.get_hist_count(vID, dj=True)})
    
    options = build_table_options(info, show_headers = False)
    return render_template('index.html', table_title = getattr(item, SongAttr.Title), **options)

@app.route('/')
def index():
    # songs will be returned as list of dictionary
    songs = ServersHub.djdb.list_all_songs(top = None, needed_attr = None, return_song_type = None)
    for i in range(len(songs)):
        # songs[i]["Details"] = f'<a href="/song/{songs[i][SongAttr.vID]}"><button>DETAIL</button></a>'
        songs[i]["Details"] = render_template('abutton.html', url = f"/song/{songs[i][SongAttr.vID]}", text = "DETAIL")

    activeGuilds = [ serverControl.getGuild() for i, serverControl in ServersHub.getAllControls().items() ]

    options = build_table_options(songs, headers = SongAttr.get_all() + ['Details'])
    return render_template('index.html', 
                           activeGuilds = activeGuilds,
                           table_title = "All songs", **options)



def build_table_options(info, headers = None, show_headers = True):
    options = {}
    assert type(info) == list, "info must be list of list or list of dictionary"
    assert len(info) > 0, "must have one or more rows"
    assert (type(info[0]) == list) or (type(info[0]) == dict), "info must be list of list (must provide headers) or list of dictionary"
    if headers is None and type(info[0]) == dict:
        headers = list(info[0].keys())

    # attributes key row
    if show_headers and headers is not None:
        options["ths"] = headers

    trs = []
    # individual row
    for row in info:
        tr = []
        if type(info[0]) == dict:
            for k in headers:
                v = row[k]
                tr.append(v)
        if type(info[0]) == list:
            for v in row:
                tr.append(v)
        trs.append(tr)
    options["trs"] = trs

    return options
    # return render_template('table.html', **options)


def runServer():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    global onGoingJSON
    # default response
    onGoingJSON = {
        'needUpdate': False,
        'playing': False,
        'songData': None,
        'queue': None,
    }

    hostName = "0.0.0.0"
    serverPort = 8080
    serve(app, host=hostName, port=serverPort)


if __name__ == "__main__":  
    runServer()

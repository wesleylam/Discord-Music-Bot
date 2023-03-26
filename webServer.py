from flask import Flask, render_template, jsonify, request
from flask_bootstrap import Bootstrap
from ServersHub import ServersHub
from const.DBFields import SongAttr
import random
from const.helper import vid_to_thumbnail, vid_to_embed_url, dict_compare
import asyncio
from waitress import serve
import ServerControl

app = Flask(__name__)
Bootstrap(app)

############## UTIL FUNC ####################
def needUpdate(guildId, showingVid, songInfo, serverControl):
    return showingVid != songInfo.vID or \
        guildId not in onGoingJSON or \
        not dict_compare(onGoingJSON[guildId]['songData'], songInfo.dictify_view_info()) or \
        len(onGoingJSON[guildId]['queue']) != len(serverControl.getQueue())
    
def constructSongDataTable(vID):
    item = ServersHub.djdb.db_get(vID)
    info = [ [attr, item.get(attr)] for attr in SongAttr.get_all() ]
    info.append(["DJ Played count", ServersHub.djdb.get_hist_count(vID, dj=True)])
    info.append(["Total Played count", ServersHub.djdb.get_hist_count(vID, dj=False)])
    return info

def constructReplyJSON(guildId, added):
    global onGoingJSON
    if guildId not in onGoingJSON:
        onGoingJSON[guildId] = {
            'needUpdate': False,
            'playing': False,
            'songData': None,
            'queue': None,
        }
        
    onGoingJSON[guildId] = onGoingJSON[guildId] | added
    return jsonify(onGoingJSON[guildId])
    

######################################### POST ############################################
@app.post('/server/playing/<guildId>')
def serverPlaying(guildId):
    showingVid = request.data.decode()
    # print(showingVid)
    serverControl: ServerControl.ServerControl = ServersHub.getControl(guildId) # will return none if not in channel
    songInfo = serverControl.getNowplaying() if serverControl is not None else None
    
    # not playing
    if songInfo == None:
        return constructReplyJSON(guildId, {
            'needUpdate': False,
            'playing': False,
            'songData': None
        })
        
    # no update needed
    update = needUpdate(guildId, showingVid, songInfo, serverControl)
    if not update:
        return constructReplyJSON(guildId, {
            'needUpdate': False
        })

    print("NEED UPDATE")
    # actual update
    return constructReplyJSON(guildId, {
        'needUpdate': True,
        'playing': True,
        'songData': songInfo.dictify_view_info(),
        'queue': [ f"{author}: {info.Title}" for source, info, author in serverControl.getQueue() ],
    })


@app.post('/server/action/<guildId>')
def djAction(guildId):
    print("DJACTION ")
    print(guildId)
    actions = ['skip', 'leave', 'djable', 'notdjable', 'notdjable;skip']
    decoded = request.data.decode()
    # print(decoded)
    actionIds, vID = decoded.split(',')
    print(actionIds)
    
    response = []
    for actionId in actionIds.split('__'):
        if actionId == 'join':
            task: asyncio.Task = ServersHub.loop.create_task(ServersHub.DJ_BOT.dj(guildId))
            # wait until done
            while not task.done(): pass
            response.append("Joined")
            
        if actionId == 'skip':
            ServersHub.getControl(guildId).skip("WEB")
            response.append("Skipped")
            
        if actionId == 'leave':
            ServersHub.getControl(guildId).disconnect()
            response.append("Leaving")
            
        if actionId == 'djable':
            response.append(f"{vID} is now DJable")
            ServersHub.djdb.set_djable(vID, True)
            ServersHub.getControl(guildId).updatePlayingInfo()
            
        if actionId == 'notdjable':
            response.append(f"{vID} is now NOT DJable")
            ServersHub.djdb.set_djable(vID, False)
            ServersHub.getControl(guildId).updatePlayingInfo()
    
    data = {
        'name': random.randint(100, 200),
        'response': ";".join(response)
    }
    
    return jsonify(data)



#################################### GET ############################################
@app.route('/server/<guildId>')
def server(guildId):
    return render_template('server.html', guildId = guildId)

@app.route('/song/<vID>')
def song(vID):
    item = ServersHub.djdb.db_get(vID)
    info = constructSongDataTable(vID)

    options = build_table_options(info, headers = None)
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



def build_table_options(info, headers = None):
    options = {}
    assert type(info) == list, "info must be list of list or list of dictionary"
    assert len(info) > 0, "must have one or more rows"
    assert (type(info[0]) == list) or (type(info[0]) == dict), "info must be list of list (must provide headers) or list of dictionary"
    if headers is None and type(info[0]) == dict:
        headers = list(info[0].keys())

    # attributes key row
    if headers is not None:
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
    global onGoingJSON
    # default response
    onGoingJSON = {} # one json per guild

    hostName = "0.0.0.0"
    serverPort = 8080
    serve(app, host=hostName, port=serverPort)


if __name__ == "__main__":  
    runServer()

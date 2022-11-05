# Python 3 server example
from DJDynamoDB import DJDB
from flask import Flask, render_template, jsonify, request
from flask_bootstrap import Bootstrap
from VcControlManager import VcControlManager
from DBFields import SongAttr
import random
from helper import vid_to_thumbnail, vid_to_embed_url

app = Flask(__name__)
Bootstrap(app)

# POST
@app.post('/server/playing/<guildId>')
def serverPlaying(guildId):
    showingVid = request.data.decode()
    print(showingVid)
    vcControl = manager.getControl(guildId)
    songInfo = vcControl.getPlayingInfo()
    
    songData = {
        'title': songInfo.Title,
        'vID': songInfo.vID,
        'thumbnailUrl': vid_to_thumbnail(songInfo.vID),
        'embedUrl': vid_to_embed_url(songInfo.vID), 
        'songInfoStr': str(songInfo)
    } if songInfo else None
    
    # not playing
    if songInfo == None:
        return constructReplyJSON({
            'needUpdate': False,
            'playing': False,
            'songData': None
        })
        
    # no update needed
    update = showingVid != songInfo.vID
    if not update:
        return constructReplyJSON({
            'needUpdate': False
        })
       
    # actual update
    return constructReplyJSON({
        'needUpdate': True,
        'playing': True,
        'songData': songData,
        'queue': vcControl.getTitleQueue(),
    })


def constructReplyJSON(added):
    default = {
        'needUpdate': False,
        'playing': False,
        'songData': None,
        'queue': None,
    }
    return jsonify(default | added)
    
    

@app.post('/server/action/<guildId>')
def djAction(guildId):
    print("DJACTION ")
    print(guildId)
    actions = ['skip', 'leave']
    actionId = request.data.decode()
    print(actionId)
    if actionId == 'skip':
        manager.getControl(guildId).skip("WEB")
    data = {'name': random.randint(100, 200)}
    
    return jsonify(data)



# GET
@app.route('/server/<guildId>')
def server(guildId):
    return render_template('server.html', guildId = guildId)

@app.route('/song/<vID>')
def song(vID):
    item = djdb.db_get(vID)
    info = [ {"title": attr, "value": item[attr]} for attr in SongAttr.get_all()  ]
    
    options = build_table_options(info, show_headers = False)
    return render_template('index.html', table_title = getattr(item, SongAttr.Title), **options)

@app.route('/')
def index():
    # songs will be returned as list of dictionary
    songs = djdb.list_all_songs(top = None, needed_attr = None, return_song_type = None)
    for i in range(len(songs)):
        # songs[i]["Details"] = f'<a href="/song/{songs[i][SongAttr.vID]}"><button>DETAIL</button></a>'
        songs[i]["Details"] = render_template('abutton.html', url = f"/song/{songs[i][SongAttr.vID]}", text = "DETAIL")

    activeGuilds = [ vcControl.getGuild() for i, vcControl in manager.getAllControls().items() ]

    options = build_table_options(songs, headers = SongAttr.get_all() + ['Details'])
    return render_template('index.html', 
                           activeGuilds = activeGuilds,
                           table_title = "All songs", print_test = VcControlManager, **options)



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


def runServer(vcControlManager):
    global manager 
    manager = vcControlManager
    
    global djdb  
    djdb = DJDB()
    djdb.connect()

    hostName = "0.0.0.0"
    serverPort = 8080
    app.run(debug = False, host = hostName, port = serverPort )

if __name__ == "__main__":  
    runServer()
import os
from uuid import uuid4

import redis
from axelrod.strategies import basic_strategies, _strategies
from axelrod.player import Player
from flask_sse import sse
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.config['REDIS_URL'] = os.environ['REDIS_URL']
app.register_blueprint(sse, url_prefix='/stream')

r = redis.StrictRedis.from_url(os.environ['REDIS_URL'], decode_responses=True)


@app.route('/')
def index():
    return render_template('index.html', strategies=basic_strategies)


@app.route('/register/', methods=['POST'])
def register():
    details = request.get_json()
    id = str(uuid4())
    username = details['username']
    strategy = details['strategy']
    r.hmset(
        f'user:{id}',
        {'username': username, 'strategy': strategy})
    return jsonify(status='OK', id=id), 201


def member_to_dict(member):
    id, username = member.split(':', 1)
    return {'id': id, 'username': username}


def dict_to_member(dict):
    return f'{dict["id"]}:{dict["username"]}'


@app.route('/lobby/')
def lobby():
    return jsonify(
        status='OK',
        players=[member_to_dict(p) for p in r.smembers('lobby')])


@app.route('/leave/', methods=['POST'])
def leave():
    details = request.get_json()
    id = details['id']
    username = r.hget(f'user:{id}', 'username')
    removed = r.srem('lobby', f'{id}:{username}')
    if removed:
        sse.publish({'id': id}, type='leave', channel='lobby')
    return jsonify(status='OK')


@app.route('/enter/', methods=['POST'])
def enter():
    details = request.get_json()
    id = details['id']
    username = r.hget(f'user:{id}', 'username')
    added = r.sadd('lobby', f'{id}:{username}')
    if added:
        sse.publish({'id': id, 'username': username}, type='enter', channel='lobby')
    return jsonify(status='OK', username=username)


def match_to_opponent(user_id, match):
    m = {
        'opponent': member_to_dict(match['opponent'])
    }
    if m['opponent']['id'] == user_id:
        m['opponent'] = member_to_dict(match['proponent'])
    return m


@app.route('/matches/')
def list_matches():
    id = request.args['id']
    match_ids = r.smembers(f'user:{id}:matches')
    p = r.pipeline()
    for match_id in match_ids:
        p.hgetall(f'match:{match_id}')
    return jsonify(
        status='OK',
        matches={
            match_id: match_to_opponent(id, match)
            for (match_id, match) in zip(match_ids, p.execute())})


@app.route('/matches/', methods=['POST'])
def create_match():
    details = request.get_json()
    match_id = str(uuid4())
    match = {
        'proponent': dict_to_member(details['proponent']),
        'opponent': dict_to_member(details['opponent']),
        'rounds': ''}

    p = r.pipeline()
    p.hmset(f'match:{match_id}', match)
    p.sadd(f'user:{details["proponent"]["id"]}:matches', match_id)
    p.sadd(f'user:{details["opponent"]["id"]}:matches', match_id)
    p.execute()

    for player in (details['proponent'], details['opponent']):
        d = match_to_opponent(player['id'], match)
        d['id'] = match_id
        sse.publish(d, type='add', channel=f'user:{player["id"]}:matches')
    return jsonify(status='OK', id=match_id), 201


def match_to_dict(user_id, match):
    m = {
        'rounds': match['rounds'].split(',') if match['rounds'] else []
    }
    m['opponent'] = member_to_dict(match['opponent'])
    if m['opponent']['id'] == user_id:
        m['opponent'] = member_to_dict(match['proponent'])
        m['rounds'] = [r[::-1] for r in m['rounds']]
    return m


@app.route('/matches/<match_id>/')
def get_match(match_id):
    id = request.args['id']
    match = r.hgetall(f'match:{match_id}')
    d = match_to_dict(id, match)
    d['status'] = 'OK'
    return jsonify(d)


@app.route('/matches/<match_id>/', methods=['POST'])
def submit_move(match_id):
    details = request.get_json()
    round = None
    with r.pipeline() as p:
        while True:
            try:
                p.watch(f'match:{match_id}')
                match = p.hgetall(f'match:{match_id}')
                is_proponent = match['proponent'].startswith(details['id'])

                if is_proponent:
                    if not match['rounds']:
                        match['rounds'] = f'{details["move"]}X'
                    elif match['rounds'][-2] == 'X':
                        match['rounds'] = match['rounds'].replace('X', details['move'])
                        round = match['rounds'][-2:]
                    elif match['rounds'][-1] != 'X':
                        match['rounds'] = ','.join(match['rounds'].split(',') + [f'{details["move"]}X'])
                else:
                    if not match['rounds']:
                        match['rounds'] = f'X{details["move"]}'
                    elif match['rounds'][-1] == 'X':
                        match['rounds'] = match['rounds'].replace('X', details['move'])
                        round = match['rounds'][-2:]
                    elif match['rounds'][-2] != 'X':
                        match['rounds'] = ','.join(match['rounds'].split(',') + [f'X{details["move"]}'])

                p.multi()
                p.hmset(f'match:{match_id}', match)
                p.execute()
                break
            except redis.WatchError:
                continue
    if round:
        d = {
            match['proponent'].split(':')[0]: round[0],
            match['opponent'].split(':')[0]: round[1],
        }
        sse.publish(d, type='round', channel=f'match:{match_id}')
    return jsonify(status='OK'), 201


def get_histories(user_id, proponent, rounds):
    proponent_history = [r[0] for r in rounds.split(',') if r and 'X' not in r]
    opponent_history = [r[1] for r in rounds.split(',') if r and 'X' not in r]
    if not proponent.startswith(user_id):
        proponent_history, opponent_history = opponent_history, proponent_history
    return proponent_history, opponent_history


@app.route('/hint/', methods=['POST'])
def hint():
    details = request.get_json()
    p = r.pipeline()
    p.hget(f'user:{details["id"]}', 'strategy')
    p.hmget(f'match:{details["match"]}', 'proponent', 'rounds')
    strategy, (proponent, rounds) = p.execute()
    proponent_history, opponent_history = get_histories(details['id'], proponent, rounds)
    proponent_strategy = getattr(_strategies, strategy)()
    proponent_strategy.history = proponent_history
    opponent_strategy = Player()
    opponent_strategy.history = opponent_history
    return jsonify(status='OK', move=proponent_strategy.strategy(opponent_strategy))

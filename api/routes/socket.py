import random
from flask import request
from flask_socketio import  join_room, emit
from models.team import Team
from server.instance import server
from models.game_list import game_list
from models.game import Game, TEAM_ONE, TEAM_TWO
from constants.call_truco_constants import ACCEPT,DECLINE,VALUES_HAND_BUFF_JSON
from models.hand import DRAW
from models.player import Player
from models.hand_resullt import HandResult
from models.card import Card
from models.bot import Bot
from time import sleep

messageCount = 0
players = []

RM_SUCCESS = 0
RM_TEAM_IS_FULL = 1
RM_ROOM_IS_FULL = 2
RM_ROOM_NOT_EXIST = 3

TEN_HAND = 10
TEN_HAND_VALUE = 4

BOT_WAIT_TIME_TO_PLAY = 2
END_HAND_WAIT_TIME = 2

@server.socketio.on('connect')
def test_connect():
    print('connection received')


@server.socketio.on('create_game')
def create(data):
    username = data['username']
    id = game_list.get_next_id()
    players.append(1)
    game_list.games.append(Game(id, Player(len(players), username, request.sid)))
    game_list.sids[request.sid] = id
    join_room(id)
    team_userNames = []
    for team in game_list.games[id - 1].teams:
        team_list = []
        for player in team.players:
            team_list.append(player.name)  
        team_userNames.append(team_list)

    server.socketio.emit(
        'room_message', {'username' : username, 'message' : f'{username} has created and intered on room {id} on team 1'}, to=id)
    server.socketio.emit(
        'connect_successfully', {'username':username, 'players':team_userNames,'room':id}, to=id)

@server.socketio.on('connect_game')
def join(data):
    username = data['username']
    team_id = int(data['team'])
    id = int(data['room'])

    # Verifica se a sala existe.
    if game_list.check_game_by_id(id):
        players.append(1)
        
        # Verifica se a sala está cheia.
        if not game_list.games[id - 1].is_full():
            playName = game_list.games[id - 1].add_player(Player(len(players), username, request.sid), team_id if team_id == TEAM_ONE or team_id == TEAM_TWO else None)
            game_list.sids[request.sid] = id
            if playName:
                join_room(id)
                
                team_userNames = []
                for team in game_list.games[id - 1].teams:
                    team_list = []
                    for player in team.players:
                      team_list.append(player.name)  
                    team_userNames.append(team_list)
                # Entrou no time
                server.socketio.emit(
                    'connect_successfully', {'username':playName, 'players':team_userNames, 'room':id}, to=id)
                server.socketio.emit(
                    'room_message', {'status': RM_SUCCESS, 'message': f'{playName} has intered on room {id} '}, to=id)
                
            else:
                # Time cheio
                server.socketio.emit(
                    'room_message', {'status': RM_TEAM_IS_FULL, 'message': f'Team {team_id} on room {id} is full'}, to=request.sid)
        else:
            # Sala cheia
            server.socketio.emit(
                'room_message', {'status': RM_ROOM_IS_FULL, 'message': f'Room {id} is full.'}, to=request.sid)
    else:
        # Sala inexistente
        server.socketio.emit(
            'room_message', {'status': RM_ROOM_NOT_EXIST, 'message': f'Room {id} does not exist.'}, to=request.sid)

@server.socketio.on('start_game')
def start():
    id = game_list.sids[request.sid]
    if request.sid == game_list.games[id - 1].owner.sid:
        game_list.games[id - 1].start()
        [server.socketio.emit('your_cards',{"username": player.name, "cards": player.cards_to_json()["cards"], "round_order": game_list.games[id - 1].player_order_to_json()},to=player.sid) for player in game_list.games[id - 1].player_order if not isinstance(player, Bot)]
    else:
        server.socketio.emit(
        'room_message', f'Apenas o dono pode iniciar a partida', to=request.sid)

@server.socketio.on('throw_card')
def throw(data):
    id = game_list.sids[request.sid]
    card_code = data['card_code']
    player = game_list.games[id - 1].player_order[0]
    if player.sid != request.sid:
        server.socketio.emit(
        'room_message', f'Não é sua vez de jogar', to=request.sid)    
        return

    card = Card(card_code)
    trigger_card_thrown_event(card, player, id)

@server.socketio.on('send message')
def send_room_message(data):
    room = game_list.sids[request.sid]
    message = data['message']
    emit('room_message', message, to=room)


@server.socketio.on('message')
def handle_message(data):
    print(f'received message: {data}')
    global messageCount

    # setting the message id
    messageCount += 1
    data['id'] = messageCount

    room = int(data['room'])

    # by including include_self=False, the message wont be sent to the client that sent the message
    server.socketio.emit('new_message', data, to=room)

@server.socketio.on('call_truco')
def call_truco():
    print('Chegou no call_truco!')
    id = game_list.sids[request.sid]
    player = game_list.games[id - 1].get_player_sid(request.sid)
    trigger_call_truco(id, player)
    # team_calling_truco = game_list.games[id-1].call_truco(player)

    # server.socketio.emit('receive_truco',{'username': player.name,'team':team_calling_truco.id,'proposed_value':VALUES_HAND_BUFF_JSON[game_list.games[id - 1].current_hand.hand_value]},to=id)

    # for team in game_list.games[id-1].teams:
    #     if team.id != team_calling_truco.id:
    #         for player_analizing_truco in team.players:
    #             if isinstance(player_analizing_truco, Bot):
    #                 if not game_list.games[id - 1].current_hand.waiting_truco:
    #                     return
    #                 result,hand_result = game_list.games[id - 1].truco_response(player_analizing_truco.bot_get_response_truco(), player_analizing_truco)
    #                 trigger_truco_response_event(player_analizing_truco,result, hand_result, player_analizing_truco.bot_get_response_truco(), id)

def trigger_call_truco(id, player: Player):
    team_calling_truco = game_list.games[id-1].call_truco(player)
    server.socketio.emit('receive_truco',{'username': player.name,'team':team_calling_truco.id,'proposed_value':VALUES_HAND_BUFF_JSON[game_list.games[id - 1].current_hand.hand_value]},to=id)

    for team in game_list.games[id-1].teams:
        if team.id != team_calling_truco.id:
            for player_analizing_truco in team.players:
                if isinstance(player_analizing_truco, Bot):
                    if not game_list.games[id - 1].current_hand.waiting_truco:
                        return
                    sleep(BOT_WAIT_TIME_TO_PLAY)
                    result,hand_result = game_list.games[id - 1].truco_response(player_analizing_truco.bot_get_response_truco(), player_analizing_truco)
                    trigger_truco_response_event(player_analizing_truco,result, hand_result, player_analizing_truco.bot_get_response_truco(), id)

@server.socketio.on('accept_truco')
def accept_truco():
    print('acept')
    response_truco(ACCEPT,request.sid)

@server.socketio.on('decline_truco')
def decline_truco():
    print('decline')
    response_truco(DECLINE,request.sid)

@server.socketio.on('accept_ten_hand')
def accept_ten_hand():
    print('accepted_ten_hand')
    id = game_list.sids[request.sid]
    if TEN_HAND not in game_list.games[id - 1].get_score():
        server.socketio.emit(
        'room_message', f'Não está na mão de 10', to=request.sid)    
        return
    print('passou')
    game_list.games[id - 1].current_hand.hand_value = TEN_HAND_VALUE
    player = game_list.games[id - 1].get_player_sid(request.sid)
    trigger_accepted_ten_hand(player, id)

@server.socketio.on('decline_ten_hand')
def decline_ten_hand():
    print('decline tem hand')
    id = game_list.sids[request.sid]
    if  TEN_HAND not in game_list.games[id - 1].get_score():
        
        server.socketio.emit(
        'room_message', f'Não está na mão de 10', to=request.sid)    
        return
    print('decline')
    player = game_list.games[id - 1].get_player_sid(request.sid)
    trigger_declined_ten_hand(player, id)
    # hand_result = game_list.games[id - 1].decline_ten_hand(player)
    # server.socketio.emit('declined_ten_hand',{'username':player.name},to=id)
    # end_hand(hand_result,id)

def trigger_accepted_ten_hand(player: Player, id):
    server.socketio.emit('accepted_ten_hand',{'username':player.name},to=id)
    next_player = game_list.games[id - 1].get_next_player()
    if isinstance(next_player, Bot):
        bot_make_a_move(next_player, id)

def trigger_declined_ten_hand(player: Player, id):
    hand_result = game_list.games[id - 1].decline_ten_hand(player)
    server.socketio.emit('declined_ten_hand',{'username':player.name},to=id)
    end_hand(hand_result,id)


def response_truco(response:int,sid):
    id = game_list.sids[sid]
    player = game_list.games[id - 1].get_player_sid(sid)
    result,hand_result = game_list.games[id -1].truco_response(response, player)
    trigger_truco_response_event(player,result,hand_result,response, id)


def trigger_truco_response_event(player: Player, result, hand_result, response, id):
    if result == ACCEPT:
        print('entrou')
        server.socketio.emit('accepted_truco', {'username':player.name,'new_hand_value':game_list.games[id - 1].current_hand.hand_value}, to=id)
        return
    elif result == DECLINE:
        server.socketio.emit('declined_truco', {'username':player.name}, to=id)
        end_hand(hand_result,id)
        return
    server.socketio.emit('waiting_truco',{'username':player.name,'response':response},to=id)


def end_hand(result:HandResult,id:int):
    sleep(END_HAND_WAIT_TIME)
    server.socketio.emit('end_hand',{'new_order':game_list.games[id -1].player_order_to_json()['player_order'],
                                                 'game_score':game_list.games[id -1].get_score(),'overall_score':game_list.games[id -1].get_games_won(),'winner':result.team_winner.id},to=id)
    [server.socketio.emit('your_cards',player.cards_to_json(),to=player.sid) for player in game_list.games[id - 1].player_order if not isinstance(player, Bot)]
    ten_hand = is_ten_hand(id)
    if not ten_hand:
        next_player = game_list.games[id - 1].get_next_player()
        if isinstance(next_player, Bot):
            bot_make_a_move(next_player, id)

    

def trigger_card_thrown_event(card_thrown: Card, player: Player, id):
    result = game_list.games[id -1].throw_card(card_thrown,player.name)
    if isinstance(result,HandResult):
        server.socketio.emit('throwed_card',{'username' : player.name,'card':card_thrown.to_json()},to=id)
        end_hand(result,id)
        return
    if isinstance(result,Player) or result == DRAW: 
        server.socketio.emit('throwed_card', {'username' : player.name, 'card' : card_thrown.to_json()}, to=id)
        sleep(END_HAND_WAIT_TIME)
        server.socketio.emit('end_round',{'team':game_list.games[id -1].find_player_team(result).id if result != DRAW else DRAW,
                                            'new_order':game_list.games[id -1].player_order_to_json()['player_order']},to=id)
        [server.socketio.emit('your_cards',player.cards_to_json(),to=player.sid) for player in game_list.games[id - 1].player_order if not isinstance(player, Bot)]

        next_player = game_list.games[id - 1].get_next_player()
        if isinstance(next_player, Bot):
            bot_make_a_move(next_player, id)
        
        return
    
    server.socketio.emit('throwed_card', {'username' : player.name, 'card' : card_thrown.to_json()}, to=id)

    next_player = game_list.games[id - 1].get_next_player()
    if isinstance(next_player, Bot):
        bot_make_a_move(next_player, id)

def bot_make_a_move(bot_player: Bot, id):
    sleep(BOT_WAIT_TIME_TO_PLAY)
    # FUNÇÃO DO BOT ANALISAR SE JOGA TRUCO
    # if bot_player.bot_call_truco():
    #     trigger_call_truco(id, bot_player)
    
    bot_card = bot_player.throw_card(bot_player.bot_get_random_card())
    print(f'Bot jogando: {bot_player.name} Carta jogando: {bot_card.code}')
    trigger_card_thrown_event(bot_card, bot_player, id)

def is_ten_hand(id:int):
    game = game_list.games[id - 1]
    print('aou potencia')
    print(game.get_score)
    print(game.get_score().count(TEN_HAND))
    if TEN_HAND not in game.get_score() or game.get_score().count(TEN_HAND) == 2:
        print('TA NO IF')
        return False
    team_on_ten_hand =  game.teams[game.get_score().index(TEN_HAND)] 
    print('entrou NO TEN HAND')

    if team_on_ten_hand.is_team_of_bots():
        bot_player = team_on_ten_hand.get_bot_on_team()
        bots_response = bots_analize_ten_hand(team_on_ten_hand)
        if bots_response == ACCEPT:
            trigger_accepted_ten_hand(bot_player, id)
        else:
            trigger_declined_ten_hand(bot_player, id)
    
    elif team_on_ten_hand.is_bot_on_team():
        bot_player = team_on_ten_hand.get_bot_on_team()
        for player in team_on_ten_hand.players:
            if not isinstance(player, Bot):
                server.socketio.emit('ten_hand',{'partner_cards':bot_player.cards_to_json()['cards']},to=player.sid)
                break
            
    elif game_list.games[id -1].player_order.index(team_on_ten_hand.players[0]) < game_list.games[id -1].player_order.index(team_on_ten_hand.players[1]):
        server.socketio.emit('ten_hand',{'partner_cards':team_on_ten_hand.players[1].cards_to_json()['cards']},to=team_on_ten_hand.players[0].sid)

    else:
        server.socketio.emit('ten_hand',{'partner_cards':team_on_ten_hand.players[0].cards_to_json()['cards']},to=team_on_ten_hand.players[1].sid)
    return True

def bots_analize_ten_hand(team: Team):
    return random.choice([ACCEPT, DECLINE])
    # bots_cards = []
    # for bot in team.players:
    #     for card in bot.cards:
    #         bots_cards.append(card)

    




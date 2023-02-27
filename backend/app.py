"""
Flask API and backend for the assassin game. 
"""
__author__ = 'Pierce Maloney'


import pymongo
import random
from db_info import uri

# -----------------------------------------------------------------
# Flask

from flask import Flask, jsonify
app = Flask(__name__)


# -----------------------------------------------------------------
# API endpoints

@app.route('/hello_world')
def hello_world():
    return jsonify('hello, assassins')

# Define the API endpoint for getting the player kills
@app.route('/api/game-stats/<string:game_name>', methods=['GET'])
def get_player_kills(game_name: str):
    collection = connect_to_db()
    if collection is None:
        return {}
    game_info = collection.find_one({"name": game_name})
    if game_info is None:
        return {}

    # Get the dictionary of player kills for the game
    player_kills = game_info['players']

    # Return the dictionary of player kills
    return jsonify(player_kills)


@app.route('/api/players/<string:netid>', methods=['GET'])
def get_player_info(netid: str):
    collection = connect_to_db(collection_name="players")
    if collection is None:
        return {}
    player_info = collection.find_one({"netid": netid})
    if player_info is None:
        return {}
    return jsonify(player_info)

# -----------------------------------------------------------------

# TODO twilio integration


def connect_to_db(collection_name="games"):
    """
    Connects to db and returns collection. Returns None if failure
    """
    try:
        client = pymongo.MongoClient(uri)
        db = client["assassin"]
        collection = db[collection_name]
        return collection
    except pymongo.errors.ConnectionFailure as e:
        print(f"Failed to connect to MongoDB server: {e}")
        return None


def get_game_info(game_name: str):
    """
    returns the game info of the specified name
    """
    collection = connect_to_db()
    if collection is None:
        return None

    # find the game with the specified game_name in the database
    game_info = collection.find_one({"name": game_name})

    if game_info is None:
        print(
            f"No game with the name '{game_name}' was found in the database.")
        return None

    return game_info


def update_game(game_info: dict):
    # connect to database
    collection = connect_to_db()
    if collection is None:
        return None

    players = game_info["players"]
    targets = game_info["targets"]
    alive_players = game_info["alive_players"]
    dead_players = game_info["dead_players"]

    collection.update_one({"_id": game_info["_id"]}, {"$set": {
        "players": players,
        "targets": targets,
        "alive_players": alive_players,
        "dead_players": dead_players}})


def new_player(netid: str, first_name: str, last_name: str, nickname: str):
    """
    creates a new player and adds it to the players collection in db
    """
    players_collection = connect_to_db(collection_name="players")
    if players_collection is None:
        return None

    # create a document for the new player
    player_info = {
        "netid": netid,
        "first_name": first_name,
        "last_name": last_name,
        "nickname": nickname
    }

    # insert the new player document into the players collection
    players_collection.insert_one(player_info)

    # return the player information
    return player_info


def add_player_to_game(game_name: str, netid: str):
    """
    adds player to game and shuffles the targets
    """
    game_info = get_game_info(game_name)
    if game_info == None:
        return

    # Check if player is already in game
    if netid in game_info["players"]:
        return

    # add player to game
    game_info["players"][netid] = 0
    game_info["alive_players"].append(netid)
    update_game(game_info)
    shuffle_game(game_name)


def shuffle_game(game_name: str):
    """
    Shuffles the targets of the alive players in the game
    """
    game_info = get_game_info(game_name)
    if game_info is None:
        return

    if len(game_name["alive_players"]) > 0:
        # shuffle the list of players to create a random order
        random.shuffle(game_name["alive_players"])

    # create a dictionary where each player's target is the next player in the shuffled list
    targets = {}
    for i in range(len(game_name["alive_players"])):
        targets[game_name["alive_players"][i]] = game_name["alive_players"][(
            i+1) % len(game_name["alive_players"])]

    update_game(game_info)


def new_game(game_name: str, player_list=[]):
    """
    Create a new game and store it in db
    """
    # connect to database
    collection = connect_to_db()
    if collection is None:
        return None

    # check if a game with the same name already exists in the database
    if collection.find_one({"name": game_name}) is not None:
        print(
            f"A game with the name '{game_name}' already exists in the database.")
        return None

    alive_players = list(player_list)
    if len(alive_players) > 0:
        # shuffle the list of alive players to create a random order
        random.shuffle(alive_players)

    # player: kill_count dict
    players = {}
    for player in player_list:
        players[player] = 0

    # create a dictionary where each player's target is the next alive player in the shuffled list
    targets = {}
    for i in range(len(alive_players)):
        targets[alive_players[i]] = alive_players[(i+1) % len(alive_players)]

    # create a list of dead players and initialize it to be empty
    dead_players = []

    # insert the game information and player status into the database
    game_info = {
        "name": game_name,
        "players": players,
        "targets": targets,
        "alive_players": alive_players,
        "dead_players": dead_players
    }
    collection.insert_one(game_info)

    # return the game information
    return game_info


def killed_target(game_name: str, netid: str):
    """
    The netid of the player that killed their target.
    Removes target from alive list and increases player's kill count
    """
    game_info = get_game_info(game_name)
    if game_info is None:
        return None

    # get the player's target
    target = game_info["targets"][netid]

    # remove the target from the alive list and add them to the dead list
    game_info["alive_players"].remove(target)
    game_info["dead_players"].append(target)

    # assign the dead player's target to the player who killed them
    game_info["targets"][netid] = game_info["targets"][target]

    # remove the dead player from the "targets" dictionary
    del game_info["targets"][target]

    # increment the player's kill count
    game_info["players"][netid] += 1

    # update the game information in the database
    update_game(game_info)

    # return the dead player's name
    return target


def unalive_player(game_name: str, netid: str):
    game_info = get_game_info(game_name)
    if game_info is None:
        return None

    if netid in game_info["alive_players"]:
        game_info["alive_players"].remove(netid)
        game_info["dead_players"].append(netid)

        # assign the dead player's target to the player who had them
        player_who_had_them = next(
            iter({i for i in game_info["targets"] if game_info["targets"][i] == netid}))
        game_info["targets"][player_who_had_them] = game_info["targets"][netid]

        # remove the player from the "targets" dictionary
        del game_info["targets"][netid]

        update_game(game_info)
        return game_info
    return None


def unpack_game(game_info: dict):
    players = game_info["players"]
    targets = game_info["targets"]
    alive_players = game_info["alive_players"]
    dead_players = game_info["dead_players"]
    return players, targets, alive_players, dead_players


# -----------------------------------------------------------------
# Tests

def test1():
    # list of players' names
    players = ["alice", "bob", "charlie", "david", "eve"]
    print(new_game("test_game", players))


def test2():
    # must be ran after test1
    killed_target("test_game", "alice")


def test3():
    # must be ran after test2
    print("unaliving alice")
    print(get_game_info("test_game"))
    unalive_player("test_game", "alice")
    print(get_game_info("test_game"))


def main():
    # print("hi")
    # print("hi")
    # print("hi")
    # new_player("pmaloney", "pierce", "maloney", "killa")
    # print("here")
    # test1()
    # test2()
    # test3()
    app.run(debug=True)


if __name__ == "__main__":
    main()

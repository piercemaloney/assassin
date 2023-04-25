"""
Flask API and backend for the assassin game. 
"""
__author__ = 'Pierce Maloney'


import pymongo
import random
import csv

from db_info import MONGODB_URI, SENDGRID_API_KEY, IVY_ASSASSIN_EMAIL, ADMIN_API_KEY


from functools import wraps
from flask import Flask, jsonify, make_response, json, request, abort

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# -----------------------------------------------------------------
# Flask

app = Flask(__name__)

# -----------------------------------------------------------------
# API endpoints

@app.route('/')
@app.route('/hello_world')
def hello_world():
    response = make_response('Happy hunting.')
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# Define the API endpoint for getting the player stats (alive/kills)
@app.route('/api/game-stats/<string:game_name>')
def get_player_kills_response(game_name: str):
    collection = connect_to_db()
    if collection is None:
        print('Failed connection to db')
        return {}
    game_info = collection.find_one({"name": game_name})
    if game_info is None:
        print('Failed retrieval of game')
        return {}
    # Get the dictionary of player kills for the game
    player_kills = game_info['players']
    game_stats = {}
    for netid, kills in player_kills.items():
        is_alive = True if netid in game_info['alive_players'] else False
        game_stats[netid] = {"kills": kills, "isAlive": is_alive}

    # Return the dictionary of player kills
    response = jsonify(game_stats)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/api/players/<string:netid>', methods=['GET'])
def get_player_info_response(netid: str):
    collection = connect_to_db(collection_name="players")
    if collection is None:
        print('Failed connection to db')
        return {}
    player_info = collection.find_one({"netid": netid})
    if player_info is None:
        print(f'Failed retrieval of player: {netid} info')
        return {}
    
    # remove object_id attribute to properly jsonify the object
    player_info.pop('_id', None) 

    response = jsonify(player_info)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


# --------------------------------
# Admin

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.args.get('api_key')
        if not api_key or api_key != ADMIN_API_KEY:
            abort(401)
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin/killed_target/<game_name>/<killer_netid>', methods=['POST'])
@require_api_key
def admin_killed_target(game_name, killer_netid):
    result = killed_target(game_name, killer_netid)
    response = jsonify(result)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# TODO: admin functions
# @app.route('/admin/get_targets/<game_name>/<killer_netid>', methods=['POST'])
# @require_api_key
# def admin_killed_target(game_name, killer_netid):
#     result = killed_target(game_name, killer_netid)
#     response = jsonify(result)
#     response.headers.add('Access-Control-Allow-Origin', '*')
#     return response


# -----------------------------------------------------------------


def connect_to_db(collection_name="games"):
    """
    Connects to db and returns collection. Returns None if failure
    """
    try:
        client = pymongo.MongoClient(MONGODB_URI)
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


def new_player(netid: str, name: str, nickname = None, email = None):
    """
    creates a new player and adds it to the players collection in db
    """
    players_collection = connect_to_db(collection_name="players")
    if players_collection is None:
        return None
    
    # clean netid
    netid = netid.lower()
    
    # check if a player with the given netid already exists
    existing_player = players_collection.find_one({"netid": netid})
    if existing_player is not None:
        return f"Player with netid {netid} already exists"
    
    # give princeton email
    if email is None:
        email = f'{netid}@princeton.edu'

    # construct the fullAssassinName field
    if nickname is None or nickname == "*":
        full_assassin_name = name
    else:
        words = name.split()
        first_word = words[0]
        rest_of_words = ' '.join(words[1:])
        full_assassin_name = f"{first_word} '{nickname}' {rest_of_words}"

    # create a document for the new player
    player_info = {
        "netid": netid.lower(),
        "name": name,
        "nickname": nickname,
        "email": email.lower(),
        "fullAssassinName": full_assassin_name
    }

    # insert the new player document into the players collection
    players_collection.insert_one(player_info)

    # return the player information
    return player_info


def get_player_info(netid: str):
    """ To be used locally
    """
    collection = connect_to_db(collection_name="players")
    if collection is None:
        print('Failed connection to db')
        return None

    player_info = collection.find_one({"netid": netid})
    if player_info is None:
        print(f'Failed retrieval of player: {netid} info')
        return None

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
    
    # Ensure the killer is alive
    if netid not in game_info["alive_players"]:
        return f"Player with netid {netid} is not alive in the game"

    # get the player's target
    target = game_info["targets"][netid]

    # remove the target from the alive list and add them to the dead list
    game_info["alive_players"].remove(target)
    game_info["dead_players"].append(target)

    # Send email informing the victim that they have been slain
    send_you_have_been_slain_email(target)

    # assign the dead player's target to the player who killed them
    game_info["targets"][netid] = game_info["targets"][target]

    # Send email with the new target
    send_new_target_email(netid, game_info["targets"][netid])

    # remove the dead player from the "targets" dictionary
    del game_info["targets"][target]

    # increment the player's kill count
    game_info["players"][netid] += 1

    # update the game information in the database
    update_game(game_info)

    # return the dead player's name
    return target


def unalive_player(game_name: str, netid: str):
    """ Makes a player unalive. Does not add to anyone's kill count, but updates the game
    """
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


def process_csv_and_create_game(file_path, game_name):
    player_netids = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Extract player information
            netid = row['netID']
            full_name = row['Full Name']
            nickname = row['Assassin Name']
            email_address = row['Email Address']

            if full_name and netid:
                # Create a new player using the new_player function
                new_player(netid, full_name, nickname, email_address)
                player_netids.append(netid.lower())
                print('Added:', netid, full_name, nickname, email_address)
            else:
                print(f"Skipping row due to missing required fields: {row}")

    # create the new game
    new_game(game_name, player_netids)


# -----------------------------------------------------------------
# Twilio/Sendgrid

def send_email(to_email:str, subject, content):
    try:
        message = Mail(
            from_email=IVY_ASSASSIN_EMAIL,  # replace with your email or desired sender email
            to_emails=to_email,
            subject=subject,
            html_content=content
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent to {to_email} with status code {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")


# -----------------------------
# Email types:

def send_new_target_email(netid: str, target_netid: str, welcome_email = False):
    """ Sends an email to netid that tells them their target"""
    # Retrieve player and target information
    player_info = get_player_info(netid)
    target_info = get_player_info(target_netid)

    player_full_assassin_name = player_info["fullAssassinName"]
    target_full_assassin_name = target_info["fullAssassinName"]

    # Create email content
    if welcome_email is True:
        subject = "Your First Target"
        content = f"""
        <p>Hello {player_full_assassin_name},</p>
        <p>Welcome to Assassin!<br> <br>
        Your first target is:<br>
        <strong>{target_full_assassin_name}</strong></p>
        <p>Reminder:</p>
        <ul>
            <li>Film your kill, and send it in the Assassin GroupMe for it to be confirmed.</li>
        </ul>
        <p>Happy hunting!</p>
        <p>Good luck,</p>
        <p>HQ</p>
        """
    else:
        subject = "Your New Target"
        content = f"""
        <p>Hello {player_full_assassin_name},</p>
        <p>Your new target is:<br>
        <strong>{target_full_assassin_name}</strong></p>
        <p>Reminder:</p>
        <ul>
            <li>Film your kill, and send it in the Assassin GroupMe for it to be confirmed.</li>
        </ul>
        <p>Happy hunting!</p>
        <p>Good luck,</p>
        <p>HQ</p>
        """

    to_email = player_info["email"]
    send_email(to_email, subject, content)

# def send_kill_confirmation_pending_email(netid):
#     """ Sends an email to netid that tells them their target"""
#     # Retrieve player and target information
#     player_info = get_player_info(netid)

#     player_full_assassin_name = player_info["fullAssassinName"]
    
#     subject = "Kill Confirmation Pending"
#     content = f"""
#     <p>Hello {player_full_assassin_name},</p>
#     <p>Your kill is pending confirmation. Once it is confirmed, you'll receive a new target email with the updated information.</p>
#     <p>Reminder:</p>
#     <ul>
#         <li>Make sure you have sent the video of your kill in the Assassin GroupMe.</li>
#     </ul>
#     <p>HQ</p>
#     """
#     to_email = player_info["email"]
#     send_email(to_email, subject, content)

def send_you_have_been_slain_email(netid):
    """ Sends an email to netid that tells them they're dead"""
    # Retrieve player and target information
    player_info = get_player_info(netid)

    player_full_assassin_name = player_info["fullAssassinName"]

    subject = "You Have Been Slain"
    content = f"""
    <p>Hello {player_full_assassin_name},</p>
    <p>Unfortunately, you have been slain in the game of Assassin. Your journey has come to an end.</p>
    <p>Thanks for participating in the game. We hope you enjoyed it.</p>
    <p>Regards,</p>
    <p>HQ</p>
    """

    to_email = player_info["email"]
    send_email(to_email, subject, content)



# -----------------------------------------------------------------
# Tests

def test_assassin_game():
    with app.app_context():
        # Create new game
        game_name = "Test Game 2"
        players_list = ["piercemaloney1", "pmaloney", "kmaloney"]
        new_player('piercemaloney1', 'Pierce Maloney 1', nickname='Slaya', email='piercemaloney1@gmail.com')
        new_player('pmaloney', 'Pierce Maloney 2', 'Slayer')
        new_player('kmaloney', 'Keller Maloney', 'Kella')
        new_game(game_name, players_list)

        # Check the created game
        game_info = get_game_info(game_name)
        assert game_info is not None
        assert len(game_info["alive_players"]) == 3
        assert len(game_info["dead_players"]) == 0

        # Check the players in the game
        for netid in players_list:
            player_info = get_player_info(netid)
            assert player_info is not None
            assert player_info["netid"] == netid

        # Simulate a kill
        killer = players_list[0]
        killed = killed_target(game_name, killer)

        # Check that the killed player is no longer alive
        game_info = get_game_info(game_name)
        assert killed not in game_info["alive_players"]
        assert killed in game_info["dead_players"]

        # Check that the killer's kill count has increased
        assert game_info["players"][killer] == 1

        # Check that emails have been sent (manually, by checking your inbox)
        print("Check the inboxes of the specified email addresses for the 'Your New Target' and 'You Have Been Slain' emails.")


def test_ivy_assassin():
    with app.app_context():
        # Create new game
        game_name = "ivy"
        process_csv_and_create_game('ivy_assassin_signup.csv', 'ivy')
        
        game_info = get_game_info(game_name)
        print("alive:", game_info["alive_players"])

        targets = game_info["targets"]

        for player in game_info["alive_players"]:
            send_new_target_email(player, targets[player], welcome_email=True)


def print_targets(game_name, netids):
    game_info = get_game_info(game_name)

    if game_info is not None:
        targets = game_info["targets"]

        for netid in netids:
            player_info = get_player_info(netid)
            if player_info is not None:
                player_name = player_info["name"]

                target_netid = targets.get(netid)
                if target_netid:
                    target_info = get_player_info(target_netid)
                    if target_info is not None:
                        target_name = target_info["name"]
                        print(f"{player_name} has target: {target_name}")
                    else:
                        print(f"Could not find target information for {target_netid}")
                else:
                    print(f"Could not find target for {player_name}")
            else:
                print(f"Could not find player information for {netid}")
    else:
        print("Game not found.")


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()

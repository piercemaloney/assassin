game_info = { "targets": {"pierce": "keller", "keller": "cleo", "cleo": "pierce"}}
netid = "cleo"

player_who_had_them = {i for i in game_info["targets"] if game_info["targets"][i]==netid}
print(*player_who_had_them)

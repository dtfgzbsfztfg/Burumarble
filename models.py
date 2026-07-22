# -*- coding: utf-8 -*-
"""데이터 모델 (JSON 직렬화 가능한 dict 기반)"""
from .board import START_CASH


def new_player(discord_id: str, name: str) -> dict:
    return {
        "discord_id": discord_id,
        "name": name,
        "cash": START_CASH,
        "position": 0,
        "properties": {},        # {tile_id(str): level(int)}
        "island_turns": 0,
        "get_out_cards": 0,
        "bankrupt": False,
    }


def new_game(channel_id: str) -> dict:
    return {
        "channel_id": channel_id,
        "phase": "waiting",      # waiting -> playing -> ended
        "players": {},           # {discord_id: player_dict}, insertion order = join order
        "order": [],             # list of discord_id (turn order)
        "turn_index": 0,
        "doubles_streak": 0,
        "fund": 0,
        "ownership": {},         # {tile_id(str): owner_discord_id}
        "last_roll": None,       # [d1, d2]
        "log": [],               # recent event strings (최대 10개 유지)
        "winner": None,
    }


def push_log(game: dict, text: str):
    game["log"].append(text)
    game["log"] = game["log"][-10:]

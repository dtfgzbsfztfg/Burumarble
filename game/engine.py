# -*- coding: utf-8 -*-
"""부루마블 게임 엔진 - 모든 규칙/상태 변화 로직"""
import random

from .board import (
    BOARD, BOARD_SIZE, get_tile, ISLAND_TILE_ID, GO_BONUS, ISLAND_SKIP_TURNS,
    ISLAND_ESCAPE_FEE, RENT_MULTIPLIER, BUILD_COST_RATIO, BUILD_MAX_LEVEL,
)
from .cards import draw_card
from .models import new_game, new_player, push_log


# ---------- 게임 생성 / 참가 / 시작 ----------

def create_game(channel_id: str) -> dict:
    return new_game(str(channel_id))


def join_game(game: dict, discord_id: str, name: str):
    discord_id = str(discord_id)
    if game["phase"] != "waiting":
        return False, "이미 게임이 시작되어 참가할 수 없습니다."
    if discord_id in game["players"]:
        return False, "이미 참가한 플레이어입니다."
    if len(game["players"]) >= 6:
        return False, "최대 6명까지 참가할 수 있습니다."
    game["players"][discord_id] = new_player(discord_id, name)
    game["order"].append(discord_id)
    return True, f"{name}님이 참가했습니다. (현재 {len(game['players'])}명)"


def start_game(game: dict):
    if game["phase"] != "waiting":
        return False, "이미 시작된 게임입니다."
    if len(game["players"]) < 2:
        return False, "최소 2명 이상이어야 시작할 수 있습니다."
    random.shuffle(game["order"])
    game["phase"] = "playing"
    game["turn_index"] = 0
    first = game["players"][game["order"][0]]["name"]
    push_log(game, f"게임 시작! 순서: {', '.join(game['players'][d]['name'] for d in game['order'])}")
    return True, f"게임이 시작되었습니다! 첫 순서는 {first}님입니다."


def current_player_id(game: dict):
    if not game["order"]:
        return None
    return game["order"][game["turn_index"] % len(game["order"])]


# ---------- 내부 헬퍼 ----------

def _advance_turn(game: dict):
    game["doubles_streak"] = 0
    if not game["order"]:
        return
    game["turn_index"] = (game["turn_index"] + 1) % len(game["order"])


def _net_worth(game: dict, discord_id: str) -> int:
    p = game["players"][discord_id]
    worth = p["cash"]
    for tile_id, level in p["properties"].items():
        tile = BOARD[int(tile_id)]
        worth += tile["price"] + int(tile["price"] * BUILD_COST_RATIO) * level
    return worth


def _release_properties(game: dict, discord_id: str):
    p = game["players"][discord_id]
    for tile_id in list(p["properties"].keys()):
        game["ownership"].pop(tile_id, None)
    p["properties"] = {}


def _try_cover_debt(game: dict, discord_id: str):
    """현금이 마이너스면 건물을 팔아 충당, 그래도 안 되면 파산 처리"""
    p = game["players"][discord_id]
    tile_ids = sorted(p["properties"].keys(), key=lambda t: -p["properties"][t])
    for tile_id in tile_ids:
        while p["cash"] < 0 and p["properties"].get(tile_id, 0) > 0:
            tile = BOARD[int(tile_id)]
            refund = int(tile["price"] * BUILD_COST_RATIO * 0.5)
            p["properties"][tile_id] -= 1
            p["cash"] += refund
        if p["cash"] >= 0:
            break

    if p["cash"] < 0:
        # 파산: 소유 부동산 반환, 게임에서 제외
        p["bankrupt"] = True
        _release_properties(game, discord_id)
        push_log(game, f"💥 {p['name']}님이 파산했습니다!")
        if discord_id in game["order"]:
            idx = game["order"].index(discord_id)
            game["order"].remove(discord_id)
            if idx <= game["turn_index"] and game["turn_index"] > 0:
                game["turn_index"] -= 1
            if game["order"]:
                game["turn_index"] %= len(game["order"])
        _check_game_over(game)


def _check_game_over(game: dict):
    alive = [d for d in game["order"] if not game["players"][d]["bankrupt"]]
    if len(alive) <= 1 and game["phase"] == "playing":
        game["phase"] = "ended"
        if alive:
            winner_id = alive[0]
            game["winner"] = winner_id
            push_log(game, f"🏆 {game['players'][winner_id]['name']}님의 승리입니다!")
        else:
            push_log(game, "모든 플레이어가 파산하여 게임이 종료되었습니다.")


def _pay(game: dict, payer_id: str, amount: int, to_fund=False, to_player_id=None):
    payer = game["players"][payer_id]
    payer["cash"] -= amount
    if to_fund:
        game["fund"] += amount
    elif to_player_id:
        events.append("✨ 더블이 나와서 한 번 더 굴릴 수 있습니다!")
    else:
        _advance_turn(game)

    push_log(game, " / ".join(events))
    return True, "\n".join(events), {"events": events, "extra_turn": extra_turn, "moved": True}


def buy_property(game: dict, discord_id: str):
    discord_id = str(discord_id)
    if game["phase"] != "playing":
        return False, "게임이 진행중이 아닙니다."
    if current_player_id(game) != discord_id:
        return False, "당신의 차례가 아닙니다."
    p = game["players"][discord_id]
    tile = get_tile(p["position"])
    if tile["type"] != "city":
        return False, "이 칸은 구매할 수 없습니다."
    tile_id = str(tile["id"])
    if tile_id in game["ownership"]:
        return False, "이미 소유자가 있는 땅입니다."
    if p["cash"] < tile["price"]:
        return False, "돈이 부족합니다."
    p["cash"] -= tile["price"]
    p["properties"][tile_id] = 0
    game["ownership"][tile_id] = discord_id
    push_log(game, f"🏠 {p['name']}님이 {tile['name']}을(를) 구매했습니다. ({tile['price']:,}원)")
    return True, f"**{tile['name']}**을(를) {tile['price']:,}원에 구매했습니다!"


def build(game: dict, discord_id: str, levels: int = 1):
    discord_id = str(discord_id)
    if game["phase"] != "playing":
        return False, "게임이 진행중이 아닙니다."
    if current_player_id(game) != discord_id:
        return False, "당신의 차례가 아닙니다."
    p = game["players"][discord_id]
    tile = get_tile(p["position"])
    tile_id = str(tile["id"])
    if tile["type"] != "city" or game["ownership"].get(tile_id) != discord_id:
        return False, "내 소유의 땅에서만 건설할 수 있습니다."
    cur_level = p["properties"].get(tile_id, 0)
    if cur_level >= BUILD_MAX_LEVEL:
        return False, "이미 최고 단계(랜드마크)까지 건설되었습니다."
    levels = max(1, min(levels, BUILD_MAX_LEVEL - cur_level))
    cost = int(tile["price"] * BUILD_COST_RATIO) * levels
    if p["cash"] < cost:
        return False, f"건설 비용({cost:,}원)이 부족합니다."
    p["cash"] -= cost
    p["properties"][tile_id] = cur_level + levels
    push_log(game, f"🏗️ {p['name']}님이 {tile['name']}에 건물을 {levels}단계 올렸습니다. (Lv.{cur_level + levels})")
    return True, f"**{tile['name']}**을(를) Lv.{cur_level + levels}(으)로 건설했습니다! (-{cost:,}원)"


def escape_island(game: dict, discord_id: str):
    discord_id = str(discord_id)
    if game["phase"] != "playing":
        return False, "게임이 진행중이 아닙니다."
    if current_player_id(game) != discord_id:
        return False, "당신의 차례가 아닙니다."
    p = game["players"][discord_id]
    if p["island_turns"] <= 0:
        return False, "무인도에 있지 않습니다."
    if p["get_out_cards"] > 0:
        p["get_out_cards"] -= 1
        p["island_turns"] = 0
        return True, "🎫 무인도 탈출 카드를 사용해 즉시 탈출했습니다!"

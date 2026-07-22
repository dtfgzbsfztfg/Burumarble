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
        game["players"][to_player_id]["cash"] += amount
    if payer["cash"] < 0:
        _try_cover_debt(game, payer_id)


def _send_to_island(player: dict):
    player["position"] = ISLAND_TILE_ID
    player["island_turns"] = ISLAND_SKIP_TURNS


# ---------- 타일 도착 처리 ----------

def _resolve_landing(game: dict, discord_id: str, events: list):
    p = game["players"][discord_id]
    tile = get_tile(p["position"])
    tile_id = str(tile["id"])
    ttype = tile["type"]

    if ttype == "city":
        owner = game["ownership"].get(tile_id)
        if owner is None:
            events.append(f"🏙️ **{tile['name']}** (구매가 {tile['price']:,}원) - 비어있는 땅입니다. `/구매`로 살 수 있어요.")
        elif owner == discord_id:
            events.append(f"🏙️ **{tile['name']}** - 내 소유 땅입니다.")
        else:
            level = game["players"][owner]["properties"].get(tile_id, 0)
            rent = int(tile["price"] * 0.1 * RENT_MULTIPLIER[level])
            _pay(game, discord_id, rent, to_player_id=owner)
            owner_name = game["players"][owner]["name"]
            events.append(f"🏙️ **{tile['name']}** (Lv.{level}) - {owner_name}님 소유! 통행료 {rent:,}원을 지불했습니다.")

    elif ttype == "tax":
        amount = tile["amount"]
        _pay(game, discord_id, amount, to_fund=True)
        events.append(f"💸 **{tile['name']}**: {amount:,}원을 세금으로 냈습니다. (사회복지기금 적립)")

    elif ttype == "card":
        card = draw_card()
        events.append(f"🎴 황금열쇠: {card['desc']}")
        _apply_card(game, discord_id, card, events)

    elif ttype == "go_island":
        _send_to_island(p)
        events.append("🏝️ 무인도로 이동했습니다! 다음 턴부터 최대 2턴을 쉽니다.")

    elif ttype == "island":
        events.append("🏝️ 무인도에 방문했습니다. (그냥 지나가는 중이라면 아무 일도 없어요)")

    elif ttype == "fund":
        amount = game["fund"]
        game["fund"] = 0
        p["cash"] += amount
        events.append(f"🎉 사회복지기금 **{amount:,}원**을 모두 획득했습니다!")

    elif ttype == "space":
        dest = random.randint(0, BOARD_SIZE - 1)
        p["position"] = dest
        events.append(f"🚀 우주여행! **{BOARD[dest]['name']}**(으)로 순간이동했습니다.")
        _resolve_landing(game, discord_id, events)  # 이동한 칸 효과도 적용

    elif ttype == "start":
        events.append("🏁 출발점입니다.")


def _apply_card(game: dict, discord_id: str, card: dict, events: list):
    p = game["players"][discord_id]
    ctype = card["type"]
    value = card["value"]

    if ctype == "gain":
        p["cash"] += value
    elif ctype == "lose":
        _pay(game, discord_id, value, to_fund=True)
    elif ctype == "move_relative":
        old_pos = p["position"]
        new_pos = (p["position"] + value) % BOARD_SIZE
        if value > 0 and new_pos < old_pos:
            p["cash"] += GO_BONUS
            events.append(f"➡️ 출발점을 통과하여 {GO_BONUS:,}원을 받았습니다!")
        p["position"] = new_pos
        events.append(f"➡️ **{BOARD[new_pos]['name']}**(으)로 이동합니다.")
        _resolve_landing(game, discord_id, events)
    elif ctype == "goto_island":
        _send_to_island(p)
    elif ctype == "get_out_free":
        p["get_out_cards"] += 1
    elif ctype == "collect_from_all":
        for other_id in game["order"]:
            if other_id != discord_id and not game["players"][other_id]["bankrupt"]:
                _pay(game, other_id, value, to_player_id=discord_id)
    elif ctype == "pay_all":
        for other_id in game["order"]:
            if other_id != discord_id and not game["players"][other_id]["bankrupt"]:
                _pay(game, discord_id, value, to_player_id=other_id)


# ---------- 플레이어 액션 ----------

def roll_dice(game: dict, discord_id: str):
    discord_id = str(discord_id)
    if game["phase"] != "playing":
        return False, "게임이 진행중이 아닙니다.", None
    if current_player_id(game) != discord_id:
        return False, "당신의 차례가 아닙니다.", None
    if game.get("turn_stage") == "decide":
        return False, "먼저 이번 땅을 살지 결정해주세요. (`/구매` 또는 `/턴종료`)", None

    p = game["players"][discord_id]
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    game["last_roll"] = [d1, d2]
    is_double = d1 == d2
    events = [f"🎲 {p['name']}님이 주사위를 굴렸습니다: {d1} + {d2} = {d1 + d2}"]
    extra_turn = False

    if p["island_turns"] > 0:
        if is_double:
            p["island_turns"] = 0
            events.append("✨ 더블이 나와 무인도에서 탈출했습니다!")
        else:
            p["island_turns"] -= 1
            events.append(f"🏝️ 무인도에서 대기 중입니다. (남은 턴: {p['island_turns']})")
            _advance_turn(game)
            push_log(game, " / ".join(events))
            return True, "\n".join(events), {"events": events, "extra_turn": False, "moved": False}

    # 이동
    if is_double:
        game["doubles_streak"] += 1
    else:
        game["doubles_streak"] = 0

    if game["doubles_streak"] >= 3:
        _send_to_island(p)
        events.append("🚨 더블을 3번 연속으로 굴려 무인도로 보내졌습니다!")
        game["doubles_streak"] = 0
        _advance_turn(game)
        push_log(game, " / ".join(events))
        return True, "\n".join(events), {"events": events, "extra_turn": False, "moved": False}

    old_pos = p["position"]
    new_pos = (old_pos + d1 + d2) % BOARD_SIZE
    if new_pos < old_pos:
        p["cash"] += GO_BONUS
        events.append(f"🏁 출발점을 통과하여 {GO_BONUS:,}원을 받았습니다!")
    p["position"] = new_pos
    events.append(f"📍 **{BOARD[new_pos]['name']}**에 도착했습니다.")

    _resolve_landing(game, discord_id, events)

    final_tile = get_tile(p["position"])
    final_tile_id = str(final_tile["id"])
    is_extra_eligible = is_double and not p["bankrupt"] and p["island_turns"] == 0
    needs_decision = (
        final_tile["type"] == "city"
        and final_tile_id not in game["ownership"]
        and p["cash"] >= 0
        and not p["bankrupt"]
    )

    if needs_decision:
        game["turn_stage"] = "decide"
        game["pending_double"] = is_extra_eligible
        events.append("🤔 이 땅을 구매하시겠어요? `/구매` 또는 `/턴종료`로 결정해주세요.")
    elif is_extra_eligible:
        extra_turn = True
        events.append("✨ 더블이 나와서 한 번 더 굴릴 수 있습니다!")
    else:
        _advance_turn(game)

    push_log(game, " / ".join(events))
    return True, "\n".join(events), {"events": events, "extra_turn": extra_turn, "moved": True, "needs_decision": needs_decision}


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

    msg = f"**{tile['name']}**을(를) {tile['price']:,}원에 구매했습니다!"
    msg += _resolve_pending_decision(game)
    return True, msg


def end_turn(game: dict, discord_id: str):
    """빈 땅을 구매하지 않고 턴을 넘길 때 사용"""
    discord_id = str(discord_id)
    if game["phase"] != "playing":
        return False, "게임이 진행중이 아닙니다."
    if current_player_id(game) != discord_id:
        return False, "당신의 차례가 아닙니다."
    if game.get("turn_stage") != "decide":
        return False, "지금은 턴을 넘길 필요가 없습니다."
    msg = "이 땅은 구매하지 않았습니다."
    msg += _resolve_pending_decision(game)
    return True, msg


def _resolve_pending_decision(game: dict) -> str:
    """구매/패스 결정 이후 다음 굴림 또는 다음 차례로 진행. 안내 메시지 조각을 반환."""
    if game.get("turn_stage") != "decide":
        return ""
    game["turn_stage"] = "roll"
    if game.get("pending_double"):
        game["pending_double"] = False
        return "\n✨ 더블이었으니 한 번 더 `/주사위`를 굴릴 수 있습니다!"
    game["pending_double"] = False
    _advance_turn(game)
    nxt = current_player_id(game)
    if nxt:
        return f"\n➡️ 다음 차례: {game['players'][nxt]['name']}"
    return ""


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
    if p["cash"] < ISLAND_ESCAPE_FEE:
        return False, f"탈출 비용({ISLAND_ESCAPE_FEE:,}원)이 부족합니다."
    p["cash"] -= ISLAND_ESCAPE_FEE
    p["island_turns"] = 0
    return True, f"💰 {ISLAND_ESCAPE_FEE:,}원을 내고 무인도에서 탈출했습니다!"


def force_end_game(game: dict):
    if game["phase"] == "ended":
        return
    game["phase"] = "ended"
    if game["order"]:
        winner_id = max(game["order"], key=lambda d: _net_worth(game, d))
        game["winner"] = winner_id
        push_log(game, f"🏆 게임 종료! 순자산 기준 승자: {game['players'][winner_id]['name']}")


# ---------- 조회용 ----------

def player_status_text(game: dict, discord_id: str) -> str:
    discord_id = str(discord_id)
    p = game["players"][discord_id]
    tile = get_tile(p["position"])
    lines = [
        f"**{p['name']}**",
        f"💰 자산: {p['cash']:,}원 (순자산 {_net_worth(game, discord_id):,}원)",
        f"📍 위치: {tile['name']}",
    ]
    if p["island_turns"] > 0:
        lines.append(f"🏝️ 무인도 대기 턴: {p['island_turns']}")
    if p["get_out_cards"] > 0:
        lines.append(f"🎫 무인도 탈출 카드: {p['get_out_cards']}장")
    if p["properties"]:
        props = ", ".join(f"{BOARD[int(t)]['name']}(Lv.{lv})" for t, lv in p["properties"].items())
        lines.append(f"🏠 보유 부동산: {props}")
    else:
        lines.append("🏠 보유 부동산: 없음")
    if p["bankrupt"]:
        lines.append("💥 파산했습니다.")
    return "\n".join(lines)


def board_summary_text(game: dict) -> str:
    lines = [f"💰 사회복지기금: {game['fund']:,}원"]
    for tile_id, owner_id in sorted(game["ownership"].items(), key=lambda kv: int(kv[0])):
        tile = BOARD[int(tile_id)]
        level = game["players"][owner_id]["properties"].get(tile_id, 0)
        lines.append(f"- {tile['name']}: {game['players'][owner_id]['name']} (Lv.{level})")
    if len(lines) == 1:
        lines.append("(아직 소유된 땅이 없습니다)")
    return "\n".join(lines)


def turn_order_text(game: dict) -> str:
    parts = []
    for i, d in enumerate(game["order"]):
        marker = "👉 " if i == game["turn_index"] % max(len(game["order"]), 1) else ""
        parts.append(f"{marker}{game['players'][d]['name']}")
    return " → ".join(parts)

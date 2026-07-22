# -*- coding: utf-8 -*-
"""황금열쇠 카드"""
import random

# type: gain, lose, move_relative, goto_island, get_out_free, collect_from_all, pay_all
CARDS = [
    {"desc": "은행 이자를 받았습니다.", "type": "gain", "value": 100_000},
    {"desc": "복권에 당첨되었습니다!", "type": "gain", "value": 300_000},
    {"desc": "세무 조사를 받아 벌금을 냈습니다.", "type": "lose", "value": 150_000},
    {"desc": "건물 수리비가 발생했습니다.", "type": "lose", "value": 100_000},
    {"desc": "3칸 앞으로 이동합니다.", "type": "move_relative", "value": 3},
    {"desc": "2칸 뒤로 이동합니다.", "type": "move_relative", "value": -2},
    {"desc": "무인도로 이동합니다.", "type": "goto_island", "value": None},
    {"desc": "무인도 탈출 카드를 획득했습니다.", "type": "get_out_free", "value": None},
    {"desc": "모든 플레이어에게 5만원씩 받습니다.", "type": "collect_from_all", "value": 50_000},
    {"desc": "모든 플레이어에게 5만원씩 지불합니다.", "type": "pay_all", "value": 50_000},
]


def draw_card() -> dict:
    return random.choice(CARDS)

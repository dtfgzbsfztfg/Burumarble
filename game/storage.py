# -*- coding: utf-8 -*-
"""게임 상태를 채널별 JSON 파일로 저장 (봇 재시작에도 게임 유지)"""
import json
import os

DATA_DIR = os.getenv(
    "DATA_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"),
)
os.makedirs(DATA_DIR, exist_ok=True)


def _path(channel_id: str) -> str:
    return os.path.join(DATA_DIR, f"{channel_id}.json")


def save_game(game: dict):
    with open(_path(game["channel_id"]), "w", encoding="utf-8") as f:
        json.dump(game, f, ensure_ascii=False, indent=2)


def load_game(channel_id: str):
    path = _path(str(channel_id))
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_game(channel_id: str):
    path = _path(str(channel_id))
    if os.path.exists(path):
        os.remove(path)

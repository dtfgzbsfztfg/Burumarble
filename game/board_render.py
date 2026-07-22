# -*- coding: utf-8 -*-
"""보드를 SVG 이미지로 렌더링 (타일 배치, 소유/건물 표시, 플레이어 말 위치)"""
from .board import BOARD

CELL = 74
GRID = 8  # 한 변에 8칸씩, 코너 공유 → 총 32칸 둘레
MARGIN = 24
SIZE = CELL * GRID + MARGIN * 2

TILE_COLORS = {
    "start": "#2ecc71",
    "city": "#ffffff",
    "tax": "#e74c3c",
    "card": "#9b59b6",
    "island": "#8d6e63",
    "go_island": "#e67e22",
    "fund": "#f1c40f",
    "space": "#3498db",
}

PLAYER_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]

FONT = "'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif"

# 토큰이 겹칠 때 살짝 벌려서 배치할 오프셋
TOKEN_OFFSETS = [(-14, -10), (14, -10), (-14, 10), (14, 10), (0, -20), (0, 20)]


def _tile_grid_pos(i: int):
    """32칸 인덱스를 8x8 격자 둘레의 (col, row) 좌표로 변환"""
    if i < 8:
        return 8 - i, 8
    if i < 16:
        off = i - 8
        return 0, 8 - off
    if i < 24:
        off = i - 16
        return off, 0
    off = i - 24
    return 8, off


def _wrap_name(name: str):
    if len(name) <= 4:
        return [name]
    mid = (len(name) + 1) // 2
    return [name[:mid], name[mid:]]


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_board_svg(game: dict) -> str:
    players = game["players"]
    order_ids = list(players.keys())  # 참가 순서를 색상 배정 기준으로 고정 사용
    color_of = {pid: PLAYER_COLORS[i % len(PLAYER_COLORS)] for i, pid in enumerate(order_ids)}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" '
        f'viewBox="0 0 {SIZE} {SIZE}" font-family="{FONT}">',
        f'<rect x="0" y="0" width="{SIZE}" height="{SIZE}" fill="#1e2124"/>',
    ]

    # ---- 타일 32개 ----
    for i, tile in enumerate(BOARD):
        col, row = _tile_grid_pos(i)
        x = MARGIN + col * CELL
        y = MARGIN + row * CELL
        color = TILE_COLORS.get(tile["type"], "#ffffff")
        owner = game["ownership"].get(str(tile["id"]))

        parts.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
            f'fill="{color}" stroke="#111318" stroke-width="1.5"/>'
        )

        # 소유/건물 표시 (하단 바)
        if owner:
            level = players[owner]["properties"].get(str(tile["id"]), 0)
            ocolor = color_of.get(owner, "#888888")
            oname = _esc(players[owner]["name"][:3])
            parts.append(
                f'<rect x="{x+3}" y="{y+CELL-15}" width="{CELL-6}" height="12" '
                f'fill="{ocolor}" opacity="0.9" rx="2"/>'
            )
            parts.append(
                f'<text x="{x+CELL/2}" y="{y+CELL-6}" font-size="9" fill="#ffffff" '
                f'text-anchor="middle">{oname} 🏠Lv{level}</text>'
            )
        elif tile["type"] == "city":
            parts.append(
                f'<text x="{x+CELL/2}" y="{y+CELL-6}" font-size="8" fill="#888888" '
                f'text-anchor="middle">{tile["price"]//10000}만원</text>'
            )

        # 타일 이름
        lines = _wrap_name(tile["name"])
        ty = y + 17 if len(lines) == 1 else y + 14
        for li, line in enumerate(lines):
            parts.append(
                f'<text x="{x+CELL/2}" y="{ty + li*11}" font-size="10.5" fill="#111111" '
                f'text-anchor="middle" font-weight="600">{_esc(line)}</text>'
            )

    # ---- 중앙 정보 패널 ----
    center = MARGIN + CELL * GRID / 2
    parts.append(
        f'<text x="{center}" y="{center-28}" font-size="26" fill="#ffffff" '
        f'text-anchor="middle" font-weight="bold">🎲 부루마블</text>'
    )
    parts.append(
        f'<text x="{center}" y="{center+6}" font-size="15" fill="#f1c40f" '
        f'text-anchor="middle">💰 사회복지기금 {game["fund"]:,}원</text>'
    )
    if game["phase"] == "playing" and game["order"]:
        cur_id = game["order"][game["turn_index"] % len(game["order"])]
        stage_txt = " (구매 결정 대기중)" if game.get("turn_stage") == "decide" else ""
        parts.append(
            f'<text x="{center}" y="{center+32}" font-size="14" fill="#2ecc71" '
            f'text-anchor="middle">👉 현재 차례: {_esc(players[cur_id]["name"])}{stage_txt}</text>'
        )
    elif game["phase"] == "ended" and game.get("winner"):
        parts.append(
            f'<text x="{center}" y="{center+32}" font-size="14" fill="#f1c40f" '
            f'text-anchor="middle">🏆 승자: {_esc(players[game["winner"]]["name"])}</text>'
        )

    # ---- 플레이어 말 ----
    tile_occupants = {}
    for pid, p in players.items():
        if p["bankrupt"]:
            continue
        tile_occupants.setdefault(p["position"], []).append(pid)

    for pos, pids in tile_occupants.items():
        col, row = _tile_grid_pos(pos)
        cx0 = MARGIN + col * CELL + CELL / 2
        cy0 = MARGIN + row * CELL + CELL / 2 - 8
        for idx, pid in enumerate(pids):
            dx, dy = TOKEN_OFFSETS[idx % len(TOKEN_OFFSETS)]
            cx, cy = cx0 + dx, cy0 + dy
            color = color_of.get(pid, "#888888")
            initial = _esc(players[pid]["name"][:1])
            parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="10" fill="{color}" stroke="#111111" stroke-width="1.5"/>'
            )
            parts.append(
                f'<text x="{cx}" y="{cy+4}" font-size="11" fill="#ffffff" '
                f'text-anchor="middle" font-weight="bold">{initial}</text>'
            )

    parts.append("</svg>")
    return "".join(parts)

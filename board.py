# -*- coding: utf-8 -*-
"""부루마블 보드 데이터 (32칸 순환)"""

# type 종류:
#  start      : 출발점 (통과/도착 시 보너스)
#  city       : 구매 가능한 도시 (rent 발생)
#  tax        : 세금 납부
#  card       : 황금열쇠 카드 뽑기
#  island     : 무인도 (수감 위치)
#  go_island  : 무인도로 강제 이동
#  fund       : 사회복지기금 (누적된 세금을 획득)
#  space      : 우주여행 (랜덤 위치로 순간이동)

BOARD = [
    {"id": 0,  "name": "출발",         "type": "start"},
    {"id": 1,  "name": "서울",         "type": "city", "price": 200_000},
    {"id": 2,  "name": "황금열쇠",      "type": "card"},
    {"id": 3,  "name": "도쿄",         "type": "city", "price": 220_000},
    {"id": 4,  "name": "베이징",       "type": "city", "price": 250_000},
    {"id": 5,  "name": "소득세",       "type": "tax", "amount": 150_000},
    {"id": 6,  "name": "뉴욕",         "type": "city", "price": 300_000},
    {"id": 7,  "name": "무인도",       "type": "island"},
    {"id": 8,  "name": "파리",         "type": "city", "price": 280_000},
    {"id": 9,  "name": "황금열쇠",      "type": "card"},
    {"id": 10, "name": "런던",         "type": "city", "price": 320_000},
    {"id": 11, "name": "로마",         "type": "city", "price": 260_000},
    {"id": 12, "name": "재산세",       "type": "tax", "amount": 200_000},
    {"id": 13, "name": "시드니",       "type": "city", "price": 300_000},
    {"id": 14, "name": "두바이",       "type": "city", "price": 350_000},
    {"id": 15, "name": "무인도로 가라", "type": "go_island"},
    {"id": 16, "name": "홍콩",         "type": "city", "price": 300_000},
    {"id": 17, "name": "황금열쇠",      "type": "card"},
    {"id": 18, "name": "싱가포르",      "type": "city", "price": 320_000},
    {"id": 19, "name": "방콕",         "type": "city", "price": 240_000},
    {"id": 20, "name": "사회복지기금",  "type": "fund"},
    {"id": 21, "name": "모스크바",      "type": "city", "price": 350_000},
    {"id": 22, "name": "카이로",       "type": "city", "price": 280_000},
    {"id": 23, "name": "황금열쇠",      "type": "card"},
    {"id": 24, "name": "리우데자네이루", "type": "city", "price": 300_000},
    {"id": 25, "name": "특별세",       "type": "tax", "amount": 250_000},
    {"id": 26, "name": "토론토",       "type": "city", "price": 320_000},
    {"id": 27, "name": "멕시코시티",    "type": "city", "price": 260_000},
    {"id": 28, "name": "우주여행",      "type": "space"},
    {"id": 29, "name": "뭄바이",       "type": "city", "price": 300_000},
    {"id": 30, "name": "황금열쇠",      "type": "card"},
    {"id": 31, "name": "상하이",       "type": "city", "price": 340_000},
]

BOARD_SIZE = len(BOARD)

# 건물 단계: 0(땅만) ~ 4(랜드마크/호텔급)
BUILD_MAX_LEVEL = 4
RENT_MULTIPLIER = {0: 1.0, 1: 2.0, 2: 3.5, 3: 5.0, 4: 8.0}
BUILD_COST_RATIO = 0.5  # 단계 1회 상승 비용 = price * 0.5

ISLAND_TILE_ID = 7
GO_BONUS = 500_000
START_CASH = 3_000_000
ISLAND_SKIP_TURNS = 2
ISLAND_ESCAPE_FEE = 200_000


def get_tile(position: int) -> dict:
    return BOARD[position % BOARD_SIZE]

# 🎲 디코 부루마블 봇

디스코드 슬래시 커맨드로 즐기는 부루마블(모두의마블 스타일) 게임 봇입니다.
32칸 보드, 땅 구매/건설, 통행료, 세금, 무인도(수감), 황금열쇠 카드, 사회복지기금, 우주여행 등의
확장 규칙을 포함합니다. 게임 상태는 채널별 JSON 파일로 저장되어 봇을 재시작해도 이어집니다.

## 1. 디스코드 봇 만들기

1. https://discord.com/developers/applications 에서 New Application 생성
2. 왼쪽 메뉴 **Bot** → Reset Token 으로 토큰 발급 (`.env`에 넣을 값)
3. **Bot** 탭에서 별도 Privileged Intent는 켤 필요 없습니다 (메시지 내용 읽지 않음, 슬래시 커맨드만 사용)
4. **OAuth2 → URL Generator**
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Use Slash Commands`
   - 생성된 URL로 봇을 서버에 초대

## 2. 로컬/VPS 설치

```bash
# 1) 압축 해제 후 폴더 진입
cd burumarble_bot

# 2) 가상환경 (권장)
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3) 패키지 설치
pip install -r requirements.txt

# 4) 토큰 설정
cp .env.example .env
# .env 파일을 열어 DISCORD_TOKEN=발급받은토큰 으로 수정

# 5) 실행
python bot.py
```

처음 실행 시 콘솔에 `슬래시 커맨드 N개 동기화 완료`가 뜨면 정상입니다.
(글로벌 슬래시 커맨드 반영은 최대 1시간 정도 걸릴 수 있어요. 바로 테스트하려면
디스코드 서버에서 한 번 나갔다 들어오거나, 새 채널에서 `/` 입력 후 잠시 기다려 보세요.)

## 3. Railway로 배포하기 (VPS 없이 가장 쉬운 방법)

이 프로젝트에는 이미 Railway용 `Procfile`이 포함되어 있습니다.

1. https://railway.app 가입 → **New Project → Deploy from GitHub repo**
   (GitHub에 이 폴더를 올린 저장소를 선택하세요. GitHub 없이 하려면 Railway CLI로 `railway up`도 가능합니다.)
2. 프로젝트 생성 후 **Variables** 탭에서 환경변수 추가:
   - `DISCORD_TOKEN` = 발급받은 봇 토큰
3. **Settings → Deploy**에서 Start Command가 비어있다면 `python bot.py`로 지정
   (Procfile이 있으면 보통 자동 인식되어 `worker: python bot.py`가 실행됩니다)
4. 배포가 끝나면 로그 탭에서 `슬래시 커맨드 N개 동기화 완료`가 뜨는지 확인

**⚠️ 게임 데이터 유지 관련 주의:** 이 봇은 게임 상태를 `data/*.json` 파일로 저장합니다.
Railway는 기본적으로 컨테이너가 재배포될 때 파일시스템이 초기화되므로, 진행 중이던 게임이 사라질 수 있습니다.
계속 유지하려면:
- Railway 프로젝트의 **Volumes** 기능으로 볼륨을 마운트하면 재배포 후에도 게임이 유지됩니다.
  (Service → Settings → Volumes → Add Volume, Mount Path를 예: `/data`로 지정)
  이후 환경변수에 `DATA_DIR=/data`를 추가하면 봇이 그 경로에 저장합니다. (안 정하면 기본값 `./data` 사용)
- 짧게 즐기고 끝낼 거라면 볼륨 없이 그냥 써도 무방합니다 (재배포/재시작 전까지는 정상 유지됨).

CLI로 배포하고 싶다면:

```bash
npm install -g @railway/cli
railway login
cd burumarble_bot
railway init
railway variables set DISCORD_TOKEN=발급받은토큰
railway up
```

## 4. VPS에서 계속 켜두기 (systemd 예시, 선택사항)

```ini
# /etc/systemd/system/burumarble.service
[Unit]
Description=Burumarble Discord Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/유저명/burumarble_bot
ExecStart=/home/유저명/burumarble_bot/venv/bin/python bot.py
Restart=always
RestartSec=5
EnvironmentFile=/home/유저명/burumarble_bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now burumarble
sudo systemctl status burumarble   # 상태 확인
journalctl -u burumarble -f        # 로그 확인
```

## 5. 게임 진행 커맨드

| 커맨드 | 설명 |
|---|---|
| `/부루마블-생성` | 현재 채널에 새 게임 생성 |
| `/부루마블-참가` | 게임에 참가 (2~6명) |
| `/부루마블-시작` | 참가 인원이 모이면 게임 시작 (순서 랜덤 셔플) |
| `/주사위` | 주사위를 굴려 이동, 도착 칸 효과 자동 적용 |
| `/구매` | 현재 위치한 빈 땅 구매 |
| `/건설 [단계]` | 내 소유 땅에 건물 단계 올리기 (최대 Lv.4) |
| `/무인도탈출` | 무인도에서 탈출카드 또는 20만원으로 즉시 탈출 |
| `/상태` | 내 자산/위치/보유 부동산 확인 |
| `/보드` | 전체 보드 소유 현황 + 턴 순서 확인 |
| `/부루마블-종료` | 게임 강제 종료 (순자산 최고자가 승리) |

## 6. 규칙 요약

- 시작 자금: 300만원 / 출발점 통과 시 50만원 지급
- 땅 통행료 = 가격의 10% × 건물 배율(Lv0:1배 ~ Lv4:8배)
- 건설 비용 = 가격의 50% × 올릴 단계 수
- 더블(같은 눈)이 나오면 한 번 더 턴 진행, 3연속 더블 시 무인도行
- 무인도: 기본 2턴 대기, 대기 중 더블이 나오면 즉시 탈출
- 세금 낸 금액은 **사회복지기금**에 적립되며, 기금 칸에 도착하면 전액 획득
- 우주여행 칸: 보드 위 랜덤 칸으로 순간이동 (도착 칸 효과도 적용됨)
- 파산: 현금이 마이너스가 되면 건물부터 매각, 그래도 부족하면 파산 처리 후 보유 부동산 반환
- 최후의 1인이 남으면 자동 승리, `/부루마블-종료`로 강제 종료 시 순자산(현금+부동산가치) 최고자가 승리

## 7. 커스터마이징 팁

- 보드 칸/가격/카드 내용: `game/board.py`, `game/cards.py` 에서 자유롭게 수정 가능
- 시작 자금, 세금액, 건물 배율 등 숫자 값도 `game/board.py` 상단 상수에서 조절
- 최대 인원(현재 6명)은 `game/engine.py`의 `join_game` 함수에서 변경

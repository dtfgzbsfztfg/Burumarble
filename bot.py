# -*- coding: utf-8 -*-
"""부루마블 디스코드 봇"""
import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from game import engine, storage

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!부루마블-", intents=intents)

COLOR = 0x2ECC71
COLOR_ERR = 0xE74C3C


def _get_game(channel_id):
    return storage.load_game(str(channel_id))


def _save(game):
    storage.save_game(game)


def _embed(title: str, desc: str, color=COLOR):
    return discord.Embed(title=title, description=desc, color=color)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"슬래시 커맨드 {len(synced)}개 동기화 완료")
    except Exception as e:
        print(f"동기화 실패: {e}")
    print(f"{bot.user} 로그인 완료")


@bot.tree.command(name="부루마블-생성", description="이 채널에 새 부루마블 게임을 만듭니다.")
async def create(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    existing = _get_game(channel_id)
    if existing and existing["phase"] != "ended":
        await interaction.response.send_message(embed=_embed("⚠️ 오류", "이미 진행중인 게임이 있습니다. `/부루마블-종료`로 먼저 종료하세요.", COLOR_ERR))
        return
    game = engine.create_game(channel_id)
    _save(game)
    await interaction.response.send_message(embed=_embed(
        "🎲 부루마블 게임 생성됨!",
        "`/부루마블-참가`로 참가한 뒤, 방장이 `/부루마블-시작`으로 게임을 시작하세요. (2~6명)"
    ))


@bot.tree.command(name="부루마블-참가", description="현재 채널의 게임에 참가합니다.")
async def join(interaction: discord.Interaction):
    game = _get_game(interaction.channel_id)
    if not game:
        await interaction.response.send_message(embed=_embed("⚠️ 오류", "먼저 `/부루마블-생성`으로 게임을 만드세요.", COLOR_ERR))
        return
    ok, msg = engine.join_game(game, interaction.user.id, interaction.user.display_name)
    _save(game)
    await interaction.response.send_message(embed=_embed("참가" if ok else "⚠️ 오류", msg, COLOR if ok else COLOR_ERR))


@bot.tree.command(name="부루마블-시작", description="게임을 시작합니다.")
async def start(interaction: discord.Interaction):
    game = _get_game(interaction.channel_id)
    if not game:
        await interaction.response.send_message(embed=_embed("⚠️ 오류", "먼저 `/부루마블-생성`으로 게임을 만드세요.", COLOR_ERR))
        return
    ok, msg = engine.start_game(game)
    _save(game)
    if ok:
        msg += f"\n\n순서: {engine.turn_order_text(game)}"
    await interaction.response.send_message(embed=_embed("게임 시작" if ok else "⚠️ 오류", msg, COLOR if ok else COLOR_ERR))


@bot.tree.command(name="주사위", description="주사위를 굴려 이동합니다.")
async def roll(interaction: discord.Interaction):
    game = _get_game(interaction.channel_id)
    if not game:
        await interaction.response.send_message(embed=_embed("⚠️ 오류", "진행중인 게임이 없습니다.", COLOR_ERR))
        return
    ok, msg, result = engine.roll_dice(game, interaction.user.id)
    _save(game)
    if not ok:
        await interaction.response.send_message(embed=_embed("⚠️ 오류", msg, COLOR_ERR))
        return
    embed = _embed("🎲 주사위 결과", msg)
    if game["phase"] == "ended":
        embed.add_field(name="게임 종료", value=f"🏆 승자: {game['players'][game['winner']]['name']}", inline=False)
    else:
        next_id = engine.current_player_id(game)
        embed.add_field(name="다음 차례", value=game["players"][next_id]["name"], inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="구매", description="현재 위치한 땅을 구매합니다.")
async def buy(interaction: discord.Interaction):
    game = _get_game(interaction.channel_id)
    if not game:
        await interaction.response.send_message(embed=_embed("⚠️ 오류", "진행중인 게임이 없습니다.", COLOR_ERR))
        return
    ok, msg = engine.buy_property(game, interaction.user.id)
    _save(game)
    await interaction.response.send_message(embed=_embed("구매" if ok else "⚠️ 오류", msg, COLOR if ok else COLOR_ERR))


@bot.tree.command(name="건설", description="현재 위치한 내 소유 땅에 건물을 짓습니다.")
@app_commands.describe(단계="올릴 단계 수 (기본 1)")
async def construct(interaction: discord.Interaction, 단계: int = 1):
    game = _get_game(interaction.channel_id)
    if not game:
        await interaction.response.send_message(embed=_embed("⚠️ 오류", "진행중인 게임이 없습니다.", COLOR_ERR))
        return
    ok, msg = engine.build(game, interaction.user.id, 단계)
    _save(game)
    await interaction.response.send_message(embed=_embed("건설" if ok else "⚠️ 오류", msg, COLOR if ok else COLOR_ERR))


@bot.tree.command(name="무인도탈출", description="무인도에서 탈출을 시도합니다. (탈출카드 또는 20만원)")
async def escape(interaction: discord.Interaction):
    game = _get_game(interaction.channel_id)
    if not game:
        await interaction.response.send_message(embed=_embed("⚠️ 오류", "진행중인 게임이 없습니다.", COLOR_ERR))
        return
    ok, msg = engine.escape_island(game, interaction.user.id)
    _save(game)
    await interaction.response.send_message(embed=_embed("무인도 탈출" if ok else "⚠️ 오류", msg, COLOR if ok else COLOR_ERR))


@bot.tree.command(name="상태", description="내 상태를 확인합니다.")
async def status(interaction: discord.Interaction):
    game = _get_game(interaction.channel_id)
    if not game or str(interaction.user.id) not in game["players"]:
        await interaction.response.send_message(embed=_embed("⚠️ 오류", "게임에 참가하지 않았습니다.", COLOR_ERR))
        return
    text = engine.player_status_text(game, interaction.user.id)
    await interaction.response.send_message(embed=_embed("📊 내 상태", text))


@bot.tree.command(name="보드", description="보드 전체 소유 현황을 봅니다.")
async def board(interaction: discord.Interaction):
    game = _get_game(interaction.channel_id)
    if not game:
        await interaction.response.send_message(embed=_embed("⚠️ 오류", "진행중인 게임이 없습니다.", COLOR_ERR))
        return
    text = engine.board_summary_text(game)
    order_text = engine.turn_order_text(game) if game["phase"] == "playing" else "-"
    embed = _embed("🗺️ 보드 현황", text)
    embed.add_field(name="턴 순서", value=order_text, inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="부루마블-종료", description="현재 채널의 게임을 강제 종료합니다.")
async def end(interaction: discord.Interaction):
    game = _get_game(interaction.channel_id)
    if not game:
        await interaction.response.send_message(embed=_embed("⚠️ 오류", "진행중인 게임이 없습니다.", COLOR_ERR))
        return
    engine.force_end_game(game)
    _save(game)
    storage.delete_game(interaction.channel_id)
    winner_name = game["players"][game["winner"]]["name"] if game.get("winner") else "없음"
    await interaction.response.send_message(embed=_embed("게임 종료", f"게임을 종료했습니다.\n🏆 최종 승자: {winner_name}"))


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("환경변수 DISCORD_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")
    bot.run(TOKEN)

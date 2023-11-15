import sqlite3
import traceback

import discord
import requests
from discord.ext import commands
from discord.ext import tasks
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access the token variable
token = os.getenv('token')
GUILD_ID = #your guild id




bot = commands.Bot(command_prefix='>', intents=discord.Intents.all())
conn = sqlite3.connect('players.db')
cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS players
             (id INTEGER PRIMARY KEY AUTOINCREMENT, time INTEGER, name REAL, discord_id TEXT)''')

conn.commit()



@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))
    isnewpb.start()



@discord.ext.tasks.loop(seconds=15)
async def isnewpb():


    c = conn.cursor()
    c.execute("SELECT name, discord_id FROM players")
    rows = c.fetchall()
    for row in rows:
        player_name, discord_id = row
        guild = bot.get_guild(GUILD_ID)  # Replace GUILD_ID with your actual guild ID
        mode = 'normal'  # Replace with the specific mode you want to check
        url = f'https://mcplayhd.net/api/v1/fastbuilder/{mode}/stats/{player_name}'
        headers = {
            'Authorization': f'Bearer {token}'
        }
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                # Parse the response and check for personal best
                current_best = response.json().get('data', {}).get('stats', {}).get('timeBest')
                current_best = current_best / 1000
                c.execute("SELECT time FROM players WHERE name = ?", (player_name,))
                saved_best = c.fetchone()[0]

                if not saved_best:
                    saved_best = 0

                if current_best is not None:
                    if current_best < saved_best and current_best > 0:
                        # Get old rank
                        c.execute("SELECT name, time FROM players")
                        rows = c.fetchall()
                        player_dict = {row[0]: row[1] for row in rows}
                        sorted_dict = sorted(player_dict.items(), key=lambda item: item[1])
                        old_rank = sorted_dict.index((player_name, saved_best)) + 1

                        # Update the record
                        c.execute('''UPDATE players SET time=? WHERE name= ?''', (current_best, player_name))
                        conn.commit()

                        # Get new rank
                        c.execute("SELECT name, time FROM players")
                        rows = c.fetchall()
                        player_dict = {row[0]: row[1] for row in rows}
                        sorted_dict = sorted(player_dict.items(), key=lambda item: item[1])
                        new_rank = sorted_dict.index((player_name, current_best)) + 1

                        channel_id = 1170705275406266379  # Replace with your channel ID
                        channel = bot.get_channel(channel_id)
                        if channel is not None:
                            member = guild.get_member(int(discord_id))  # Convert discord_id to integer
                            if member:
                                if old_rank == new_rank:
                                    await channel.send(
                                        f'{member.mention} achieved a new personal best of {current_best} seconds in long! '
                                        f'\n`#{new_rank}`')
                                else:
                                    await channel.send(
                                        f'{member.mention} achieved a new personal best of {current_best} seconds in long ! '
                                        f'\n`#{old_rank} → #{new_rank}`')
                            else:
                                print(f'Failed to get member with ID {discord_id}')
            else:
                print(f'Failed to get stats for {player_name} from {url}. Response code: {response.status_code}')
        except Exception as e:
            print(f'An error occurred while checking {player_name} for a new personal best:')
            traceback.print_exc()








#OTHER COMMANDS




















@bot.command()
async def hello(ctx):
    await ctx.send('Hello {0.author}!'.format(ctx))


@bot.command()
@commands.has_role("dev")
async def addplayer(ctx, name: str, discord_mention: discord.Member):
    # Check if the player already exists in the database
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE name = ?", (name,))
    existing_player = c.fetchone()


    if existing_player:
        await ctx.send(f'Player {name} is already in the list.')
        return

    # Use discord_mention.id to get the Discord ID
    discord_id = str(discord_mention.id)

    url = f'https://api.mojang.com/users/profiles/minecraft/{name}'
    response = requests.get(url)

    if response.status_code == 200:
        uuid = response.json().get('id')
        if uuid:
            player_name = requests.get(f'https://sessionserver.mojang.com/session/minecraft/profile/{uuid}').json().get(
                'name')
            if player_name.lower() == name.lower():
                mode = 'normal'  # Replace with the specific mode you want to check
                url = f'https://mcplayhd.net/api/v1/fastbuilder/{mode}/stats/{player_name}'
                headers = {
                    'Authorization': f'Bearer {token}'
                }
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    current_best = response.json().get('data', {}).get('stats', {}).get('timeBest', 0)
                    current_best = current_best / 1000
                    current_best_short = response.json().get('data', {}).get('stats', {}).get('timeBest')
                    current_best_short = current_best_short / 1000
                    c.execute("INSERT INTO players (name, time, time_short, discord_id) VALUES (?, ?, ?, ?)",
                              (name, current_best, current_best_short, discord_id))

                    conn.commit()
                    if current_best and current_best_short> 0:
                        await ctx.send(f'Player {name} added to the list, with the current best time of: {current_best} seconds!')
                    else:
                        await ctx.send(f'Player {name} added to the list, without any personal best yet!')
            else:
                await ctx.send(
                    'The provided Minecraft username does not match with the username registered in the database.')
        else:
            await ctx.send('Failed to retrieve UUID for the provided Minecraft username.')
    else:
        await ctx.send('The provided Minecraft username does not exist.')

@bot.command()
@commands.has_role("dev")
async def delplayer(ctx, name: str):
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE name = ?", (name,))
    existing_player = c.fetchone()

    if not existing_player:
        await ctx.send(f'Player {name} does not exist in the list.')
        return

    c.execute("DELETE FROM players WHERE name = ?", (name,))
    conn.commit()

    await ctx.send(f'Player {name} has been successfully deleted from the list.')



@bot.command(name="lb", aliases=["leaderboard"])
async def leaderboard(ctx, page: int = 1):
    c = conn.cursor()
    c.execute("SELECT * FROM players")
    rows = c.fetchall()

    players_per_page = 10

    if rows:
        player_dict = {name: record for record, name in (row[1:] for row in rows)}
        sorted_dict = sorted(player_dict.items(), key=lambda item: item[1])

        start_idx = (page - 1) * players_per_page
        end_idx = page * players_per_page
        current_players = sorted_dict[start_idx:end_idx]

        embed = discord.Embed(title=f"Player List (Page {page})", color=discord.Color.dark_red())

        for idx, (name, time) in enumerate(current_players, start=start_idx + 1):
            # Include the rank before the usernames
            embed.add_field(name=f"Rank #{idx}", value=f"**{name}**: **{time}**", inline=False)

        if end_idx < len(sorted_dict):
            embed.set_footer(text=f"React with ➡️ to go to the next page")

        message = await ctx.author.send(embed=embed)
        if end_idx < len(sorted_dict):
            await message.add_reaction("➡️")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "➡️"

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
            await message.delete()
            await leaderboard(ctx, page + 1)
        except TimeoutError:
            pass
    else:
        await ctx.author.send("There are no players in the list.")



async def get_player_rank(name):
    c = conn.cursor()
    c.execute("SELECT * FROM players")
    rows = c.fetchall()
    if rows:
        player_dict = {name: record for record, name in (row[1:] for row in rows)}
        sorted_dict = sorted(player_dict.items(), key=lambda item: item[1])
        for rank, (player, time) in enumerate(sorted_dict, start=1):
            if player.lower() == name.lower():
                return rank, time
    return None, None


@bot.command()
async def rank(ctx, name: str):
    rank, time = await get_player_rank(name)
    if rank:
        await ctx.send(f'{name} is ranked **`#{rank}`** with a time of **`{time}`** seconds.')
    else:
        await ctx.send(f'{name} does not exist in the list.')
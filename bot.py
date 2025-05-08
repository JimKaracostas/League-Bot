from dotenv import load_dotenv
import sqlite3
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional
import os
import random

load_dotenv()
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput
import json

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("ANNOUNCEMENT_CHANNEL_ID"))
RESULTS_CHANNEL_ID = int(os.getenv("RESULTS_CHANNEL_ID"))
ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID"))
REPORT_SCORES_CHANNEL_ID = int(os.getenv("REPORT_SCORES_CHANNEL_ID"))


# Data storage
class LeagueData:

    def __init__(self):
        self.conn = sqlite3.connect('league_data.db')
        self.cursor = self.conn.cursor()
        self.teams = {}  # Initialize teams dictionary
        self.player_stats = {}  # Initialize player_stats dictionary
        self.team_captains = {}  # Initialize team_captains dictionary
        self.player_teams = {}  # Initialize player_teams dictionary
        self.create_tables()

    def create_tables(self):
        # Drop existing tables
        self.cursor.execute("DROP TABLE IF EXISTS match_results")
        self.cursor.execute("DROP TABLE IF EXISTS scheduled_matches")
        self.cursor.execute("DROP TABLE IF EXISTS player_teams")
        self.cursor.execute("DROP TABLE IF EXISTS team_captains")
        self.cursor.execute("DROP TABLE IF EXISTS player_stats")
        self.cursor.execute("DROP TABLE IF EXISTS teams")
        self.cursor.execute("DROP TABLE IF EXISTS standings")

        # Create tables
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            team_name TEXT PRIMARY KEY,
            captain_id INTEGER,
            players TEXT,
            division TEXT
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS champions_league_teams (
            team_name TEXT PRIMARY KEY,
            captain_id INTEGER,
            players TEXT,
            division TEXT
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_stats (
            player_id INTEGER PRIMARY KEY,
            goals INTEGER,
            assists INTEGER,
            saves INTEGER
            champions_league_goals INTEGER DEFAULT 0,
            champions_league_assists INTEGER DEFAULT 0,
            champions_league_saves INTEGER DEFAULT 0
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_captains (
            captain_id INTEGER PRIMARY KEY,
            team_name TEXT
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_teams (
            player_id INTEGER PRIMARY KEY,
            team_name TEXT
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_matches (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team1_name TEXT,
            team2_name TEXT,
            scheduled_time TEXT,
            status TEXT,
            FOREIGN KEY (team1_name) REFERENCES teams(team_name),
            FOREIGN KEY (team2_name) REFERENCES teams(team_name)
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS match_results (
            match_id INTEGER PRIMARY KEY,
            team1_score INTEGER,
            team2_score INTEGER,
            team1_goals TEXT,
            team2_goals TEXT,
            team1_saves INTEGER,
            team2_saves INTEGER,
            FOREIGN KEY (match_id) REFERENCES scheduled_matches(match_id)
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS champions_league_match_results (
            match_id INTEGER PRIMARY KEY,
            team1_score INTEGER,
            team2_score INTEGER,
            team1_goals TEXT,
            team2_goals TEXT,
            team1_saves INTEGER,
            team2_saves INTEGER,
            FOREIGN KEY (match_id) REFERENCES scheduled_matches(match_id)
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS standings (
            team_name TEXT PRIMARY KEY,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            FOREIGN KEY (team_name) REFERENCES teams(team_name)
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS champions_league_standings (
            team_name TEXT PRIMARY KEY,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            FOREIGN KEY (team_name) REFERENCES champions_league_teams(team_name)
        )
        ''')
        self.conn.commit()

    def save_data(self):
        # Clear existing data
        self.cursor.execute("DELETE FROM teams")
        self.cursor.execute("DELETE FROM player_stats")
        self.cursor.execute("DELETE FROM team_captains")
        self.cursor.execute("DELETE FROM player_teams")

        # Insert teams
        for team_name, team_data in self.teams.items():
            self.cursor.execute("INSERT INTO teams VALUES (?, ?, ?, ?)",
                                (team_name, team_data['captain_id'], ','.join(
                                    map(str, team_data['players'])),
                                 team_data.get('division', '')))

        # Insert player stats
        for player_id, stats in self.player_stats.items():
            self.cursor.execute(
                "INSERT INTO player_stats (player_id, goals, assists, saves) VALUES (?, ?, ?, ?)",
                (player_id, stats['goals'], stats['assists'], stats['saves']))

        # Insert team captains
        for captain_id, team_name in self.team_captains.items():
            self.cursor.execute("INSERT INTO team_captains VALUES (?, ?)",
                                (captain_id, team_name))

        # Insert player teams
        for player_id, team_name in self.player_teams.items():
            self.cursor.execute("INSERT INTO player_teams VALUES (?, ?)",
                                (player_id, team_name))

        self.conn.commit()

    def load_data(self):
        # Load teams
        self.cursor.execute("SELECT * FROM teams")
        for row in self.cursor.fetchall():
            team_name, captain_id, players_str, division = row
            self.teams[team_name] = {
                'captain_id': captain_id,
                'players': list(map(int, players_str.split(','))),
                'division': division
            }

        # Load champions league teams
        self.cursor.execute("SELECT * FROM champions_league_teams")
        for row in self.cursor.fetchall():
            team_name, captain_id, players_str, division = row
            self.teams[team_name] = {
                'captain_id': captain_id,
                'players': list(map(int, players_str.split(','))),
                'division': division
            }

        # Load player stats
        self.cursor.execute("SELECT * FROM player_stats")
        for row in self.cursor.fetchall():
            player_id, goals, assists, saves = row
            self.player_stats[player_id] = {
                'goals': goals,
                'assists': assists,
                'saves': saves
            }
            # different stats for champions league
            self.player_stats[player_id]['champions_league_goals'] = 0
            self.player_stats[player_id]['champions_league_assists'] = 0
            self.player_stats[player_id]['champions_league_saves'] = 0

        # Load team captains
        self.cursor.execute("SELECT * FROM team_captains")
        for row in self.cursor.fetchall():
            captain_id, team_name = row
            self.team_captains[captain_id] = team_name

        # Load player teams
        self.cursor.execute("SELECT * FROM player_teams")
        for row in self.cursor.fetchall():
            player_id, team_name = row
            self.player_teams[player_id] = team_name

    def __del__(self):
        self.conn.close()


# Score submission modal, with a league selector
class LeagueSelector(discord.ui.Select):

    def __init__(self, leagues: List[str]):
        options = [
            discord.SelectOption(label=league, value=league)
            for league in leagues
        ]
        super().__init__(placeholder='Select a league', options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_league = self.values[0]
        await interaction.response.send_message(
            f"You selected the {selected_league} league.", ephemeral=True)


class ScoreSubmissionModal(Modal, title='Submit Match Score'):

    def __init__(self, league_data: LeagueData, match_id: int,
                 interaction: discord.Interaction):
        super().__init__()
        self.league_data = league_data
        self.match_id = match_id
        self.interaction = interaction
        self.selected_league = "League"  # Default to regular league

        # Add league selector
        leagues = ["League", "Champions League"]
        self.league_selector = LeagueSelector(leagues)
        self.league_selector.callback = self.on_league_select
        self.add_item(self.league_selector)

        self.score1 = TextInput(label='Team 1 Score',
                                placeholder='Enter Team 1 score...',
                                required=True)
        self.score2 = TextInput(label='Team 2 Score',
                                placeholder='Enter Team 2 score...',
                                required=True)

        # Get match details
        self.league_data.cursor.execute(
            "SELECT team1_name, team2_name FROM scheduled_matches WHERE match_id = ?",
            (match_id, ))
        match = self.league_data.cursor.fetchone()
        if not match:
            return

        team1_name, team2_name = match

        # Get team 1 players
        team1_players = self.league_data.teams[team1_name]['players']
        team1_player_names = []
        for player_id in team1_players:
            member = interaction.guild.get_member(player_id)
            if member:
                team1_player_names.append(member.name)

        # Get team 2 players
        team2_players = self.league_data.teams[team2_name]['players']
        team2_player_names = []
        for player_id in team2_players:
            member = interaction.guild.get_member(player_id)
            if member:
                team2_player_names.append(member.name)

        # Create combined fields for team 1 stats
        self.team1_stats = TextInput(
            label=f'{team1_name} Stats',
            placeholder=
            f'Format: goals/assists/saves\nOne per line for:\n{", ".join(team1_player_names)}',
            style=discord.TextStyle.paragraph,
            required=True)

        # Create combined fields for team 2 stats
        self.team2_stats = TextInput(
            label=f'{team2_name} Stats',
            placeholder=
            f'Format: goals/assists/saves\nOne per line for:\n{", ".join(team2_player_names)}',
            style=discord.TextStyle.paragraph,
            required=True)

        self.add_item(self.score1)
        self.add_item(self.score2)
        self.add_item(self.team1_stats)
        self.add_item(self.team2_stats)

    async def on_league_select(self, interaction: discord.Interaction):
        # Update selected league when selector changes
        self.selected_league = self.league_selector.values[0]
        await interaction.response.defer()

    async def on_submit(self, interaction: discord.Interaction):
        try:
            score1 = int(self.score1.value)
            score2 = int(self.score2.value)

            # Get match details
            self.league_data.cursor.execute(
                "SELECT team1_name, team2_name FROM scheduled_matches WHERE match_id = ?",
                (self.match_id, ))
            match = self.league_data.cursor.fetchone()
            if not match:
                await interaction.response.send_message("Match not found!",
                                                        ephemeral=True)
                return

            team1_name, team2_name = match

            # Get team players
            team1_players = self.league_data.teams[team1_name]['players']
            team2_players = self.league_data.teams[team2_name]['players']

            # Process team 1 stats
            team1_stats_lines = self.team1_stats.value.strip().split('\n')
            team1_stats = []
            for line in team1_stats_lines:
                if line.strip():
                    try:
                        goals, assists, saves = map(int,
                                                    line.strip().split('/'))
                        team1_stats.append((goals, assists, saves))
                    except ValueError:
                        await interaction.response.send_message(
                            f"Invalid stats format for Team 1. Please use format: goals/assists/saves (e.g. 2/1/0)",
                            ephemeral=True)
                        return

            # Process team 2 stats
            team2_stats_lines = self.team2_stats.value.strip().split('\n')
            team2_stats = []
            for line in team2_stats_lines:
                if line.strip():
                    try:
                        goals, assists, saves = map(int,
                                                    line.strip().split('/'))
                        team2_stats.append((goals, assists, saves))
                    except ValueError:
                        await interaction.response.send_message(
                            f"Invalid stats format for Team 2. Please use format: goals/assists/saves (e.g. 2/1/0)",
                            ephemeral=True)
                        return

            # Validate scores match the number of goals
            total_team1_goals = sum(stats[0] for stats in team1_stats)
            total_team2_goals = sum(stats[0] for stats in team2_stats)

            if total_team1_goals != score1:
                await interaction.response.send_message(
                    f"Total goals ({total_team1_goals}) doesn't match Team 1's score ({score1})!",
                    ephemeral=True)
                return
            if total_team2_goals != score2:
                await interaction.response.send_message(
                    f"Total goals ({total_team2_goals}) doesn't match Team 2's score ({score2})!",
                    ephemeral=True)
                return

            # Check if we're handling a Champions League match
            is_champions_league = self.selected_league == "Champions League"

            # Update player stats
            self.update_player_stats(team1_players, team1_stats, team2_players,
                                     team2_stats, is_champions_league)

            # Save match result to appropriate table
            if is_champions_league:
                self.league_data.cursor.execute(
                    """INSERT INTO champions_league_match_results (match_id, team1_score, team2_score, team1_goals, team2_goals, team1_saves, team2_saves)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (self.match_id, score1, score2, self.team1_stats.value,
                     self.team2_stats.value,
                     sum(stats[2] for stats in team1_stats),
                     sum(stats[2] for stats in team2_stats)))
            else:
                self.league_data.cursor.execute(
                    """INSERT INTO match_results (match_id, team1_score, team2_score, team1_goals, team2_goals, team1_saves, team2_saves)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (self.match_id, score1, score2, self.team1_stats.value,
                     self.team2_stats.value,
                     sum(stats[2] for stats in team1_stats),
                     sum(stats[2] for stats in team2_stats)))

            # Update match status
            self.league_data.cursor.execute(
                "UPDATE scheduled_matches SET status = 'completed' WHERE match_id = ?",
                (self.match_id, ))

            # Update standings for regular league only
            if not is_champions_league:
                self.update_regular_league_standings(team1_name, team2_name,
                                                     score1, score2)
            else:
                self.update_champions_league_standings(team1_name, team2_name,
                                                       score1, score2)

            self.league_data.save_data()

            # Create detailed match result embed
            embed = self.create_match_result_embed(interaction, team1_name,
                                                   team2_name, score1, score2,
                                                   team1_players, team1_stats,
                                                   team2_players, team2_stats,
                                                   is_champions_league)

            # Send to interaction
            await interaction.response.send_message(embed=embed)

            # Send to announcement channel
            await self.send_announcement(interaction, team1_name, team2_name,
                                         score1, score2, team1_players,
                                         team1_stats, team2_players,
                                         team2_stats, is_champions_league)

        except Exception as e:
            await interaction.response.send_message(
                f"Error processing score: {str(e)}", ephemeral=True)

    def update_player_stats(self, team1_players, team1_stats, team2_players,
                            team2_stats, is_champions_league):
        # Update player stats for team 1
        for i, player_id in enumerate(team1_players):
            if i < len(team1_stats):
                goals, assists, saves = team1_stats[i]

                # First make sure player exists in the database
                self.league_data.cursor.execute(
                    "INSERT OR IGNORE INTO player_stats (player_id, goals, assists, saves, champions_league_goals, champions_league_assists, champions_league_saves) VALUES (?, 0, 0, 0, 0, 0, 0)",
                    (player_id, ))

                # Update the appropriate stats
                if is_champions_league:
                    self.league_data.cursor.execute(
                        "UPDATE player_stats SET champions_league_goals = champions_league_goals + ?, champions_league_assists = champions_league_assists + ?, champions_league_saves = champions_league_saves + ? WHERE player_id = ?",
                        (goals, assists, saves, player_id))
                else:
                    self.league_data.cursor.execute(
                        "UPDATE player_stats SET goals = goals + ?, assists = assists + ?, saves = saves + ? WHERE player_id = ?",
                        (goals, assists, saves, player_id))

        # Update player stats for team 2
        for i, player_id in enumerate(team2_players):
            if i < len(team2_stats):
                goals, assists, saves = team2_stats[i]

                # First make sure player exists in the database
                self.league_data.cursor.execute(
                    "INSERT OR IGNORE INTO player_stats (player_id, goals, assists, saves, champions_league_goals, champions_league_assists, champions_league_saves) VALUES (?, 0, 0, 0, 0, 0, 0)",
                    (player_id, ))

                # Update the appropriate stats
                if is_champions_league:
                    self.league_data.cursor.execute(
                        "UPDATE player_stats SET champions_league_goals = champions_league_goals + ?, champions_league_assists = champions_league_assists + ?, champions_league_saves = champions_league_saves + ? WHERE player_id = ?",
                        (goals, assists, saves, player_id))
                else:
                    self.league_data.cursor.execute(
                        "UPDATE player_stats SET goals = goals + ?, assists = assists + ?, saves = saves + ? WHERE player_id = ?",
                        (goals, assists, saves, player_id))

    def update_regular_league_standings(self, team1_name, team2_name, score1,
                                        score2):
        if score1 > score2:
            # Team 1 wins
            self.league_data.cursor.execute(
                "UPDATE standings SET wins = wins + 1 WHERE team_name = ?",
                (team1_name, ))
            self.league_data.cursor.execute(
                "UPDATE standings SET losses = losses + 1 WHERE team_name = ?",
                (team2_name, ))
        elif score1 < score2:
            # Team 2 wins
            self.league_data.cursor.execute(
                "UPDATE standings SET wins = wins + 1 WHERE team_name = ?",
                (team2_name, ))
            self.league_data.cursor.execute(
                "UPDATE standings SET losses = losses + 1 WHERE team_name = ?",
                (team1_name, ))
        else:
            # Draw
            self.league_data.cursor.execute(
                "UPDATE standings SET draws = draws + 1 WHERE team_name = ?",
                (team1_name, ))
            self.league_data.cursor.execute(
                "UPDATE standings SET draws = draws + 1 WHERE team_name = ?",
                (team2_name, ))

    def update_champions_league_standings(self, team1_name, team2_name, score1,
                                          score2):
        # Make sure teams exist in champions_league_standings
        self.league_data.cursor.execute(
            "INSERT OR IGNORE INTO champions_league_standings (team_name, wins, losses, draws) VALUES (?, 0, 0, 0)",
            (team1_name, ))
        self.league_data.cursor.execute(
            "INSERT OR IGNORE INTO champions_league_standings (team_name, wins, losses, draws) VALUES (?, 0, 0, 0)",
            (team2_name, ))

        if score1 > score2:
            # Team 1 wins
            self.league_data.cursor.execute(
                "UPDATE champions_league_standings SET wins = wins + 1 WHERE team_name = ?",
                (team1_name, ))
            self.league_data.cursor.execute(
                "UPDATE champions_league_standings SET losses = losses + 1 WHERE team_name = ?",
                (team2_name, ))
        elif score1 < score2:
            # Team 2 wins
            self.league_data.cursor.execute(
                "UPDATE champions_league_standings SET wins = wins + 1 WHERE team_name = ?",
                (team2_name, ))
            self.league_data.cursor.execute(
                "UPDATE champions_league_standings SET losses = losses + 1 WHERE team_name = ?",
                (team1_name, ))
        else:
            # Draw
            self.league_data.cursor.execute(
                "UPDATE champions_league_standings SET draws = draws + 1 WHERE team_name = ?",
                (team1_name, ))
            self.league_data.cursor.execute(
                "UPDATE champions_league_standings SET draws = draws + 1 WHERE team_name = ?",
                (team2_name, ))

    def create_match_result_embed(self, interaction, team1_name, team2_name,
                                  score1, score2, team1_players, team1_stats,
                                  team2_players, team2_stats,
                                  is_champions_league):
        league_name = "Champions League" if is_champions_league else "League"

        embed = discord.Embed(
            title=f"{league_name} Match Result - {team1_name} vs {team2_name}",
            color=discord.Color.blue())

        # Team 1 stats
        team1_stats_text = f"Score: {score1}\n\n"

        # Goals
        team1_stats_text += "**Goals:**\n"
        for i, player_id in enumerate(team1_players):
            if i < len(team1_stats) and team1_stats[i][0] > 0:
                member = interaction.guild.get_member(player_id)
                if member:
                    team1_stats_text += f"⚽ {member.name}: {team1_stats[i][0]}\n"

        # Assists
        team1_stats_text += "\n**Assists:**\n"
        for i, player_id in enumerate(team1_players):
            if i < len(team1_stats) and team1_stats[i][1] > 0:
                member = interaction.guild.get_member(player_id)
                if member:
                    team1_stats_text += f"🎯 {member.name}: {team1_stats[i][1]}\n"

        # Saves
        team1_stats_text += "\n**Saves:**\n"
        for i, player_id in enumerate(team1_players):
            if i < len(team1_stats) and team1_stats[i][2] > 0:
                member = interaction.guild.get_member(player_id)
                if member:
                    team1_stats_text += f"🧤 {member.name}: {team1_stats[i][2]}\n"

        embed.add_field(name=f"{team1_name}",
                        value=team1_stats_text,
                        inline=True)

        # VS
        embed.add_field(name="vs", value="", inline=True)

        # Team 2 stats
        team2_stats_text = f"Score: {score2}\n\n"

        # Goals
        team2_stats_text += "**Goals:**\n"
        for i, player_id in enumerate(team2_players):
            if i < len(team2_stats) and team2_stats[i][0] > 0:
                member = interaction.guild.get_member(player_id)
                if member:
                    team2_stats_text += f"⚽ {member.name}: {team2_stats[i][0]}\n"

        # Assists
        team2_stats_text += "\n**Assists:**\n"
        for i, player_id in enumerate(team2_players):
            if i < len(team2_stats) and team2_stats[i][1] > 0:
                member = interaction.guild.get_member(player_id)
                if member:
                    team2_stats_text += f"🎯 {member.name}: {team2_stats[i][1]}\n"

        # Saves
        team2_stats_text += "\n**Saves:**\n"
        for i, player_id in enumerate(team2_players):
            if i < len(team2_stats) and team2_stats[i][2] > 0:
                member = interaction.guild.get_member(player_id)
                if member:
                    team2_stats_text += f"🧤 {member.name}: {team2_stats[i][2]}\n"

        embed.add_field(name=f"{team2_name}",
                        value=team2_stats_text,
                        inline=True)

        return embed

    async def send_announcement(self, interaction, team1_name, team2_name,
                                score1, score2, team1_players, team1_stats,
                                team2_players, team2_stats,
                                is_champions_league):
        try:
            announcement_channel = interaction.guild.get_channel(
                int(os.getenv("ANNOUNCEMENT_CHANNEL_ID")))
            if announcement_channel:
                league_name = "Champions League" if is_champions_league else "League"

                announcement_embed = discord.Embed(
                    title=f"{league_name} Match Result Announced!",
                    description=
                    f"A match between {team1_name} and {team2_name} has been completed!",
                    color=discord.Color.green())
                announcement_embed.add_field(
                    name="Result",
                    value=f"{team1_name} {score1} - {score2} {team2_name}")

                # Add goal scorers
                goal_scorers = "**Goal Scorers:**\n"
                for i, player_id in enumerate(team1_players):
                    if i < len(team1_stats) and team1_stats[i][0] > 0:
                        member = interaction.guild.get_member(player_id)
                        if member:
                            goal_scorers += f"⚽ {member.name} ({team1_name}): {team1_stats[i][0]}\n"
                for i, player_id in enumerate(team2_players):
                    if i < len(team2_stats) and team2_stats[i][0] > 0:
                        member = interaction.guild.get_member(player_id)
                        if member:
                            goal_scorers += f"⚽ {member.name} ({team2_name}): {team2_stats[i][0]}\n"
                announcement_embed.add_field(name="Goal Scorers",
                                             value=goal_scorers,
                                             inline=False)

                await announcement_channel.send(embed=announcement_embed)
        except Exception as e:
            print(f"Error sending to announcement channel: {e}")


class ScheduleMatchModal(Modal, title='Schedule Match'):

    def __init__(self, league_data: LeagueData, team1: str, team2: str):
        super().__init__()
        self.league_data = league_data
        self.team1 = team1
        self.team2 = team2

        self.date = TextInput(label='Match Date',
                              placeholder='YYYY-MM-DD',
                              required=True)
        self.time = TextInput(label='Match Time',
                              placeholder='HH:MM (24-hour format)',
                              required=True)

        self.add_item(self.date)
        self.add_item(self.time)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse date
            try:
                match_date = datetime.strptime(self.date.value, "%Y-%m-%d")
            except ValueError:
                await interaction.response.send_message(
                    "Invalid date format! Please use YYYY-MM-DD",
                    ephemeral=True)
                return

            # Parse time
            try:
                match_time = datetime.strptime(self.time.value, "%H:%M").time()
            except ValueError:
                await interaction.response.send_message(
                    "Invalid time format! Please use HH:MM (24-hour format)",
                    ephemeral=True)
                return

            # Combine date and time
            scheduled_datetime = datetime.combine(match_date.date(),
                                                  match_time)
            scheduled_time = scheduled_datetime.strftime("%Y-%m-%d %H:%M:%S")

            # Schedule the match
            self.league_data.cursor.execute(
                """
                INSERT INTO scheduled_matches (team1_name, team2_name, scheduled_time, status)
                VALUES (?, ?, ?, ?)
            """, (self.team1, self.team2, scheduled_time, 'scheduled'))
            self.league_data.conn.commit()

            # Create embed
            embed = discord.Embed(
                title="Match Scheduled",
                description=
                f"A match has been scheduled between {self.team1} and {self.team2}!",
                color=discord.Color.green())
            embed.add_field(name="Date",
                            value=scheduled_datetime.strftime("%Y-%m-%d"))
            embed.add_field(name="Time",
                            value=scheduled_datetime.strftime("%H:%M"))
            embed.add_field(name="Status", value="Scheduled")

            # Send to announcement channel
            try:
                announcement_channel = interaction.guild.get_channel(
                    int(os.getenv("ANNOUNCEMENT_CHANNEL_ID")))
                if announcement_channel:
                    announcement_embed = discord.Embed(
                        title="New Match Scheduled!",
                        description=f"A new match has been scheduled!",
                        color=discord.Color.blue())
                    announcement_embed.add_field(
                        name="Teams", value=f"{self.team1} vs {self.team2}")
                    announcement_embed.add_field(
                        name="Date",
                        value=scheduled_datetime.strftime("%Y-%m-%d"))
                    announcement_embed.add_field(
                        name="Time",
                        value=scheduled_datetime.strftime("%H:%M"))
                    await announcement_channel.send(embed=announcement_embed)
            except Exception as e:
                print(f"Error sending to announcement channel: {e}")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                f"Error scheduling match: {str(e)}", ephemeral=True)


# Bot setup
class RematchBot(commands.Bot):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix='!', intents=intents)
        self.league_data = LeagueData()
        self.league_data.load_data()

    async def setup_hook(self):
        # Force sync commands globally and for all guilds
        await self.tree.sync()
        for guild in self.guilds:
            await self.tree.sync(guild=guild)


bot = RematchBot()


# Helper function: is user a captain of a team?
def is_team_captain(user, guild, team_name):
    captain_role = discord.utils.get(guild.roles, name=f"{team_name} Captain")
    return captain_role and captain_role in user.roles


# Helper function: is user a league admin?
def is_league_admin(user, guild):
    admin_roles = [
        discord.utils.get(guild.roles, name="League Admin"),
        discord.utils.get(guild.roles, name="Admin")
    ]
    return any(
        role for role in admin_roles
        if role and role in user.roles) or user.guild_permissions.administrator


# Team Management Commands
@bot.tree.command(name="create_team",
                  description="Create a new team and become its captain")
async def create_team(interaction: discord.Interaction, team_name: str):
    user_id = interaction.user.id

    # Check if user is already a captain
    if user_id in bot.league_data.team_captains:
        await interaction.response.send_message(
            "You are already a team captain!", ephemeral=True)
        return

    # Check if user is already in a team
    if user_id in bot.league_data.player_teams:
        await interaction.response.send_message("You are already in a team!",
                                                ephemeral=True)
        return

    # Check if team name exists
    if team_name in bot.league_data.teams:
        await interaction.response.send_message(
            "A team with this name already exists!", ephemeral=True)
        return

    # Create team
    bot.league_data.teams[team_name] = {
        'captain_id': user_id,
        'players': [user_id]
    }
    bot.league_data.team_captains[user_id] = team_name
    bot.league_data.player_teams[user_id] = team_name
    bot.league_data.save_data()

    # Create a role for the team
    team_role = await interaction.guild.create_role(name=team_name)
    await interaction.user.add_roles(team_role)

    # Create a role for the captain
    captain_role = await interaction.guild.create_role(
        name=f"{team_name} Captain")
    await interaction.user.add_roles(captain_role)

    # Ensure the @Captain role exists and assign it
    captain_global_role = discord.utils.get(interaction.guild.roles,
                                            name="Captain")
    if not captain_global_role:
        captain_global_role = await interaction.guild.create_role(
            name="Captain")
    await interaction.user.add_roles(captain_global_role)

    embed = discord.Embed(title="Team Created",
                          description=f"Team '{team_name}' has been created!",
                          color=discord.Color.green())
    embed.add_field(name="Captain", value=f"<@{user_id}>")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="add_player", description="Add a player to your team")
async def add_player(interaction: discord.Interaction, user: discord.Member,
                     team_name: str):
    guild = interaction.guild
    if not (is_team_captain(interaction.user, guild, team_name)
            or is_league_admin(interaction.user, guild)):
        embed = discord.Embed(
            title="Permission Denied",
            description=
            "Only the team captain or a League Admin/Admin can add players to a team.",
            color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    target_id = user.id

    # Check if target is already in a team
    if target_id in bot.league_data.player_teams:
        await interaction.response.send_message(
            "This player is already in a team!", ephemeral=True)
        return

    # Check if the team exists
    if team_name not in bot.league_data.teams:
        await interaction.response.send_message("This team does not exist!",
                                                ephemeral=True)
        return

    # Add player to the team
    bot.league_data.teams[team_name]['players'].append(target_id)
    bot.league_data.player_teams[target_id] = team_name
    bot.league_data.save_data()

    # Assign the team role to the player
    role = discord.utils.get(interaction.guild.roles, name=team_name)
    if role:
        await user.add_roles(role)

    embed = discord.Embed(
        title="Player Added",
        description=f"<@{target_id}> has been added to {team_name}!",
        color=discord.Color.green())
    embed.add_field(name="Team", value=team_name)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="remove_player",
                  description="Remove a player from your team")
async def remove_player(interaction: discord.Interaction, user: discord.Member,
                        team_name: str):
    guild = interaction.guild
    if not (is_team_captain(interaction.user, guild, team_name)
            or is_league_admin(interaction.user, guild)):
        embed = discord.Embed(
            title="Permission Denied",
            description=
            "Only the team captain or a League Admin/Admin can remove players from a team.",
            color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    target_id = user.id

    # Check if the team exists
    if team_name not in bot.league_data.teams:
        await interaction.response.send_message("This team does not exist!",
                                                ephemeral=True)
        return

    # Check if target is in the team
    if target_id not in bot.league_data.teams[team_name]['players']:
        await interaction.response.send_message(
            "This player is not in your team!", ephemeral=True)
        return

    # Check if the player is the captain
    is_captain = target_id == bot.league_data.teams[team_name]['captain_id']

    # Remove player
    bot.league_data.teams[team_name]['players'].remove(target_id)
    del bot.league_data.player_teams[target_id]

    # If the player was a captain, remove captain status
    if is_captain:
        del bot.league_data.team_captains[target_id]
        # Remove captain role
        captain_role = discord.utils.get(guild.roles,
                                         name=f"{team_name} Captain")
        if captain_role and captain_role in user.roles:
            await user.remove_roles(captain_role)

    # Remove the team role from the player
    role = discord.utils.get(interaction.guild.roles, name=team_name)
    if role and role in user.roles:
        await user.remove_roles(role)

    bot.league_data.save_data()

    embed = discord.Embed(
        title="Player Removed",
        description=f"<@{target_id}> has been removed from {team_name}!",
        color=discord.Color.red())
    embed.add_field(name="Team", value=team_name)
    if is_captain:
        embed.add_field(name="Note",
                        value="Player was also removed as team captain.",
                        inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(
    name="schedule_match",
    description="Schedule a match between two teams (Admin only)")
async def schedule_match(interaction: discord.Interaction, team1: str,
                         team2: str):
    guild = interaction.guild
    if not is_league_admin(interaction.user, guild):
        embed = discord.Embed(
            title="Permission Denied",
            description="Only a League Admin/Admin can schedule matches.",
            color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Check if teams exist
    if team1 not in bot.league_data.teams or team2 not in bot.league_data.teams:
        await interaction.response.send_message(
            "One or both teams don't exist!", ephemeral=True)
        return

    # Create and show the modal
    modal = ScheduleMatchModal(bot.league_data, team1, team2)
    await interaction.response.send_modal(modal)


@bot.tree.command(name="list_matches",
                  description="List all scheduled matches")
async def list_matches(interaction: discord.Interaction):
    bot.league_data.cursor.execute("""
        SELECT match_id, team1_name, team2_name, scheduled_time, status 
        FROM scheduled_matches 
        WHERE status = 'scheduled'
    """)
    matches = bot.league_data.cursor.fetchall()

    if not matches:
        await interaction.response.send_message(
            "No matches are currently scheduled!", ephemeral=True)
        return

    embed = discord.Embed(title="Scheduled Matches",
                          color=discord.Color.blue())

    for match in matches:
        match_id, team1, team2, scheduled_time, status = match
        embed.add_field(
            name=f"Match #{match_id}",
            value=
            f"{team1} vs {team2}\nTime: {scheduled_time}\nStatus: {status}",
            inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="set_score",
                  description="Submit match score (Admin only)")
async def set_score(interaction: discord.Interaction, match_id: int):
    guild = interaction.guild
    if not is_league_admin(interaction.user, guild):
        embed = discord.Embed(
            title="Permission Denied",
            description="Only a League Admin/Admin can submit match scores.",
            color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Fetch match info
    bot.league_data.cursor.execute(
        "SELECT team1_name, team2_name FROM scheduled_matches WHERE match_id = ?",
        (match_id, ))
    match = bot.league_data.cursor.fetchone()
    if not match:
        await interaction.response.send_message(
            "Match not found! Please use /list_matches to see valid match IDs.",
            ephemeral=True)
        return

    # Create and show the modal
    modal = ScoreSubmissionModal(bot.league_data, match_id, interaction)
    await interaction.response.send_modal(modal)


@bot.command(name="stats")
async def stats(ctx, user: discord.Member):
    user_id = user.id

    # Query the database directly for player stats
    bot.league_data.cursor.execute(
        "SELECT goals, assists, saves, champions_league_goals, champions_league_assists, champions_league_saves FROM player_stats WHERE player_id = ?",
        (user_id, ))
    stats_row = bot.league_data.cursor.fetchone()

    if not stats_row:
        await ctx.send(f"{user.mention} has no stats yet!")
        return

    # Extract stats from database row
    goals, assists, saves, cl_goals, cl_assists, cl_saves = stats_row

    # Get player's team
    team_name = bot.league_data.player_teams.get(user_id, "No team")

    embed = discord.Embed(title=f"Player Stats - {user.name}",
                          color=discord.Color.blue())
    embed.add_field(name="Team", value=team_name)

    # Regular league stats
    embed.add_field(name="Regular League", value="-------------", inline=False)
    embed.add_field(name="Goals", value=str(goals))
    embed.add_field(name="Assists", value=str(assists))
    embed.add_field(name="Saves", value=str(saves))

    # Champions League stats
    embed.add_field(name="Champions League",
                    value="-------------",
                    inline=False)
    embed.add_field(name="Goals", value=str(cl_goals))
    embed.add_field(name="Assists", value=str(cl_assists))
    embed.add_field(name="Saves", value=str(cl_saves))

    # Calculate total stats
    total_goals = goals + cl_goals
    total_assists = assists + cl_assists
    total_saves = saves + cl_saves

    # Total stats
    embed.add_field(name="Total Stats", value="-------------", inline=False)
    embed.add_field(name="Total Goals", value=str(total_goals))
    embed.add_field(name="Total Assists", value=str(total_assists))
    embed.add_field(name="Total Saves", value=str(total_saves))

    await ctx.send(embed=embed)


@bot.tree.command(name="list_teams",
                  description="List all teams in the league")
async def list_teams(interaction: discord.Interaction):
    if not bot.league_data.teams:
        await interaction.response.send_message(
            "No teams have been created yet!", ephemeral=True)
        return

    embed = discord.Embed(title="League Teams", color=discord.Color.blue())
    for team_name, team_data in bot.league_data.teams.items():
        embed.add_field(name=team_name,
                        value=f"Captain: <@{team_data['captain_id']}>",
                        inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="list_players",
                  description="List all players in a team")
async def list_players(interaction: discord.Interaction, team_name: str):
    if team_name not in bot.league_data.teams:
        await interaction.response.send_message("This team does not exist!",
                                                ephemeral=True)
        return

    players = bot.league_data.teams[team_name]['players']
    embed = discord.Embed(title=f"Players in {team_name}",
                          color=discord.Color.blue())
    for player_id in players:
        embed.add_field(name="Player", value=f"<@{player_id}>", inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="delete_team",
                  description="Delete a team from the league")
async def delete_team(interaction: discord.Interaction, team_name: str):
    guild = interaction.guild
    if not is_league_admin(interaction.user, guild):
        embed = discord.Embed(
            title="Permission Denied",
            description="Only a League Admin/Admin can delete teams.",
            color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    if team_name not in bot.league_data.teams:
        await interaction.response.send_message("This team does not exist!",
                                                ephemeral=True)
        return

    # Remove team from all relevant dictionaries
    del bot.league_data.teams[team_name]
    to_remove = [
        player_id for player_id, tname in bot.league_data.player_teams.items()
        if tname == team_name
    ]
    for player_id in to_remove:
        del bot.league_data.player_teams[player_id]
    to_remove_captains = [
        captain_id
        for captain_id, tname in bot.league_data.team_captains.items()
        if tname == team_name
    ]
    for captain_id in to_remove_captains:
        del bot.league_data.team_captains[captain_id]

    # Remove Discord roles for the team and captain
    guild = interaction.guild
    team_role = discord.utils.get(guild.roles, name=team_name)
    captain_role = discord.utils.get(guild.roles, name=f"{team_name} Captain")
    Captain_global_role = discord.utils.get(guild.roles, name="Captain")
    if Captain_global_role:
        for member in Captain_global_role.members:
            await member.remove_roles(Captain_global_role)
        await Captain_global_role.delete()

    if team_role:
        for member in team_role.members:
            await member.remove_roles(team_role)
        await team_role.delete()

    if captain_role:
        for member in captain_role.members:
            await member.remove_roles(captain_role)
        await captain_role.delete()

    bot.league_data.save_data()
    await interaction.response.send_message(
        f"Team '{team_name}' and its roles have been deleted!", ephemeral=True)


@bot.tree.command(name="update_captain",
                  description="Change the captain of a team")
async def update_captain(interaction: discord.Interaction, team_name: str,
                         new_captain: discord.Member):
    guild = interaction.guild
    if not (is_team_captain(interaction.user, guild, team_name)
            or is_league_admin(interaction.user, guild)):
        embed = discord.Embed(
            title="Permission Denied",
            description=
            "Only the team captain or a League Admin/Admin can update the captain.",
            color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    new_captain_id = new_captain.id
    if new_captain_id not in bot.league_data.teams[team_name]['players']:
        await interaction.response.send_message(
            "The new captain must be a player in the team!", ephemeral=True)
        return

    # Get the old captain's ID
    old_captain_id = bot.league_data.teams[team_name]['captain_id']
    old_captain = guild.get_member(old_captain_id)

    # Get the captain role
    captain_role = discord.utils.get(guild.roles, name=f"{team_name} Captain")
    if not captain_role:
        await interaction.response.send_message(
            "Error: Captain role not found!", ephemeral=True)
        return

    # Remove captain role from old captain
    if old_captain and captain_role in old_captain.roles:
        await old_captain.remove_roles(captain_role)

    # Add captain role to new captain
    await new_captain.add_roles(captain_role)

    # Ensure the @Captain role exists and assign it to the new captain
    captain_global_role = discord.utils.get(interaction.guild.roles,
                                            name="Captain")
    if not captain_global_role:
        captain_global_role = await interaction.guild.create_role(
            name="Captain")
    await new_captain.add_roles(captain_global_role)

    # Remove @Captain role from the old captain
    if old_captain and captain_global_role in old_captain.roles:
        await old_captain.remove_roles(captain_global_role)

    # Update database
    bot.league_data.teams[team_name]['captain_id'] = new_captain_id
    # Remove old captain from team_captains
    if old_captain_id in bot.league_data.team_captains:
        del bot.league_data.team_captains[old_captain_id]
    # Add new captain to team_captains
    bot.league_data.team_captains[new_captain_id] = team_name
    bot.league_data.save_data()

    embed = discord.Embed(
        title="Captain Updated",
        description=f"Captain of '{team_name}' has been updated!",
        color=discord.Color.green())
    embed.add_field(name="New Captain", value=f"<@{new_captain_id}>")
    if old_captain:
        embed.add_field(name="Previous Captain", value=f"<@{old_captain_id}>")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="view_league_stats",
                  description="View overall league statistics")
async def view_league_stats(interaction: discord.Interaction):
    total_goals = sum(stats['goals']
                      for stats in bot.league_data.player_stats.values())
    total_assists = sum(stats['assists']
                        for stats in bot.league_data.player_stats.values())
    total_saves = sum(stats['saves']
                      for stats in bot.league_data.player_stats.values())

    embed = discord.Embed(title="League Statistics",
                          color=discord.Color.blue())
    embed.add_field(name="Total Goals", value=str(total_goals))
    embed.add_field(name="Total Assists", value=str(total_assists))
    embed.add_field(name="Total Saves", value=str(total_saves))

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="help", description="Display all available commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are all the available commands for the League Bot:",
        color=discord.Color.blue())

    # List of commands and their descriptions
    commands = [
        ("create_team <team_name>",
         "Create a new team and become its captain"),
        ("add_player <@user> <team_name>",
         "Add a player to your team (Captain/Admin only)"),
        ("remove_player <@user> <team_name>",
         "Remove a player from your team (Captain/Admin only)"),
        ("schedule_match <team1> <team2>",
         "Schedule a match between two teams (Captain/Admin only)"),
        ("list_matches", "List all scheduled matches"),
        ("set_score <match_id>", "Submit match score for a scheduled match"),
        ("stats <@user>", "View player statistics"),
        ("list_teams", "List all teams in the league"),
        ("list_players <team_name>", "List all players in a specific team"),
        ("delete_team <team_name>",
         "Delete a team from the league (Captain/Admin only)"),
        ("update_captain <team_name> <@user>",
         "Change the captain of a team (Captain/Admin only)"),
        ("view_league_stats", "View overall league statistics"),
        ("sync_commands", "Force sync all slash commands (admin only)"),
        ("initiate_league", "Initialize the league data (admin only)"),
        ("help", "Display this help message")
    ]

    for cmd, desc in commands:
        embed.add_field(name=f"/{cmd}", value=desc, inline=False)

    embed.set_footer(
        text=
        "Note: Some commands require captain or admin permissions. Use /list_matches to find match IDs for /set_score."
    )

    await interaction.response.send_message(embed=embed)


# Manual sync command for admins
@bot.tree.command(name="sync_commands",
                  description="Force sync all slash commands (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def sync_commands(interaction: discord.Interaction):
    try:
        # Defer the response since syncing might take some time
        await interaction.response.defer(ephemeral=True)

        # Sync commands globally
        await bot.tree.sync()

        # Sync commands for each guild
        for guild in bot.guilds:
            await bot.tree.sync(guild=guild)

        embed = discord.Embed(
            title="Commands Synced",
            description="Slash commands have been successfully synced!",
            color=discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        error_embed = discord.Embed(
            title="Error",
            description=f"An error occurred while syncing commands: {str(e)}",
            color=discord.Color.red())
        await interaction.followup.send(embed=error_embed, ephemeral=True)


@bot.tree.command(
    name="initiate_champions_league",
    description=
    "Initialize the Champions League data (admin only) with top 4 teams from each division"
)
async def initiate_champions_league(interaction: discord.Interaction):
    # First, clear any existing champions league data
    bot.league_data.cursor.execute("DELETE FROM champions_league_teams")
    bot.league_data.cursor.execute("DELETE FROM champions_league_standings")
    bot.league_data.conn.commit()

    # Get the top 4 teams from each division
    divisions = ["Division 1", "Division 2", "Division 3", "Division 4"]
    qualified_teams = []

    embed = discord.Embed(
        title="Champions League Qualifiers",
        description=
        "Top 4 teams from each division that qualified for Champions League!",
        color=discord.Color.gold())

    # Get top 4 teams from each division
    for division in divisions:
        bot.league_data.cursor.execute(
            """
            SELECT t.team_name, s.wins, s.losses, s.draws 
            FROM teams t
            JOIN standings s ON t.team_name = s.team_name
            WHERE t.division = ?
            ORDER BY s.wins DESC, s.losses ASC, s.draws DESC
            LIMIT 4
        """, (division, ))

        division_top_teams = bot.league_data.cursor.fetchall()
        qualified_teams.extend(division_top_teams)

        # Add to embed
        team_list = [
            f"{team[0]} ({team[1]}W-{team[2]}L-{team[3]}D)"
            for team in division_top_teams
        ]
        embed.add_field(
            name=f"{division} Qualifiers",
            value="\n".join(team_list) if team_list else "No teams",
            inline=False)

    # Send the initial qualification message
    await interaction.response.send_message(embed=embed)

    # Shuffle the qualified teams for random group assignment
    random.shuffle(qualified_teams)

    # Assign teams to Champions League groups
    groups = {
        "Group A": qualified_teams[0:4],
        "Group B": qualified_teams[4:8],
        "Group C": qualified_teams[8:12],
        "Group D": qualified_teams[12:16]
    }

    # Create Champions League groups embed
    groups_embed = discord.Embed(
        title="Champions League Groups",
        description="Teams have been assigned to Champions League groups!",
        color=discord.Color.blue())

    # Add teams to champions_league_teams and champions_league_standings tables
    for group_name, group_teams in groups.items():
        group_team_names = []

        for team_data in group_teams:
            team_name = team_data[0]
            group_team_names.append(team_name)

            # Get team data from regular league
            bot.league_data.cursor.execute(
                "SELECT captain_id, players FROM teams WHERE team_name = ?",
                (team_name, ))
            team_info = bot.league_data.cursor.fetchone()

            if team_info:
                captain_id, players = team_info

                # Add team to champions_league_teams table
                bot.league_data.cursor.execute(
                    "INSERT INTO champions_league_teams (team_name, captain_id, players, division) VALUES (?, ?, ?, ?)",
                    (team_name, captain_id, players, group_name))

                # Initialize team in champions_league_standings
                bot.league_data.cursor.execute(
                    "INSERT INTO champions_league_standings (team_name, wins, losses, draws) VALUES (?, 0, 0, 0)",
                    (team_name, ))

        # Add group to embed
        groups_embed.add_field(name=group_name,
                               value="\n".join(group_team_names)
                               if group_team_names else "No teams",
                               inline=False)

    bot.league_data.conn.commit()

    # Send the groups organization message
    await interaction.followup.send(embed=groups_embed)
    await interaction.followup.send(
        "Champions League has been successfully initialized!", ephemeral=True)


@bot.tree.command(
    name="initiate_league",
    description=
    "Initialize the league data (admin only), set the leagues as 4 divisions, 8 teams each"
)
async def initiate_league(interaction: discord.Interaction):
    # Randomize teams and assign them to divisions
    teams = list(bot.league_data.teams.keys())

    divisions = {
        "Division 1": teams[:8],
        "Division 2": teams[8:16],
        "Division 3": teams[16:24],
        "Division 4": teams[24:32]
    }

    embed = discord.Embed(title="League Divisions",
                          description="Teams have been assigned to divisions!",
                          color=discord.Color.green())

    for division_name, division_teams in divisions.items():
        embed.add_field(
            name=division_name,
            value=", ".join(division_teams) if division_teams else "No teams",
            inline=False)

    await interaction.response.send_message(embed=embed)

    # Update the database with the divisions
    for division_name, division_teams in divisions.items():
        for team in division_teams:
            bot.league_data.cursor.execute(
                "UPDATE teams SET division = ? WHERE team_name = ?",
                (division_name, team))
    bot.league_data.conn.commit()

    # Update the standings based on wins, losses, draws
    for division_name, division_teams in divisions.items():
        for team in division_teams:
            bot.league_data.cursor.execute(
                "UPDATE standings SET wins = 0, losses = 0, draws = 0 WHERE team_name = ?",
                (team, ))
    bot.league_data.conn.commit()

    await interaction.followup.send("League divisions have been initialized!",
                                    ephemeral=True)


@bot.tree.command(name="view_standings", description="View league standings")
async def view_standings(interaction: discord.Interaction):
    # Query with sorting done in SQL
    bot.league_data.cursor.execute("""
        SELECT team_name, wins, losses, draws
        FROM standings
        ORDER BY wins DESC, losses ASC, draws DESC
    """)
    standings = bot.league_data.cursor.fetchall()

    if not standings:
        await interaction.response.send_message("No standings available!",
                                                ephemeral=True)
        return

    # Create embed and format standings table
    embed = discord.Embed(title="League Standings", color=discord.Color.blue())
    standings_text = "```md\n# Team Name | Wins | Losses | Draws\n"
    standings_text += "-------------------------------------\n"
    for team_name, wins, losses, draws in standings:
        standings_text += f"{team_name} | {wins} | {losses} | {draws}\n"
    standings_text += "```"
    embed.description = standings_text


# Run the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)

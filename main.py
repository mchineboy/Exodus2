# Copyright <2023> <Craig J. Wessel>

# Import the required modules.
import discord
import random
import aiohttp
import aiomysql
import logging
import re
import asyncio
import os
import sys
import json
import urllib.parse
from datetime import datetime, timedelta
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv
from opencage.geocoder import OpenCageGeocode

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.DEBUG)

intents = discord.Intents.all()
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Connect to the MariaDB database.

async def connect_to_db():
    pool = await aiomysql.create_pool(
        host=os.getenv('DB_HOST'),
        port=3306,
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        db=os.getenv('DB_DATABASE'),
        autocommit=True
    )
    connection = await pool.acquire()
    return pool, connection


# Keep the MariaDB Connection Alive
@tasks.loop(minutes=5)
async def keep_alive(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")

# Create the users table if it doesn't already exist
async def create_users_table(pool):
    async with pool.acquire() as connection:
        async with connection.cursor() as cur:
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    location VARCHAR(255),
                    unit CHAR(1)
                )
            ''')

api_key = os.getenv('OPENWEATHERMAP_API_KEY')
opencage_api_key = os.getenv('OPENCAGE_API_KEY')

# Events

@client.event
async def on_ready():
    pool, connection = await connect_to_db()
    await create_users_table(pool)
    keep_alive.start(pool)  # Start the keep-alive task
    check_reminders.start(pool)
    print(f'We have logged in as {client.user}')

# Quotes for the Quote Command

quotes=[
    "<Leo7Mario> I want to make an IRC Bot, is there a way to make one in HTML?",
    "<`> Gerbils",
    "<|> Morse code is the best encryption algorhythm ever.",
    "<erno> Hmmm. I've lost a machine. Literally LOST. It responds to ping, it works completely, I just can't figure out where in my apartment it is.",
    "<Ubre> I'M RETARDED!",
    "<KK> Immo go rape my eyes.",
    "<KomputerKid> Hey did you know if you type your password in it shows up as stars! *********** See? "
    "<JacobGuy7800> mariospro "
    "<JacobGuy7800> Wait, DAMMIT",
    "<billy_mccletus> The onlee wuhn whose gunna be marryin' mah sister is gunna be me.",
    "<maxell> He just needs to realize we're one giant schizophrenic cat floating in a void...",
    "<KomputerKid> Why are you gae?",
    "<|> The holy bobble says 'Fuck you'"
]

# Definitions for the weather database.

async def set_user_location(user_id, location, pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('UPDATE users SET location = %s WHERE id = %s', (location, user_id))
            if cur.rowcount == 0:
                await cur.execute('INSERT INTO users (id, location) VALUES (%s, %s)', (user_id, location))
        await conn.commit()

async def set_user_unit(user_id, unit, pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('UPDATE users SET unit = %s WHERE id = %s', (unit, user_id))
            if cur.rowcount == 0:
                await cur.execute('INSERT INTO users (id, unit) VALUES (%s, %s)', (user_id, unit))
        await conn.commit()

async def get_user_location(user_id, pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT location FROM users WHERE id = %s", (user_id,))
            result = await cur.fetchone()
            return result[0] if result else None

async def get_user_unit(user_id, pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT unit FROM users WHERE id = %s", (user_id,))
            result = await cur.fetchone()
            return result[0] if result else None

# Classes and scripting for the Blackjack, poker, and play commands.

class Roulette:
    def __init__(self):
        self.gun = []
        self.bullets = [1]
        self.chambers = 6

        self.create_game()
        self.spin_chamber()

    def create_game(self):
        for bullet in self.bullets:
            for chamber in range(1, self.chambers + 1):
                self.gun.append((bullet, chamber))

    def spin_chamber(self):
        random.shuffle(self.gun)

class Blackjack:
    def __init__(self):
        self.deck = []
        self.suits = ('Hearts', 'Diamonds', 'Clubs', 'Spades')
        self.values = {'Two':2, 'Three':3, 'Four':4, 'Five':5, 'Six':6, 'Seven':7, 'Eight':8,
                       'Nine':9, 'Ten':10, 'Jack':10, 'Queen':10, 'King':10, 'Ace':11}
        self.ranks = ('Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
                      'Jack', 'Queen', 'King', 'Ace')
        self.create_deck()
        self.shuffle_deck()

    def create_deck(self):
        for suit in self.suits:
            for rank in self.ranks:
                self.deck.append((suit, rank))

    def shuffle_deck(self):
        random.shuffle(self.deck)

    def deal_card(self):
        return self.deck.pop()

    def calculate_score(self, hand):
        score = 0
        aces = 0
        for card in hand:
            rank = card[1]
            score += self.values[rank]
            if rank == 'Ace':
                aces += 1
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

class Poker:
    def __init__(self):
        self.deck = []
        self.suits = ('Hearts', 'Diamonds', 'Clubs', 'Spades')
        self.values = {'Two':2, 'Three':3, 'Four':4, 'Five':5, 'Six':6, 'Seven':7, 'Eight':8,
                       'Nine':9, 'Ten':10, 'Jack':11, 'Queen':12, 'King':13, 'Ace':14}
        self.ranks = ('Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
                      'Jack', 'Queen', 'King', 'Ace')
        self.create_deck()
        self.shuffle_deck()

    def create_deck(self):
        for suit in self.suits:
            for rank in self.ranks:
                self.deck.append((suit, rank))

    def shuffle_deck(self):
        random.shuffle(self.deck)

    def deal_card(self):
        return self.deck.pop()

    def calculate_score(self, hand):
        score = 0
        ranks = [card[1] for card in hand]
        rank_counts = {rank: ranks.count(rank) for rank in ranks}
        if len(set(ranks)) == 5:
            if max([self.values[rank] for rank in ranks]) - min([self.values[rank] for rank in ranks]) == 4:
                score += 100
            if len(set([card[0] for card in hand])) == 1:
                score += 1000
        if 4 in rank_counts.values():
            score += 750
        elif 3 in rank_counts.values() and 2 in rank_counts.values():
            score += 500
        elif 3 in rank_counts.values():
            score += 250
        elif len([count for count in rank_counts.values() if count == 2]) == 2:
            score += 100
        elif 2 in rank_counts.values():
            score += 50
        return score
    
class GeocodingService:
    async def get_coordinates(self, location):
        # Use the geocoding service to get the coordinates of the location
        coordinates = await self.fetch_coordinates_from_opencage(location)

        # Check if coordinates were obtained
        if coordinates:
            # Extract latitude and longitude
            latitude, longitude = coordinates

            # Use the weather service to get weather information
            weather_info = await weather_service.get_weather(latitude, longitude, location)

            # Check if weather information was obtained
            if weather_info:
                return weather_info
            else:
                return "Unable to fetch weather information."
        else:
            return "Unable to determine coordinates for the location."

    async def fetch_coordinates_from_opencage(self, location):
        geocoder = OpenCageGeocode(opencage_api_key)
        try:
            results = geocoder.geocode(location)

            if results and 'geometry' in results[0]:
                geometry = results[0]['geometry']
                return geometry['lat'], geometry['lng']
            else:
                print(f"No results found in OpenCage response for {location}")
            return None
        except Exception as e:
            print(f"Error in OpenCage API request: {e}")
        return None

class WeatherService:
    async def get_weather(self, latitude, longitude, location):
        # Use the geocoding service to get the coordinates of the location
        coordinates = await geocoding_service.fetch_coordinates_from_opencage(location)

        # Check if coordinates were obtained
        if coordinates:
            return coordinates  # Return the obtained coordinates
        else:
            return None

# Create instances of your services
geocoding_service = GeocodingService()
weather_service = WeatherService()

# Shutdown cleanup commands

async def cleanup_before_shutdown():
    await save_bot_state()
    await log_shutdown_event()
    await close_database_connection()

async def save_bot_state():
    # Example: Save user preferences to a JSON file
    user_preferences = {'user1': {'theme': 'dark', 'language': 'en'}, 'user2': {'theme': 'light', 'language': 'fr'}}
    with open('user_preferences.json', 'w') as file:
        json.dump(user_preferences, file)

async def log_shutdown_event():
    # Example: Log shutdown event to a file
    logging.basicConfig(filename='bot_shutdown.log', level=logging.INFO)
    logging.info('Bot is shutting down.')

async def close_database_connection():
    pool = None  # Initialize pool outside the try block

    try:
        # Retrieve connection details from environment variables
        host = os.getenv('DB_HOST')
        port = 3306
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        db = os.getenv('DB_DATABASE')

        # Establish the connection
        pool = await aiomysql.create_pool(host=host, port=port, user=user, password=password, db=db)

        # Add code here to perform any necessary database operations before closing

    finally:
        if pool:
            pool.close()
            await pool.wait_closed()


# Commands begin here.

# Blackjack command.

@tree.command(name="blackjack", description="Play blackjack!")
async def blackjack(interaction):
    play_again = True
    while play_again:
        game = Blackjack()
        player_hand = [game.deal_card(), game.deal_card()]
        dealer_hand = [game.deal_card(), game.deal_card()]
        await interaction.response.send_message(f'Your hand: {player_hand[0][1]} of {player_hand[0][0]}, {player_hand[1][1]} of {player_hand[1][0]}')
        await interaction.followup.send(f'Dealer hand: {dealer_hand[0][1]} of {dealer_hand[0][0]}, X')

        player_score = game.calculate_score(player_hand)
        dealer_score = game.calculate_score(dealer_hand)

        if player_score == 21:
            await interaction.followup.send('Blackjack! You win!')

        while player_score < 21:
            await interaction.followup.send('Type `h` to hit or `s` to stand.')
            msg = await client.wait_for('message')
            if msg.content.lower() == 'h':
                player_hand.append(game.deal_card())
                player_score = game.calculate_score(player_hand)
                hand_text = ', '.join([f'{card[1]} of {card[0]}' for card in player_hand])
                await interaction.followup.send(f'Your hand: {hand_text}')
            else:
                break

        if player_score > 21:
            await interaction.followup.send('Bust! You lose.')

        while dealer_score < 17:
            dealer_hand.append(game.deal_card())
            dealer_score = game.calculate_score(dealer_hand)

        hand_text = ', '.join([f'{card[1]} of {card[0]}' for card in dealer_hand])
        await interaction.followup.send(f'Dealer hand: {hand_text}')

        if dealer_score > 21:
            await interaction.followup.send('Dealer busts! You win!')
        elif dealer_score > player_score:
            await interaction.followup.send('Dealer wins!')
        elif dealer_score < player_score:
            await interaction.followup.send('You win!')
        else:
            await interaction.followup.send('Tie!')

        await interaction.followup.send('Do you want to play again? Type `y` for yes or `n` for no.')
        msg = await client.wait_for('message')
        if msg.content.lower() != 'y':
            play_again = False

# Poker command

@tree.command(name="poker", description="Play poker!")
async def poker(interaction):
    play_again = True
    while play_again:
        game = Poker()
        player_hand = [game.deal_card(), game.deal_card(), game.deal_card(), game.deal_card(), game.deal_card()]
        dealer_hand = [game.deal_card(), game.deal_card(), game.deal_card(), game.deal_card(), game.deal_card()]
        await interaction.response.send_message(f'Your hand: {player_hand[0][1]} of {player_hand[0][0]}, {player_hand[1][1]} of {player_hand[1][0]}, {player_hand[2][1]} of {player_hand[2][0]}, {player_hand[3][1]} of {player_hand[3][0]}, {player_hand[4][1]} of {player_hand[4][0]}')
        await interaction.followup.send('Type the numbers of the cards you want to discard (e.g., `1 3` to discard the first and third cards).')

        msg = await client.wait_for('message')
        discards = [int(i)-1 for i in msg.content.split()]
        for i in sorted(discards, reverse=True):
            player_hand.pop(i)
            player_hand.append(game.deal_card())

        hand_text = ', '.join([f'{card[1]} of {card[0]}' for card in player_hand])
        await interaction.followup.send(f'Your new hand: {hand_text}')

        player_score = game.calculate_score(player_hand)
        dealer_score = game.calculate_score(dealer_hand)

        hand_text = ', '.join([f'{card[1]} of {card[0]}' for card in dealer_hand])
        await interaction.followup.send(f'Dealer hand: {hand_text}')

        if dealer_score > player_score:
            await interaction.followup.send('Dealer wins!')
        elif dealer_score < player_score:
            await interaction.followup.send('You win!')
        else:
            await interaction.followup.send('Tie!')

        await interaction.followup.send('Do you want to play again? Type `y` for yes or `n` for no.')
        msg = await client.wait_for('message')
        if msg.content.lower() != 'y':
            play_again = False

# Russian Roulette Command

@tree.command(name='roulette', description='Play Russian Roulette!')
async def roulette(interaction):   
        game = Roulette()
        await interaction.response.send_message("Are you ready to pull the trigger? Type `s` to continue or `q` to pussy out.")
        msg = await client.wait_for('message')
        if msg.content.lower() != 'q':
            bullet, chamber = game.gun.pop(0)
            if bullet == 1 and chamber == 1:
                await interaction.followup.send("BLAMMO! You are dead!")
            else:
                await interaction.followup.send("Click! You survived!")
        else:
            await interaction.followup.send("WIMP! You pussied out!")

# Weather command! Fetch the weather!
@tree.command(name="weather", description="Fetch the weather!")
async def weather(interaction, location: str = None, unit: str = None):
    def filter_geonames(results):
        return [
            result for result in results
            if result['components']['_category'] == 'place'
            and result['components']['_type'] == 'city'
        ]

    async def get_city_details(location):
        geocoder = OpenCageGeocode(opencage_api_key)
        try:
            await interaction.response.defer()
            results = geocoder.geocode(location)
            print(f"OpenCage Response for {location}: {results}")

            results = filter_geonames(results)

            if results and 'components' in results[0]:
                components = results[0]['components']
                print(f"components: {components}")
                state_province = components.get('state') or components.get('state_code') or components.get('state_district') or ''
                country = components.get('country') or components.get('country_code') or ''

                print(f"DEBUG: state_province: {state_province}, country: {country}")

                # Return a dictionary with location information
                return {
                    'city': components.get('place'), 
                    'state_province': state_province, 
                    'country': country,
                    'lng': results[0]['geometry']['lng'],
                    'lat': results[0]['geometry']['lat']
                }
            else:
                print(f"No results found in OpenCage response for {city}")
                return {}
        except Exception as e:
            print(f"Error in OpenCage API request: {e}")
        return {}

    async def get_weather_info(latitude, longitude):
        # Use the weather service to get weather information
        weather_info = await weather_service.get_weather(latitude, longitude, location)
        return weather_info

    async with aiohttp.ClientSession() as session:
        # Connect to the database
        pool, connection = await connect_to_db()

        try:
            # If unit is not provided, retrieve the user's preferred unit from the database
            unit = await get_user_unit(interaction.user.id, pool)
            print(f"DEBUG: Unit retrieved from the database: {unit}")

            if not unit:
                # Default to Celsius if the unit is not provided and there is no unit in the database.
                unit = 'C'

            # Check if the location is not provided
            if location is None:
                # Retrieve the user's location from the database
                location = await get_user_location(interaction.user.id, pool)
                print(f"DEBUG: Location retrieved from the database: {location}")

                if not location:
                    await interaction.response.send_message('Please specify a location or set your location using the `setlocation` command.')
                    return

        finally:
            # Release the database connection
            await pool.release(connection)

            # Split the input into parts (city, state_province, country)
            location_parts = [part.strip() for part in location.split(',')]

            # Assign values based on the number of parts provided
            city = location_parts[0]
            state_province = location_parts[1] if state_province is None and len(location_parts) > 1 else ''
            country = location_parts[2] if country is None and len(location_parts) > 2 else ''

            # Use OpenCage to get state_province and country details.
            city_details = await get_city_details(f'{city} {state_province} {country}')
            state_province_cage = city_details.get('state_province', '')
            country_cage = city_details.get('country', '')

            state_province = state_province or state_province_cage or ''
            country = country_cage or country or ''

            # Construct the full location string without extra commas
            full_location = ', '.join(part for part in [city, state_province, country] if part)

            # Use the geocoding service to get coordinates
            coordinates = (city_details.get('lat'), city_details.get('lng'))

        # Check if coordinates were obtained
        if coordinates:
            # Extract latitude and longitude
            latitude, longitude = coordinates

            # Use the weather service to get weather information
            weather_info = await get_weather_info(latitude, longitude)

    async with aiohttp.ClientSession() as session:
        try:
            url = f'http://api.openweathermap.org/data/2.5/weather?q={urllib.parse.quote(full_location)}&appid={api_key}&units=metric'
            print(f"DEBUG: OpenWeatherMap API URL: {url}")

            async with session.get(url) as response:
                data = await response.json()

                print(f"DEBUG: OpenWeatherMap API Response: {data}")

            if data and data.get('cod') == 200:
                temp_celsius = data['main']['temp']
                description = data['weather'][0]['description']

                # Convert temperature based on the user's preferred unit
                if unit == 'F':
                    temp_fahrenheit = temp_celsius * 9/5 + 32
                    await interaction.followup.send(f'The current temperature in {full_location} is {temp_fahrenheit:.1f}°F with {description}.')
                elif unit == 'K':
                    temp_kelvin = temp_celsius + 273.15
                    await interaction.followup.send(f'The current temperature in {full_location} is {temp_kelvin:.2f}°K with {description}.')
                else:
                    await interaction.followup.send(f'The current temperature in {full_location} is {temp_celsius}°C with {description}.')
            else:
                await interaction.followup.send(f'The current weather in {full_location} is {weather_info}.')

        except Exception as e:
            error_message = f"Error in weather command: {e}"
            print(error_message)
            await interaction.followup.send(f"An error occurred while handling the weather command: {e}")

# Remind me command!

@tree.command(name='remind', description='Set a Reminder!')
async def remind(interaction, reminder_time: str, *, reminder: str):
    remind_time = parse_reminder_time(reminder_time)
    # Use create_pool directly here
    async with aiomysql.create_pool(
        host=os.getenv('DB_HOST'),
        port=3306,
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        db=os.getenv('DB_DATABASE'),
        autocommit=True
    ) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = "INSERT INTO reminders (user_id, reminder, remind_time) VALUES (%s, %s, %s)"
                val = (interaction.user.id, reminder, remind_time)
                await cur.execute(sql, val)
        await interaction.response.send_message(f'Reminder set! I will remind you at {remind_time}.')

def parse_reminder_time(reminder_time: str) -> datetime:
    # Implement your parsing logic here
    # Example: '2h30m' means 2 hours and 30 minutes
    # You need to convert this string into a timedelta object
    # You may use regular expressions to extract the time components

    # For simplicity, let's assume the input is in the format 'XhYmZs'
    hours, minutes, seconds = 0, 0, 0

    # Parse hours
    if 'h' in reminder_time:
        hours_str, reminder_time = reminder_time.split('h', 1)
        hours = int(hours_str)

    # Parse minutes
    if 'm' in reminder_time:
        minutes_str, reminder_time = reminder_time.split('m', 1)
        minutes = int(minutes_str)

    # Parse seconds
    if 's' in reminder_time:
        seconds_str, reminder_time = reminder_time.split('s', 1)
        seconds = int(seconds_str)

    # Calculate the total timedelta
    delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)

    return datetime.now() + delta
@tasks.loop(seconds=1)
async def check_reminders(pool):
    while True:
        now = datetime.now()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT user_id, reminder, remind_time FROM reminders WHERE remind_time <= %s", (now,))
                reminders = await cur.fetchall()
                for row in reminders:
                    user_id, reminder_message, remind_time = row
                    user = client.get_user(user_id)
                    await user.send(f'DO IT: {reminder_message}')
                    await cur.execute("DELETE FROM reminders WHERE user_id = %s AND reminder = %s AND remind_time = %s", (user_id, reminder_message, remind_time))
                    await conn.commit()

# 8ball command. It will tell you if you don't specify a question that you need to specify one.

@tree.command(name='8ball', description='Magic 8ball!')
async def _8ball(interaction, *, question: str = None):
    responses = ['It is certain.',
                 'It is decidedly so.',
                 'Without a doubt.',
                 'Yes - definitely.',
                 'You may rely on it.',
                 'As I see it, yes.',
                 'Most likely.',
                 'Outlook good.',
                 'Yes.',
                 'Signs point to yes.',
                 'Reply hazy, try again.',
                 'Ask again later.',
                 'Better not tell you now.',
                 'Cannot predict now.',
                 'Concentrate and ask again.',
                 'Don\'t count on it.',
                 'My reply is no.',
                 'My sources say no.',
                 'Outlook not so good.',
                 'Very doubtful.']
    if question is None:
        await interaction.response.send_message('Please specify a question to use the 8ball.')
    else:
        response = random.choice(responses)
        await interaction.response.send_message(response)

# Quote command. Pulls from quotes above.

@tree.command(name='quote', description='Get a random quote from the old IRC Days')
async def quote(interaction):
    random_quote = random.choice(quotes)
    await interaction.response.send_message(random_quote)

@tree.command(name='setlocation', description='Set your preferred location')
async def setlocation(interaction, location: str, state_province: str = None, country: str = None):
    pool, connection = await connect_to_db()

    # Check if the user's location is already set to the provided location
    current_location = await get_user_location(interaction.user.id, pool)
    if current_location == f"{location}, {state_province}, {country}" or current_location == f"{location}, {country}":
        await pool.release(connection)
        await interaction.response.send_message('Your location is already set to this location.')
        return

    full_location = f"{location}, {state_province}, {country}" if state_province else f"{location}, {country}"
    await set_user_location(interaction.user.id, full_location, pool)
    await pool.release(connection)
    await interaction.response.send_message(f'Your location has been set to {location}.')

# Set preferred units for the weather command. Stores this information in a mariadb database.

@tree.command(name='setunit', description='Set your preferred units')
async def setunit(interaction, *, unit: str):
    valid_units = ['C', 'F', 'K']
    
    # Check if the provided unit is valid
    if unit.upper() not in valid_units:
        await interaction.response.send_message('Invalid unit. Please specify either `C` for Celsius, `F` for Fahrenheit, or `K` for Kelvin.')
        return

    pool, connection = await connect_to_db()

    # Check if the user's preferred unit is already set to the specified unit
    current_unit = await get_user_unit(interaction.user.id, pool)
    if current_unit == unit.upper():
        await pool.release(connection)
        await interaction.response.send_message(f'Your preferred temperature unit is already set to {unit.upper()}.')
        return

    await set_user_unit(interaction.user.id, unit.upper(), pool)
    await pool.release(connection)
    await interaction.response.send_message(f'Your preferred temperature unit has been set to {unit.upper()}.')


# Coin Flip Command

@tree.command(name='flip', description='Flip a coin')
async def flip(interaction):
    responses = ['Heads',
                 'Tails']
    response = random.choice(responses)
    await interaction.response.send_message(response)

# About this bot.

@tree.command(name='about', description='About this bot')
async def about(interaction):
    response = 'Exodus2 is the successor to the old Exodus IRC bot re-written for Discord. I know many bots like this exist, but I wanted to write my own.'
    await interaction.response.send_message(response)

# Ping.

@tree.command(name='ping', description='Ping command')
async def ping(interaction):
    response = 'PONG!'
    await interaction.response.send_message(response)

# Help
    
@tree.command(name="help", description="Show help information")
async def help(interaction):
    embed = discord.Embed(title="Help", color=discord.Color.blurple())
    for cmd in tree.walk_commands():
        embed.add_field(name=cmd.name, value=cmd.description, inline=False)
    await interaction.response.send_message(embed==embed)

# Sync Command! ONLY THE OWNER CAN DO THIS!
    
@tree.command(name='sync', description='Owner only!')
async def sync(interaction: discord.Interaction):
    owner_id = os.getenv('OWNER_ID')
    if str(interaction.user.id) == owner_id: # Check if the user is the owner.
        try:
            await tree.sync()
            await interaction.response.send_message('Tree has been synced!')
            print('Command tree synced.')
        except Exception as e:
            print(e)
    else:
        await interaction.response.send_message('You must be the owner to use this command!')

# Shutdown command. ONLY THE OWNER CAN DO THIS!
@tree.command(name='shutdown', description='Gracefully kill the bot. OWNER ONLY!')
async def shutdown(interaction):
    owner_id = os.getenv('OWNER_ID')  # Get the owner ID from environment variable

    if str(interaction.user.id) == owner_id:  # Check if the user is the owner
        await interaction.response.send_message("Shutting down...")
        await cleanup_before_shutdown()
        await client.close()
    else:
        await interaction.response.send_message("You do not have permission to shut down the bot.")

# Restart the bot. ONLY THE OWNER CAN DO THIS!
@tree.command(name='restart', description='Gracefully reboot the bot. OWNER ONLY!')
async def restart(interaction):
    owner_id = os.getenv('OWNER_ID') # Get the owner ID from environment variable

    if str(interaction.user.id) == owner_id: # Check if the user is the owner.
        await interaction.response.send_message('Rebooting...')
        await cleanup_before_shutdown()
        await client.close()

        # Restart the bot
        os.execv(sys.executable, ['python'] + sys.argv)
    else:
        await interaction.response.send_message('You do not have permission to reboot the bot.')

client.run(os.getenv('DISCORD_TOKEN'))

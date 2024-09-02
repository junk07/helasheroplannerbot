import discord
from discord.ext import commands
import asyncio

from googleapiclient.discovery import build
from google.oauth2 import service_account

SERVICE_ACCOUNT_FILE = r"hela-hero-planner-256ecb561827.json"
SPREADSHEET_ID = '15ewV9pkz0TyzLxQQSb8KnYYeAskxDODqQA8mxwgWAwk' #contains Master Tab tab as well as User Hero Data tab
SPREADSHEET_ID_HERO_DATA = '1IEL1FVbCFNXqCUMfQQX8kQOIek-_J-Q9Z9EpGz-2lyA'  #contains Hero Data General tab

# Enable necessary intents 
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
service = build('sheets', 'v4', credentials=creds)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

    await bot.tree.sync() # Sync globally 

# hero_list command as a slash command
@bot.tree.command(name="hero_list", description="Display the list of heroes")
async def hero_list(interaction: discord.Interaction): 
    await interaction.response.defer() 

    # Wrap the entire command logic in an asyncio.wait_for block
    try:
        await asyncio.wait_for(asyncio.create_task(_hero_list_logic(interaction)), timeout=60) 
    except asyncio.TimeoutError:
        await interaction.followup.send("Request timed out. The command is taking too long to complete.")

# Helper function to encapsulate the hero_list logic
async def _hero_list_logic(interaction):
    range_name = 'Master Tab!A2:E' # Fetch both hero names (column A) and rarities (column E) 

    try:
        print("Fetching data from Google Sheets...")
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
        values = result.get('values', [])
        print("Data fetched successfully!")

         # Organize heroes by rarity
        heroes_by_rarity = {}
        for row in values:
            if not row:
                break
            name, rarity = row[0], row[4]
            heroes_by_rarity.setdefault(rarity, []).append(name)

        rarity_order = ["Common", "Fine", "Exquisite", "Epic"]

        if not any(heroes_by_rarity.values()):
            print("No heroes found")
            await interaction.followup.send('No heroes found in the sheet.') # ... (Handle no heroes found)
        else:
            output = ""
            index = 1 # Initialize the index counter

            for rarity in rarity_order:
                if rarity in heroes_by_rarity:
                    emoji = {'Epic': '🟠', 'Exquisite': '🟣', 'Fine': '🔵', 'Common': '🟢'}.get(rarity)
                    hero_list_with_emoji = [f"{emoji} {index + i}. {name}" for i, name in enumerate(heroes_by_rarity[rarity])]
                    output += f"**{rarity} Heroes**\n" 
                    output += "\n".join(hero_list_with_emoji) + "\n\n"
                    index += len(heroes_by_rarity[rarity]) # Increment the index based on the number of heroes in this rarity

            print("Sending hero list...")

             # Create an embed with all heroes in a single field
            embed = discord.Embed(title="Hero List", description=output)

            try:
                await interaction.followup.send(embed=embed) 
                print("Hero list sent!")
            except discord.errors.Forbidden:
                await interaction.followup.send("I don't have permission to send embeds here. Please enable the 'Embed Links' permission or try this command in a different channel.")

    except Exception as e:
        print(f"An error occurred: {e}")
        await interaction.followup.send(f'An error occurred: {e}') 

# New command: all_hero_statistics with a 60-second timeout
@bot.tree.command(name="all_hero_statistics", description="Provides a link to the hero statistics sheet")
async def all_hero_statistics(interaction: discord.Interaction):
    await interaction.response.defer() # Acknowledge the command immediately

     # Wrap the command logic in an asyncio.wait_for block with a 60-second timeout
    try:
        await asyncio.wait_for(asyncio.create_task(_all_hero_statistics_logic(interaction)), timeout=60)
    except asyncio.TimeoutError:
        await interaction.followup.send("Request timed out. The command is taking too long to complete.")

# Helper function to encapsulate the all_hero_statistics logic
async def _all_hero_statistics_logic(interaction):
    try:
        print("Preparing to send hero statistics link...")
        spreadsheet_url = "https://docs.google.com/spreadsheets/d/1IEL1FVbCFNXqCUMfQQX8kQOIek-_J-Q9Z9EpGz-2lyA/edit?usp=sharing" # Replace with your actual spreadsheet URL
        filter_view_guide_url = "https://support.google.com/docs/answer/3540681?hl=en" # Link to Google's filter view guide

        message = (
            "\n**Hela's Hero Planner Information Sheet**\n\n"
            "This sheet contains detailed statistics for all heroes. You can create custom filter views to easily find the information you need. \n\n" # Newline added here
            "Here's how to create one:\n\n"
             "1. **Click the 'Data' tab** at the top of the spreadsheet.\n" 
             "2. **Select 'Create a filter view'.** \n"
             "3. **Choose the columns you want to filter.** Click the filter icon in the column header and select your desired criteria.\n" 
             "4. **Name your filter view** (optional) to easily access it later.\n\n" # Newlines added here
             f"For more detailed instructions and screenshots, check out this guide: [Creating and using filter views](<{filter_view_guide_url}>)\n\n" 
             f"Access the sheet: [Hela's Hero Planner Information Sheet]({spreadsheet_url})"
         )

        print("Sending hero statistics link...")
        await interaction.followup.send(message)
        print("Hero statistics link sent successfully!")

    except Exception as e:
        print(f"An error occurred while sending the hero statistics link: {e}")
        await interaction.followup.send("An error occurred while processing your request. Please try again later.")

# Autocomplete function for hero_number_or_name
async def autocomplete_hero_info(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:
    if len(current) < 3:
        return []

    try:
        # Fetch all hero names from the spreadsheet 
        hero_names_range = 'Hero Data General!A2:A' 
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID_HERO_DATA, range=hero_names_range).execute()
        all_hero_names = [row[0] for row in result.get('values', []) if row]

    except Exception as e:
        print(f"An error occurred while fetching hero names for autocomplete: {e}")
        return []  # Return an empty list if there's an error

    # Filter hero names based on the current input
    matching_heroes = [
        discord.app_commands.Choice(name=name, value=name)
        for name in all_hero_names if current.lower() in name.lower()
    ]

    # Limit the number of suggestions to 25 (Discord's limit)
    return matching_heroes[:25]

# hero_info command as a slash command with user input
@bot.tree.command(name="hero_info", description="Fetch information for a specific hero by name or assigned number from hero_list")
async def hero_info(interaction: discord.Interaction, hero_number_or_name: str):
    await interaction.response.defer() 

    try:
        await asyncio.wait_for(asyncio.create_task(_process_hero_selection(interaction, hero_number_or_name)), timeout=60)
    except asyncio.TimeoutError:
        await interaction.followup.send("Request timed out. Processing hero information is taking too long.")

# Attach the autocomplete function to the hero_info command parameter
hero_info.autocomplete("hero_number_or_name")(autocomplete_hero_info)

# Helper function to handle hero selection and subsequent actions
async def _process_hero_selection(interaction, hero_number_or_name):
    try:
        print(f"User provided {hero_number_or_name}. Fetching hero information...")

        # Fetch all data from the 'Hero Data General' tab
        data_range = 'Hero Data General!A1:ZZ' 
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID_HERO_DATA, range=data_range).execute()
        values = result.get('values', [])
        print(f"Data fetched successfully!")

        # Find the row for the selected hero
        headers = values[0]
        hero_row = None

        if hero_number_or_name.isdigit():
            hero_number = int(hero_number_or_name)

            # Fetch hero names and their assigned numbers from the 'Master Tab'
            master_tab_range = 'Master Tab!A2:E'
            master_tab_result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=master_tab_range).execute()
            master_tab_values = master_tab_result.get('values', [])

            # Organize heroes by rarity and assign numbers
            heroes_by_rarity = {}
            for i, row in enumerate(master_tab_values):
                if not row:
                    break
                name, rarity = row[0], row[4]
                heroes_by_rarity.setdefault(rarity, []).append(name)

            rarity_order = ["Common", "Fine", "Exquisite", "Epic"]
            index = 1

            for rarity in rarity_order:
                if rarity in heroes_by_rarity:
                    for name in heroes_by_rarity[rarity]:
                        if index == hero_number:
                            hero_row = next((row for row in values if row and row[0] == name), None)
                            break # Stop searching once the hero is found
                        index += 1
                    if hero_row: # If the hero was found, break out of the outer loop as well
                        break

        else:
            hero_row = next((row for row in values if row and row[0] == hero_number_or_name), None)

        if hero_row:
            # Create the embed with hero information, formatting header text as bold and combining Council/March info
            print(f"Creating embed for {hero_row[0]}...")
            embed = discord.Embed(title=f"{hero_row[0]} Information")
            field_value = "" 
            council_or_march_value = None 
            for i in range(len(headers)):
                if i < len(hero_row) and hero_row[i]: 
                    if "council or march" in headers[i].lower():
                        council_or_march_value = hero_row[i]  # Store the value
                    elif headers[i].lower() == "signature skill":
                        if council_or_march_value:  # Check if we have a value to combine
                            field_value += f"**{headers[i]}**: {council_or_march_value} - {hero_row[i]}\n"
                            council_or_march_value = None  # Reset after combining
                        else:
                            field_value += f"**{headers[i]}**: {hero_row[i]}\n"  # Display as is if no value to combine
                    elif headers[i].lower().startswith("level") and council_or_march_value:
                        field_value += f"**{headers[i]}**: {council_or_march_value} - {hero_row[i]}\n"
                        council_or_march_value = None  # Reset after combining
                    else:
                        field_value += f"**{headers[i]}**: {hero_row[i]}\n"

            embed.add_field(name="\u200b", value=field_value, inline=False)
            print(f"Embed created successfully for {hero_row[0]}!")

            print(f"Sending information for {hero_row[0]}...")
            await interaction.followup.send(embed=embed)
            print(f"Information for {hero_row[0]} sent successfully!")

        else:
            print(f"Hero with identifier {hero_number_or_name} not found.")
            await interaction.followup.send(f"Hero with identifier {hero_number_or_name} not found in the sheet.")

    except Exception as e:
        print(f"An error occurred while processing hero information: {e}")
        await interaction.followup.send("An error occurred while processing your request. Please try again later.")

# Autocomplete function for hero_number_or_name (used in both hero_info and add_hero)
async def autocomplete_hero_info(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:
    if len(current) < 3:
        return []

    try:
        # Fetch all hero names from the spreadsheet 
        hero_names_range = 'Hero Data General!A2:A' 
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID_HERO_DATA, range=hero_names_range).execute()
        all_hero_names = [row[0] for row in result.get('values', []) if row]

    except Exception as e:
        print(f"An error occurred while fetching hero names for autocomplete: {e}")
        return []  # Return an empty list if there's an error

    # Filter hero names based on the current input
    matching_heroes = [
        discord.app_commands.Choice(name=name, value=name)
        for name in all_hero_names if current.lower() in name.lower()
    ]

    # Limit the number of suggestions to 25 (Discord's limit)
    return matching_heroes[:25]

# /add_hero command
@bot.tree.command(name="add_hero", description="Add a hero to your tracking list")
async def add_hero(interaction: discord.Interaction, hero_name: str):
    await interaction.response.defer()  # Acknowledge the command immediately

    try:
        user_id = interaction.user.id

        # ... (Check if the hero exists in the 'Hero Data General' sheet - this part remains the same)

        print(f"Hero {hero_name} exists. Checking if already added...")

        # Check if the hero is already added by the user
        user_hero_data_range = f'{SPREADSHEET_ID}User Hero Data!A2:B' 
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=user_hero_data_range).execute() 
        user_data = result.get('values', [])

        existing_row_index = None
        for i, row in enumerate(user_data):
            if row and row[0] == str(user_id) and row[1] == hero_name:
                existing_row_index = i + 2  # Adjust for 0-based indexing and header row
                break

        if existing_row_index:
            print(f"Hero {hero_name} already added by user {user_id}. Updating existing row...")
            
            # Update the existing row (you'll need to adjust the values based on your data structure)
            values = [[user_id, hero_name]]  # Add other updated data columns as needed
            body = {'values': values}
            result = service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f'{SPREADSHEET_ID}!A{existing_row_index}:B{existing_row_index}',  # Update the specific row
                valueInputOption='RAW',
                body=body
            ).execute()

            await interaction.followup.send(f"Hero '{hero_name}' already exists in your tracking list. Its data has been updated.")

        else:
            print(f"Adding hero {hero_name} for user {user_id}...")

            # Insert hero data into the 'User Hero Data' sheet
            values = [[user_id, hero_name]]  # Add other data columns as needed
            body = {'values': values}
            result = service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=SPREADSHEET_ID, 
                valueInputOption='RAW', 
                body=body
            ).execute()

            print(f"Hero {hero_name} added successfully for user {user_id}.")
            await interaction.followup.send(f"Hero '{hero_name}' added to your tracking list!")

    except Exception as e:
        print(f"An error occurred while adding/updating hero: {e}")
        await interaction.followup.send("An error occurred while processing your request. Please try again later.")

# Attach the autocomplete function to the add_hero command parameter
add_hero.autocomplete("hero_name")(autocomplete_hero_info)

bot.run("MTI3OTgwMTc1MDY1NTg2NDgzMg.GwwLJ7.srhVj6BNTPN_odUdSUdi-ki-jJksKv7vf095K4")

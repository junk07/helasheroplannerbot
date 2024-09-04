import discord
from discord.ext import commands
import asyncio

from googleapiclient.discovery import build
from google.oauth2 import service_account

SERVICE_ACCOUNT_FILE = "hela-hero-planner-256ecb561827.json"
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

@bot.tree.command(name="add_hero", description="Add a hero to your tracking list")
async def add_hero(interaction: discord.Interaction, hero_name: str):
    await interaction.response.defer()

    try:
        # Wrap the potentially long-running parts in an asyncio.wait_for block
        async with asyncio.timeout(60):  # Timeout after 60 seconds
            user_id = str(interaction.user.id)

            # Check if the hero exists in the 'Hero Data General' sheet
            hero_data_range = 'Hero Data General!A2:A' 
            result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID_HERO_DATA, range=hero_data_range).execute()
            hero_names = [row[0] for row in result.get('values', []) if row]

            if hero_name not in hero_names:
                await interaction.followup.send(f"Hero '{hero_name}' not found in the database. Please double-check the spelling or use the autocomplete feature for suggestions.")
                return

            print(f"Hero {hero_name} exists. Checking if already added...")

            # Fetch all data from the 'User Hero Data' sheet
            user_hero_data_range = 'User Hero Data!A2:B' 
            result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=user_hero_data_range).execute() 
            user_data = result.get('values', [])
            print(f"Fetched user data: {user_data}")

            # Iterate through the rows and check for duplicates
            for row in user_data:
                print(f"Checking row: {row}")
                if row and row[0] == user_id and row[1].strip() == hero_name:
                    raise Exception(f"Hero '{hero_name}' is already in your tracking list.")

            print(f"Adding hero {hero_name} for user {user_id}...")

            # Insert hero data into the 'User Hero Data' sheet
            values = [[user_id, hero_name]] 
            body = {'values': values}
            result = service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range='User Hero Data',
                valueInputOption='RAW',
                body=body
            ).execute()

            print(f"Hero {hero_name} added successfully for user {user_id}.")
            await interaction.followup.send(f"Hero '{hero_name}' added to your tracking list!")

    except asyncio.TimeoutError:
        await interaction.followup.send("The request timed out. Adding the hero is taking too long. Please try again later.")
    except Exception as e:
        if "already in your tracking list" in str(e):
            await interaction.followup.send(f"You already have '{hero_name}' in your tracking list. You can only add each hero once.")
        else:
            print(f"An unexpected error occurred while adding the hero: {e}")
            await interaction.followup.send("An unexpected error occurred while adding the hero. Please try again later or contact the Hela if the issue persists.")

# Attach the autocomplete function to the add_hero command parameter
add_hero.autocomplete("hero_name")(autocomplete_hero_info)

@bot.tree.command(name="my_heroes", description="Display the list of heroes you have added")
async def my_heroes(interaction: discord.Interaction):
    await interaction.response.defer() 

    user_id = str(interaction.user.id) 

    try:
        # Fetch user's heroes from 'User Hero Data' sheet
        user_hero_data_range = 'User Hero Data!A2:B'
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=user_hero_data_range).execute()
        user_data = result.get('values', [])

        user_heroes = [row[1] for row in user_data if row and row[0] == user_id]

        if not user_heroes:
            await interaction.followup.send("You haven't added any heroes yet!") 
            return

        embed = discord.Embed(title=f"{interaction.user.name}'s Heroes") 

        # Format hero information for the embed, removing bold formatting and extra lines
        hero_list = "\n".join(user_heroes)  
        embed.add_field(name="Heroes", value=hero_list, inline=False)

        await interaction.followup.send(embed=embed) 

    except Exception as e: 
        print(f"An error occurred while fetching user heroes: {e}")
        await interaction.followup.send("An error occurred while fetching your heroes. Please try again later.") 

@bot.tree.command(name="remove_hero", description="Remove a hero from your tracking list")
async def remove_hero(interaction: discord.Interaction, hero_name: str):
    await interaction.response.defer()

    user_id = str(interaction.user.id)

    try:
        print(f"Attempting to remove hero '{hero_name}' for user {user_id}")

        # Fetch user's heroes from 'User Hero Data' sheet
        user_hero_data_range = 'User Hero Data!A2:B'
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=user_hero_data_range).execute()
        user_data = result.get('values', [])

        print(f"Fetched user data: {user_data}")

        # Find the row index to delete
        row_index_to_delete = None
        for i, row in enumerate(user_data):
            if row and row[0] == user_id and row[1].strip() == hero_name:
                row_index_to_delete = i + 2  # +2 to account for header row and 0-based indexing
                break

        if row_index_to_delete:
            print(f"Found hero to delete at row index {row_index_to_delete}")

            # --- Place the code block to print sheet properties here ---
            spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
            sheets = spreadsheet.get('sheets', '')
            for sheet in sheets:  

                print(f"Sheet Name: {sheet['properties']['title']}, Sheet ID: {sheet['properties']['sheetId']}")
            # --- End of code block ---

            # Delete the row
            requests = [{
                "deleteDimension": {
                    "range": {
                        "sheetId": 1156414171,  # Assuming 'User Hero Data' is the second sheet
                        "dimension": "ROWS",
                        "startIndex": row_index_to_delete - 1,
                        "endIndex": row_index_to_delete,
                    }
                }
            }]

            body = {'requests': requests}
            service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()

            print(f"Hero '{hero_name}' removed successfully for user {user_id}")
            await interaction.followup.send(f"Hero '{hero_name}' removed from your tracking list!")
        else:
            print(f"Hero '{hero_name}' not found in user's list")
            await interaction.followup.send(f"Hero '{hero_name}' not found in your tracking list.")

    except Exception as e:
        print(f"An error occurred while removing the hero: {e}")
        await interaction.followup.send("An error occurred while removing the hero. Please try again later.")

# Attach the autocomplete function to the remove_hero command parameter (reuse the existing one)
remove_hero.autocomplete("hero_name")(autocomplete_hero_info)

@bot.tree.command(name="manage_hero", description="Update the current level of a tracked hero")
async def manage_hero(interaction: discord.Interaction, hero_name: str, current_level: int = None,current_relics: int = None, next_goal_level: int = None, ultimate_goal_level: int = None):
    global existing_hero_data

    await interaction.response.defer()

    try:
        # 1. Fetch existing hero data from 'User Hero Data'
        user_hero_data_range = 'User Hero Data!A2:F' 
        print(f"Fetching existing hero data for {hero_name} from {user_hero_data_range}...") 
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=user_hero_data_range).execute()
        user_data = result.get('values', [])
        print(f"User data fetched: {user_data}") 

        # 2. Find the row to update, matching both user_id and hero_name
        user_id = str(interaction.user.id) 
        row_to_update = next(
            (i + 2 for i, row in enumerate(user_data) if row and row[0] == user_id and row[1] == hero_name),
            None
        )
        print(f"Row to update: {row_to_update}") 

        if row_to_update is None:
            raise ValueError(f"{hero_name} was not found in your tracking list. Add the hero first using the 'add_hero' command.")
        
        # 3. Fetch existing hero data (to get current level, relics, and next goal level)
        existing_hero_data = next((row for row in user_data if row and row[0] == str(interaction.user.id) and row[1] == hero_name), None)

        # 4. Fetch hero's max level from 'Hero Data General' sheet 
        max_level_range = f'Hero Data General!A2:C'
        print(f"4. Fetching all hero data (including max level) from {max_level_range}...")  
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID_HERO_DATA, 
            range=max_level_range
        ).execute()
        hero_data = result.get('values', [])
        print(f"Hero data fetched: {hero_data}")

        # 5. Find the row containing the hero's data and extract max_level
        hero_row = next((row for row in hero_data if row and row[0] == hero_name), None)
        if hero_row is None:
            raise ValueError(f"{hero_name} was not found in the hero database. (This should not happen, please contact Hela)") 

        max_level = int(hero_row[2])
        print(f"Max level for {hero_name}: {max_level}")

        # 6. Input validation for current_level (if provided)
        if current_level is not None and not (0 <= current_level <= max_level):
            raise ValueError(f"You have entered an invalid current level value for {hero_name} Please enter a value between 0 and {max_level}.")
        
        # Additional check: current_level should not be higher than next_goal_level (if provided)
        if next_goal_level is not None and current_level > next_goal_level:
            raise ValueError(f"Current level cannot be higher than the next goal level.")
        
        # 7. Input validation for current_relics (if provided)
        if current_relics is not None and current_relics < 0:
            raise ValueError("Current relics cannot be negative.")
        
        # 8. Input validation for next_goal_level (if provided)
        if next_goal_level is not None:
            # Get the current level, either from the provided input or the existing data
            current_level_for_goal_check = current_level if current_level is not None else \
                (int(existing_hero_data[2]) if len(existing_hero_data) > 2 and existing_hero_data[2] else 0)

            # Handle the case where current_level_for_goal_check is None
            if current_level_for_goal_check is None:
                current_level_for_goal_check = 0  # Set to 0 if not available

            if not (current_level_for_goal_check <= next_goal_level <= max_level):
                raise ValueError(f"Invalid next goal level value. Please enter a value between the current level you have for this hero ({current_level_for_goal_check}) and the max level for this hero ({max_level}) or leave it blank.")
            
            # Additional check: next_goal_level should not be higher than ultimate_goal_level (if provided)
            if ultimate_goal_level is not None and next_goal_level > ultimate_goal_level:
                raise ValueError(f"Next goal level cannot be higher than the ultimate goal level.")
            
        # 10. Input validation for ultimate_goal_level (if provided)
        if ultimate_goal_level is not None:
            # Get the next_goal_level, either from the provided input or the existing data
            next_goal_level_for_check = next_goal_level if next_goal_level is not None else \
                (int(existing_hero_data[4]) if len(existing_hero_data) > 4 and existing_hero_data[4] else 0)

            # If next_goal_level is also not available, use current_level
            if next_goal_level_for_check is None or next_goal_level_for_check == 0:
                next_goal_level_for_check = current_level if current_level is not None else \
                    (int(existing_hero_data[2]) if len(existing_hero_data) > 2 and existing_hero_data[2] else 0)

            if not (next_goal_level_for_check <= ultimate_goal_level <= max_level):
                raise ValueError(f"Invalid ultimate goal level value. Please enter a value between the next goal level ({next_goal_level_for_check}) and the max level for this hero ({max_level}) or leave it blank.")
            
            # Additional check: current_level should not be higher than ultimate_goal_level
            if current_level is not None and current_level > ultimate_goal_level:
                raise ValueError(f"Current level cannot be higher than the ultimate goal level.")
        
        # 11. Prepare the data to be updated, preserving existing values if not provided
        values_to_update = []
        if current_level is not None:
            values_to_update.append(current_level)
        else:
            values_to_update.append(int(existing_hero_data[2]) if len(existing_hero_data) > 2 and existing_hero_data[2] else 0)  # Preserve existing level if not provided

        if current_relics is not None:
            values_to_update.append(current_relics)
        else:
            values_to_update.append(int(existing_hero_data[3]) if len(existing_hero_data) > 3 and existing_hero_data[3] else 0) # Preserve existing relics if not provided

        if next_goal_level is not None:
            values_to_update.append(next_goal_level)
        else:
            values_to_update.append(existing_hero_data[4] if len(existing_hero_data) > 4 and existing_hero_data[4] else '')

        if ultimate_goal_level is not None:
            values_to_update.append(ultimate_goal_level)
        else:
            values_to_update.append(existing_hero_data[5] if len(existing_hero_data) > 5 and existing_hero_data[5] else '')

        # 12. Update the spreadsheet
        range_to_update = f'User Hero Data!C{row_to_update}:F{row_to_update}'  # Update columns C, D, E, and F
        body = {'values': [values_to_update]}
        print(f"Updating spreadsheet at range {range_to_update} with values: {values_to_update}")
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_update,
            valueInputOption='RAW',
            body=body
        ).execute()

        # 13. Construct the success message based on which fields were updated
        updated_fields = []
        if current_level is not None:
            updated_fields.append("current level")
        if current_relics is not None:
            updated_fields.append("current relics")
        if next_goal_level is not None:
            updated_fields.append("next goal level")
        if ultimate_goal_level is not None:
            updated_fields.append("ultimate goal level")

        success_message = f"{hero_name} " 
        if updated_fields:
            success_message += f"{' and '.join(updated_fields)} updated successfully!"
        else:
            success_message += "not updated. No new values were provided."

        await interaction.edit_original_response(content=success_message)

    except ValueError as e:
        await interaction.edit_original_response(content=str(e))
    except Exception as e:
        print(f"An error occurred while updating hero data: {e}")
        await interaction.edit_original_response(content="An error occurred while updating hero data. Please try again later.")

# Attach the autocomplete function to the manage_hero command parameter 
manage_hero.autocomplete("hero_name")(autocomplete_hero_info)

@bot.tree.command(name="my_heroes_with_input_information", description="Display a list of your tracked heroes with the information you have entered for them")
async def my_heroes_with_input_information(interaction: discord.Interaction):
    await interaction.response.defer()

    user_id = str(interaction.user.id)

    try:
        # Fetch user's heroes with additional data from 'User Hero Data' sheet
        user_hero_data_range = 'User Hero Data!A2:F'  # Include columns C to F for level, relics, and goals
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=user_hero_data_range).execute()
        user_data = result.get('values', [])

        user_heroes_data = [row for row in user_data if row and row[0] == user_id]

        if not user_heroes_data:
            await interaction.followup.send("You haven't added any heroes yet!")
            return

        # Paginate the hero data
        heroes_per_page = 10  
        current_page = 0
        total_pages = (len(user_heroes_data) + heroes_per_page - 1) // heroes_per_page 

        def create_embed(page_num):
            start_idx = page_num * heroes_per_page
            end_idx = min(start_idx + heroes_per_page, len(user_heroes_data))
            page_heroes_data = user_heroes_data[start_idx:end_idx]

            embed = discord.Embed(title=f"{interaction.user.name}'s Hero Overview (Page {page_num + 1}/{total_pages})")

            for hero_data in page_heroes_data:
                hero_name = hero_data[1]
                hero_name_with_underline = f"__{hero_name}__"
                current_level = hero_data[2] if len(hero_data) > 2 and hero_data[2] else "N/A"
                current_relics = hero_data[3] if len(hero_data) > 3 and hero_data[3] else "N/A"
                next_goal_level = hero_data[4] if len(hero_data) > 4 and hero_data[4] else "N/A"
                ultimate_goal_level = hero_data[5] if len(hero_data) > 5 and hero_data[5] else "N/A"

                hero_info = (
                    f"**Current Level:** {current_level}\n"
                    f"**Current Relics:** {current_relics}\n"
                    f"**Next Goal Level:** {next_goal_level}\n"
                    f"**Ultimate Goal Level:** {ultimate_goal_level}\n"
                )

                embed.add_field(name=hero_name_with_underline, value=hero_info, inline=False)
            return embed

        # Create the initial embed
        embed = create_embed(current_page)

        # Create buttons for navigation
        previous_button = discord.ui.Button(label="Previous", style=discord.ButtonStyle.blurple, disabled=True) 
        next_button = discord.ui.Button(label="Next", style=discord.ButtonStyle.blurple, disabled=total_pages == 1) 

        # View to hold the buttons
        view = discord.ui.View()
        view.add_item(previous_button)
        view.add_item(next_button)

        # Button callback functions
        async def previous_callback(interaction):
            nonlocal current_page
            current_page -= 1
            await interaction.response.edit_message(embed=create_embed(current_page), view=update_view())

        async def next_callback(interaction):
            nonlocal current_page
            current_page += 1
            await interaction.response.edit_message(embed=create_embed(current_page), view=update_view())

        # Function to update button states based on current_page
        def update_view():
            previous_button.disabled = current_page == 0
            next_button.disabled = current_page == total_pages - 1
            return view

        # Assign callbacks to the buttons
        previous_button.callback = previous_callback
        next_button.callback = next_callback

        # Send the initial embed with the buttons
        await interaction.followup.send(embed=embed, view=view)

    except Exception as e:
        print(f"An error occurred while fetching user heroes: {e}")
        await interaction.followup.send("An error occurred while fetching your heroes. Please try again later.")

@bot.tree.command(name="calculate_relics_needed", description="Calculate relics needed for various goals for a tracked hero")
async def calculate_relics_needed(interaction: discord.Interaction, hero_name: str):
    await interaction.response.defer()

    try:
        # 1. Fetch existing hero data from 'User Hero Data'
        user_hero_data_range = 'User Hero Data!A2:J'  # Include columns up to J for calculations
        print(f"1. Fetching existing hero data for {hero_name} from {user_hero_data_range}...")
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=user_hero_data_range).execute()
        user_data = result.get('values', [])
        print(f"1. User data fetched: {user_data}")

        # 2. Find the row to update, matching both user_id and hero_name
        user_id = str(interaction.user.id)
        row_to_update = next(
            (i + 2 for i, row in enumerate(user_data) if row and row[0] == user_id and row[1] == hero_name),
            None
        )
        print(f"2. Row to update: {row_to_update}")

        if row_to_update is None:
            raise ValueError(f"2. Hero '{hero_name}' was not found in your tracking list. Add the hero first using the 'add_hero' command.")

        # 3. Fetch existing hero data (to get current level, relics, and goals)
        existing_hero_data = next((row for row in user_data if row and row[0] == str(interaction.user.id) and row[1] == hero_name), None)

        # 4. Fetch hero's max level from 'Hero Data General' sheet 
        max_level_range = f'Hero Data General!A2:C'
        print(f"4. Fetching all hero data (including max level) from {max_level_range}...")  
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID_HERO_DATA, 
            range=max_level_range
        ).execute()
        hero_data = result.get('values', [])
        print(f"4. Hero data fetched: {hero_data}")

        # 5. Find the row containing the hero's data and extract max_level
        hero_row = next((row for row in hero_data if row and row[0] == hero_name), None)
        if hero_row is None:
            raise ValueError(f"5. Hero '{hero_name}' was not found in the hero database. (This should not happen, please contact Hela)") 

        max_level = int(hero_row[2])
        print(f"5. Max level for {hero_name}: {max_level}")

        # 6. Get current level, relics, and goals from existing data or defaults
        current_level = int(existing_hero_data[2]) if len(existing_hero_data) > 2 and existing_hero_data[2] else 0
        current_relics = int(existing_hero_data[3]) if len(existing_hero_data) > 3 and existing_hero_data[3] else 0
        
        # Handle empty strings as None for goal levels
        next_goal_level = int(existing_hero_data[4]) if len(existing_hero_data) > 4 and existing_hero_data[4] else None
        if next_goal_level == 0:  # Treat 0 as not set
            next_goal_level = None

        ultimate_goal_level = int(existing_hero_data[5]) if len(existing_hero_data) > 5 and existing_hero_data[5] else None
        if ultimate_goal_level == 0:
            ultimate_goal_level = None

        # 7. Calculate relic requirements
        relic_milestones = [1, 10, 20, 30, 40, 50, 60]
        relic_costs = [500, 6100, 13000, 54000, 80000, 100000, 120000]

        # Next unlock level (no changes here)
        next_unlock = next((level for level in relic_milestones if level > current_level and level <= max_level), "Hero Already Maxed")
        if next_unlock == "Hero Already Maxed":
            relics_to_next_unlock = "Hero Already Maxed"
        else:
            relics_to_next_unlock = relic_costs[relic_milestones.index(next_unlock)] - current_relics
            if relics_to_next_unlock < 0:
                relics_to_next_unlock = "You already have enough relics for the next unlock level"

        # Next goal level (modified to handle non-milestone goal levels)
        if next_goal_level is None:
            relics_to_next_goal = "No next goal level has been set"
        elif current_level >= next_goal_level:
            relics_to_next_goal = "Current level is higher than next goal level, please adjust using /manage_hero"
        else:
            # Find milestones within the range [current_level, next_goal_level]
            milestones_in_range = [level for level in relic_milestones if current_level < level <= next_goal_level]

            # Calculate the relic cost for each milestone in the range
            total_relic_cost = sum(relic_costs[relic_milestones.index(level)] for level in milestones_in_range)

            relics_to_next_goal = total_relic_cost - current_relics
            if relics_to_next_goal < 0:
                relics_to_next_goal = "You already have enough relics for the next goal level"

        # Ultimate goal level (modified similarly to next_goal_level)
        if ultimate_goal_level is None:
            relics_to_ultimate_goal = "No ultimate goal level has been set"
        elif current_level >= ultimate_goal_level:
            relics_to_ultimate_goal = "Current level is higher than ultimate goal level, please adjust using /manage_hero"
        else:
            # Find milestones within the range [current_level, ultimate_goal_level]
            milestones_in_range = [level for level in relic_milestones if current_level < level <= ultimate_goal_level]

            # Calculate the relic cost for each milestone in the range
            total_relic_cost = sum(relic_costs[relic_milestones.index(level)] for level in milestones_in_range)

            relics_to_ultimate_goal = total_relic_cost - current_relics
            if relics_to_ultimate_goal < 0:
                relics_to_ultimate_goal = "You already have enough relics for the ultimate goal level"

        # 8. Update calculated values in the spreadsheet (columns G to J)
        range_to_update = f'User Hero Data!G{row_to_update}:J{row_to_update}'
        values_to_update = [[next_unlock, relics_to_next_unlock, relics_to_next_goal, relics_to_ultimate_goal]]
        print(f"8. Updating spreadsheet at range {range_to_update} with values: {values_to_update}")
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_update,
            valueInputOption='RAW',
            body={'values': values_to_update}
        ).execute()

        # 9. Create the embed with hero information, formatting each item on a new line and with a colon separator
        embed = discord.Embed(title=f"{hero_name} Information")

        # Combine all information into a single field value with manual newlines
        field_value = (
            f"**Current Level:** {current_level}\n"
            f"**Current Relics:** {current_relics}\n"
            f"**Next Unlock Level:** {next_unlock}\n"
            f"**Relics Needed for Next Unlock:** {relics_to_next_unlock}\n"
            f"**Next Goal Level:** {next_goal_level if next_goal_level is not None else 'No next goal level has been set'}\n"
            f"**Relics Needed for Next Goal:** {relics_to_next_goal}\n"
            f"**Ultimate Goal Level:** {ultimate_goal_level if ultimate_goal_level is not None else 'No ultimate goal level has been set'}\n"
            f"**Relics Needed for Ultimate Goal:** {relics_to_ultimate_goal}\n"
        )

        embed.add_field(name="\u200b", value=field_value, inline=False)  # Use a zero-width space for the field name

        await interaction.edit_original_response(content="", embed=embed)

    except ValueError as e:
        await interaction.edit_original_response(content=str(e))
    except Exception as e:
        print(f"An error occurred while processing hero information: {e}")

# Attach the autocomplete function to the calculate_relics_needed command parameter
calculate_relics_needed.autocomplete("hero_name")(autocomplete_hero_info)


@bot.tree.command(name="help", description="Display all bot commands and their descriptions")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Hela's Hero Planner Bot Commands", description="Here are the available commands:")

    for command in bot.tree.get_commands():
        embed.add_field(name=f"/{command.name}", value=command.description, inline=False)

    await interaction.response.send_message(embed=embed)

bot.run("MTI3OTgwMTc1MDY1NTg2NDgzMg.GwwLJ7.srhVj6BNTPN_odUdSUdi-ki-jJksKv7vf095K4")

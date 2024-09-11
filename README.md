# Hela's Hero Planner Bot

This Discord bot helps you track and plan your hero progression in a game (presumably). It interacts with Google Sheets to store and retrieve hero data, providing features like hero lists, hero information lookup, and tracking your own hero roster.

## Features

* `/hero_list`: Displays a list of all available heroes, organized by rarity.
* `/all_hero_statistics`: Provides a link to a spreadsheet with detailed hero statistics.
* `/hero_info <hero_name or number>`: Fetches detailed information about a specific hero.
* `/add_hero <hero_name>`: Adds a hero to your personal tracking list.
* `/my_heroes`: Shows a list of heroes you're currently tracking.
* `/remove_hero <hero_name>`: Removes a hero from your tracking list.
* `/manage_hero <hero_name> [current_level] [current_relics] [next_goal_level] [ultimate_goal_level]`: Updates the level, relics, and goal levels for a tracked hero.
* `/my_heroes_with_input_information`: Displays a paginated list of your tracked heroes with their current level, relics, and goal levels
* `/calculate_relics_needed <hero_name>`: Calculates the relics needed to reach the next unlock level, next goal level, and ultimate goal level for a tracked hero.
* `/calculate_xp_and_oaths_needed <hero_name>`: Calculates the XP and oaths needed to reach the next unlock level, next goal level, and ultimate goal level for a tracked hero
* `/help`: Lists all available commands and their descriptions

## Setup

1. **Prerequisites:**
   * Python 3.x
   * `discord.py` library
   * `google-api-python-client` library
   * A Google Cloud Project with a Service Account and enabled Google Sheets API
   * Two Google Sheets: one for master hero data, one for user-specific hero tracking

2. **Configuration:**
   * Replace placeholders in the code:
     * `SERVICE_ACCOUNT_FILE`: Path to your Service Account JSON file
     * `SPREADSHEET_ID`: ID of your main Google Sheet
     * `SPREADSHEET_ID_HERO_DATA`: ID of your hero data Google Sheet
     * `bot.run("YOUR_BOT_TOKEN")`: Replace with your actual Discord bot token

3. **Install Dependencies:**
   * `pip install discord.py google-api-python-client google-auth-httplib2 google-auth-oauthlib`

4. **Run the bot:**
   * `python your_bot_filename.py`

## Google Sheets Structure

* **Main Sheet (`SPREADSHEET_ID`)**
    * `Master Tab`: Contains the list of all heroes, their rarities, etc.
    * `User Hero Data`: Tracks which heroes each user is following, along with their progress.

* **Hero Data Sheet (`SPREADSHEET_ID_HERO_DATA`)**
    * `Hero Data General`: Contains detailed statistics for each hero, including max level.

**Note:** Make sure your Service Account has edit access to both Google Sheets.

## Contributing

Feel free to fork this repository and submit pull requests if you have any improvements or bug fixes.

## Disclaimer

This bot is provided as-is.  The author is not responsible for any issues or data loss that may occur during use.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

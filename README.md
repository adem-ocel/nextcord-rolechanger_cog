# Nextcord Role Changer Cog

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Discord Library](https://img.shields.io/badge/Library-Nextcord-7289DA.svg)](https://nextcord.readthedocs.io/en/latest/)
[![GitHub Repo](https://img.shields.io/badge/GitHub-nextcord--rolechanger__cog-2b3137.svg)](https://github.com/adem-ocel/nextcord-rolechanger_cog)

---

## 📝 Description

This repository contains an extension (**Cog**) developed with the **Nextcord** library for Discord bots.

The file **`role_changer.py`** provides commands that enable server administrators or authorized users to easily manage member roles on the server. This cog is designed to streamline the process of quickly assigning a role to a user or removing a role from them.

---

## ✨ Features

* Command to instantly add a role to a specified user.
* Command to instantly remove a role from a specified user.
* Built-in permission check to ensure commands are run only by users with the **Manage Roles** permission.
* Clear feedback messages for successful and failed operations.

---

## ⚙️ Installation

### Prerequisites

To successfully integrate and use this cog, your bot must meet the following requirements:

1.  **Python 3.8+**
2.  The **`nextcord`** library (`pip install nextcord`)
3.  The **`members`** intent must be **ENABLED** in your bot's `Intents` settings. (This is crucial for role management to function.)

### Loading the Cog into Your Bot

1.  Copy the **`role_changer.py`** file into your bot's cogs/extensions directory.
2.  Load the extension in your main bot file (e.g., `bot.py`).

**`bot.py` Example:**

This code snippet illustrates how the `role_changer` extension can be loaded:

```python
import nextcord
from nextcord.ext import commands

# Ensure the members intent is correctly set
intents = nextcord.Intents.default()
intents.members = True 
intents.message_content = True # May be required for command processing

bot = commands.Bot(command_prefix="!", intents=intents) # Use your preferred prefix.

@bot.event
async def on_ready():
    print(f'Bot logged in as: {bot.user}')
    
    # Load the extension using the cog file name (role_changer)
    try:
        bot.load_extension("role_changer") 
        print("Role Changer Cog successfully loaded.")
    except Exception as e:
        print(f"Error: Role Changer Cog could not be loaded. {e}")

# bot.run("YOUR_BOT_TOKEN")

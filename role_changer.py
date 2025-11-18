from nextcord import Permissions, slash_command, RawReactionActionEvent, Interaction, Role, Message, Embed
from nextcord.ext import commands
import nextcord
import json

_config = 'rolechanger_conf.json'

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.data = {"guilds": []}
        self._load_config()

    def _load_config(self):
        try:
            with open(_config, 'r', encoding='utf-8') as file:
                self.data = json.load(file)
            print(f'The configuration file ({_config}) was loaded successfully.')
        except FileNotFoundError:
            print(f'Configuration file ({_config}) not found. Creating new file.')
            self.data = {"guilds": []}
            self._save_config()
        except json.JSONDecodeError:
            print(f'Could not read configuration file ({_config}) (unformatted). Continuing with empty data.')
            self.data = {"guilds": []}
            self._save_config()
    
    def _save_config(self):
        try:
            with open(_config, 'w', encoding='utf-8') as file:
                json.dump(self.data, file, indent=4, ensure_ascii=False)
            print(f'The configuration file ({_config}) has been saved.')
        except Exception as e:
            print(f'Failed to save configuration file: {e}')

    def _get_guild_data(self, guild_id: int, create_if_missing: bool = False) -> dict | None:
        for guild_data in self.data.get("guilds", []):
            if guild_data.get("guild_id") == guild_id:
                return guild_data
        
        if create_if_missing:
            new_data = {"guild_id": guild_id, "messages": []}
            self.data["guilds"].append(new_data)
            self._save_config()
            return new_data
        
        return None

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        await self.change_reaction_role(payload=payload, is_add=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        await self.change_reaction_role(payload=payload, is_add=False)

    @slash_command(name='rolechanger', description='Commands for users to select a role with a message.', default_member_permissions=Permissions(administrator=True))
    async def rolechanger(self, interaction: Interaction):
        pass

    async def change_reaction_role(self, payload: RawReactionActionEvent, is_add: bool):
        if payload.user_id == self.bot.user.id or not payload.guild_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        guild_data = self._get_guild_data(guild.id)
        if not guild_data:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message: Message = await channel.fetch_message(payload.message_id)
        except nextcord.NotFound:
            print(f'No message found. Message ID: {payload.message_id}')
            return
        except Exception as e:
            print(f'Error receiving message: {e}')
            return
        
        for msg in guild_data.get("messages", []):
            if msg.get("message_id") == message.id:
                
                try:
                    user: nextcord.Member = guild.get_member(payload.user_id) or await guild.fetch_member(payload.user_id)
                except nextcord.NotFound:
                    print(f'No user found on server {guild.name}. ID: {payload.user_id}')
                    return
                
                for role_config in msg.get("roles", []):
                    emoji_match = str(payload.emoji) == role_config.get("emote")
                    
                    if emoji_match:
                        role_id = role_config.get("role")
                        role: Role = guild.get_role(role_id)

                        if not role:
                            print(f'No role found on server {guild.name}. Role ID: {role_id}')
                            continue
                        
                        action_name = "added" if is_add else "removed"
                        try:
                            if is_add:
                                if role not in user.roles:
                                    await user.add_roles(role)
                                    action_log = f"{role.name} role ADDED."
                                else:
                                    action_log = f"The role {role.name} ALREADY EXISTED."
                            else:
                                if role in user.roles:
                                    await user.remove_roles(role)
                                    action_log = f"The {role.name} role has been REMOVED."
                                else:
                                    action_log = f"The {role.name} role did not already exist."
                            
                            print(
                                f"[{guild.name}] {user.name} with {payload.emoji.name}{action_log}"
                            )
                        except nextcord.Forbidden:
                            print(f"[{guild.name}] Authorization error for {action_name} to {user.name} for role {role.name}.")
                        except Exception as e:
                            print(f"Error during role {action_name}: {e}")
                
                return 

    @rolechanger.subcommand(name="create_message", description="It allows the bot to send a reaction message where it can add or remove roles with a reaction.")
    async def create_message(self, interaction: Interaction, title: str = "Find the one that suits you.", description: str = "Click on the relevant emoji to add/remove the role you want on the server."):
        await interaction.response.defer(ephemeral=True) 

        guild_data = self._get_guild_data(interaction.guild.id, create_if_missing=True)
        if not guild_data:
            await interaction.followup.send("Failed to create server data.", ephemeral=True)
            return

        embed = Embed(
            color=nextcord.Color.blue(),
            title=title,
            description=description
        )
        try:
            message: Message = await interaction.channel.send(embed=embed)
        except nextcord.Forbidden:
            print(f'[{interaction.guild.name}] is not allowed to send messages.')
            await interaction.followup.send("ERROR: I do not have permission to send messages to this channel. Please check your permissions.", ephemeral=True)
            return

        guild_data["messages"].append({
            "message_id": message.id, 
            "channel_id": interaction.channel.id,
            "roles": []
        })
        self._save_config()

        print(f"[{interaction.guild.name}] An empty message was created for role selection. ID: {message.id}, Channel ID: {interaction.channel.id}")
        await interaction.followup.send(f"✅ A role selection message has been created. Message ID: `{message.id}`. You can now add roles with the `/rolechanger add_role` command.", ephemeral=False)

    @rolechanger.subcommand('remove_message', 'Deletes a previously sent election message and removes it from the configuration.')
    async def remove_message(self, interaction: Interaction, message_id: str):
        await interaction.response.defer(ephemeral=True)

        try:
            message_id_int = int(message_id)
        except ValueError:
            await interaction.followup.send("ERROR: Invalid Message ID format. Please enter a numeric ID.", ephemeral=True)
            return

        guild_data = self._get_guild_data(interaction.guild.id)
        if not guild_data:
            await interaction.followup.send("WARNING: There is no role selector data stored on this server.", ephemeral=True)
            return
        
        msg_data_to_remove = next((msg for msg in guild_data.get("messages", []) if msg.get("message_id") == message_id_int), None)
        
        if msg_data_to_remove:
            channel_id = msg_data_to_remove.get("channel_id")
            channel = self.bot.get_channel(channel_id)
            
            if channel:
                try:
                    message = await channel.fetch_message(message_id_int)
                    await message.delete()
                    print(f"The message with ID [{interaction.guild.name}] ({message_id_int}) was deleted from channel {channel.name}.")
                except nextcord.NotFound:
                    print(f"[{interaction.guild.name}] Message ({message_id_int}) did not already exist on Discord.")
                except Exception as e:
                    await interaction.followup.send(f"ERROR: There was a problem deleting the message: {e}", ephemeral=True)
                    print(f"[{interaction.guild.name}] Error deleting message ({message_id_int}): {e}")
                    return
            else:
                 print(f"[{interaction.guild.name}] The channel ({channel_id}) used to delete the message could not be found. Removing it from the configuration.")


        initial_count = len(guild_data["messages"])
        guild_data["messages"] = [
            msg for msg in guild_data["messages"] if msg.get("message_id") != message_id_int
        ]

        if len(guild_data["messages"]) < initial_count:
            self._save_config()
            await interaction.followup.send(f"✅ Role selection message (ID: `{message_id_int}`) has been successfully deleted and removed from the configuration.", ephemeral=False)
        else:
            await interaction.followup.send(f"⚠️ Warning: The message was deleted from Discord or was not found, but no entry with this ID (`{message_id_int}`) was found in the configuration.", ephemeral=False)

    @rolechanger.subcommand(name='list_messages', description='Lists all election messages previously sent.')
    async def list_messages(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild_data = self._get_guild_data(interaction.guild.id)
        if not guild_data:
            await interaction.followup.send("There are **no** servers registered.", ephemeral=True)
            return
            
        messages = guild_data.get("messages", [])

        if not messages:
            await interaction.followup.send("There are **no** role selection messages recorded on the server.", ephemeral=True)
            return

        list_content = []
        for i, msg in enumerate(messages, 1):
            message_id = msg.get("message_id")
            channel_id = msg.get("channel_id")
            role_count = len(msg.get("roles", []))
            
            message_link = f"https://discord.com/channels/{interaction.guild.id}/{channel_id}/{message_id}"
            
            channel = interaction.guild.get_channel(channel_id)
                            
            list_content.append(
                f"**{i}.** [See Message]({message_link})\n"
                f"** ↳ channel:** {channel.name} | **Role count:** {role_count}"
            )

        embed = Embed(
            color=nextcord.Color.green(),
            title=f"✅ {interaction.guild.name}Saved Role Selection Messages.",
            description="\n".join(list_content)
        )
        embed.set_footer(text=f"A total of {len(messages)} messages have been recorded.")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @rolechanger.subcommand(name="add_role", description="Adds a role to the specified selector.")
    async def add_role(self, interaction: Interaction, message_id: str, role: Role, emote: str, description: str):
        await interaction.response.defer(ephemeral=True)
        
        guild_data = self._get_guild_data(interaction.guild.id)
        if not guild_data:
            await interaction.followup.send("WARNING: There is no role selector data stored on this server. Create a message first.", ephemeral=True)
            return

        message_id_int = -1
        try:
            message_id_int = int(message_id)
        except ValueError:
             await interaction.followup.send("ERROR: Invalid Message ID format. Please enter a numeric ID.", ephemeral=True)
             return

        msg_data = next((msg for msg in guild_data["messages"] if msg.get("message_id") == message_id_int), None)
        
        if msg_data is None:
            await interaction.followup.send("WARNING: No registered role selector with this message ID was found.", ephemeral=True)
            return
        
        channel_id = msg_data.get("channel_id", interaction.channel.id) 
        channel = self.bot.get_channel(channel_id)

        if not channel:
            await interaction.followup.send("ERROR: The channel containing the message was not found or cannot be accessed.", ephemeral=True)
            return

        try:
            message: Message = await channel.fetch_message(message_id_int)
        except nextcord.NotFound:
            await interaction.followup.send("ERROR: The message with the specified ID was not found in that channel. Please check the ID.", ephemeral=True)
            return
        except nextcord.Forbidden:
            await interaction.followup.send("ERROR: I do not have permission to fetch the message. Please check the permissions.", ephemeral=True)
            return


        for r_config in msg_data["roles"]:
            if r_config.get("emote") == emote:
                await interaction.followup.send(f"ERROR: The emoji **{emote}** is already assigned to a role in this selector.", ephemeral=True)
                return
            if r_config.get("role") == role.id:
                await interaction.followup.send(f"ERROR: The role **{role.name}** is already registered in this selector.", ephemeral=True)
                return
        
        if interaction.guild.me.top_role.position <= role.position:
            await interaction.followup.send("ERROR: The bot's role is not high enough to assign this role. Move the bot's role above this role.", ephemeral=True)
            return

        try:
            embed = message.embeds[0].copy()
            embed.add_field(
                name=f"{emote} {role.name} :",
                value=description,
                inline=False
            )
            
            await message.edit(embed=embed)
            await message.add_reaction(emoji=emote)

            new_role_config = {
                "role": role.id,
                "emote": emote,
                "description": description
            }
            msg_data["roles"].append(new_role_config)
            self._save_config()

            print(f"The role ({emote} {role.name}) has been added to the message with ID [{interaction.guild.name}] ({message_id}).")
            await interaction.followup.send(f"✅ Successfully added **{emote}** emoji and (**{role.name}**) role to the role selection message.", ephemeral=False)

        except nextcord.Forbidden:
            print(f'[{interaction.guild.name}] Does not have permission to edit message/add emoji.')
            await interaction.followup.send("ERROR: I don't have permission to edit the message or add emojis. Please check permissions.", ephemeral=True)
        except Exception as e:
            print(f"A general error occurred while adding a role to a message: {e}")
            await interaction.followup.send(f"ERROR: An unexpected problem occurred: {e}", ephemeral=True)

    @rolechanger.subcommand(name="remove_role", description="Removes a role from the specified selector.")
    async def remove_role(self, interaction: Interaction, message_id: str, emote: str):
        await interaction.response.defer(ephemeral=True)

        guild_data = self._get_guild_data(interaction.guild.id)
        if not guild_data:
            await interaction.followup.send("WARNING: There is no role selector data stored on this server.", ephemeral=True)
            return

        message_id_int = -1
        try:
            message_id_int = int(message_id)
        except ValueError:
            await interaction.followup.send("ERROR: Invalid Message ID format. Please enter a numeric ID.", ephemeral=True)
            return

        msg_data = next((msg for msg in guild_data["messages"] if msg.get("message_id") == message_id_int), None)

        if msg_data is None:
            await interaction.followup.send("WARNING: No registered role selector with this message ID was found.", ephemeral=True)
            return
        
        channel_id = msg_data.get("channel_id", interaction.channel.id)
        channel = self.bot.get_channel(channel_id)

        if not channel:
            await interaction.followup.send("ERROR: The channel containing the message was not found or cannot be accessed.", ephemeral=True)
            return

        try:
            message: Message = await channel.fetch_message(message_id_int)
        except nextcord.NotFound:
            await interaction.followup.send("ERROR: The message with the specified ID was not found in that channel.", ephemeral=True)
            return
        except nextcord.Forbidden:
            await interaction.followup.send("ERROR: I do not have permission to fetch the message.", ephemeral=True)
            return
        
        
        role_config_index_to_remove = -1
        removed_role_name = ""
        
        for k, role_config in enumerate(msg_data["roles"]):
            if role_config.get("emote") == emote:
                role_config_index_to_remove = k
                removed_role = interaction.guild.get_role(role_config.get("role"))
                removed_role_name = removed_role.name if removed_role else "Unknown Role"
                break
        
        if role_config_index_to_remove != -1:
            
            msg_data["roles"].pop(role_config_index_to_remove)
            self._save_config()
            
            if message.embeds:
                embed = message.embeds[0].copy()
                field_index_to_remove = -1
                for j, field in enumerate(embed.fields):
                    if field.name.startswith(emote):
                        field_index_to_remove = j
                        break
                
                if field_index_to_remove != -1:
                    try:
                        embed.remove_field(field_index_to_remove)
                        await message.edit(embed=embed)
                    except nextcord.Forbidden:
                        print(f'[{interaction.guild.name}] No permission to edit the message.')
                        await interaction.followup.send("ERROR: I don't have permission to edit the message. The role was removed from the configuration, but the message could not be updated.", ephemeral=True)
                    except Exception as e:
                        print(f"Error while editing message: {e}")
                        await interaction.followup.send("WARNING: The role was removed from the configuration, but an error occurred while updating the message.", ephemeral=True)

            try:
                await message.clear_reaction(emoji=emote)
            except nextcord.NotFound:
                pass
            except nextcord.Forbidden:
                print(f"[{interaction.guild.name}] No permission to delete reaction.")
            except Exception as e:
                print(f"Error removing response: {e}")

            print(f"The role {emote} ({removed_role_name}) was removed from the message with ID [{interaction.guild.name}] ({message_id}).")
            await interaction.followup.send(f"✅ Successfully removed the role **{emote}** ({removed_role_name}) from the role selector message.", ephemeral=False)

        else:
            await interaction.followup.send(f"ERROR: No role matching emoji **{emote}** found in configuration.", ephemeral=True)

def setup(bot):
    bot.add_cog(ReactionRoles(bot))
    print('The rolechanger module is loaded.')
import discord
from discord.ui import Button, View
import requests

# === CONFIG ===
BOT_TOKEN = "your_discord_bot_token_here"
JELLYFIN_API_KEY = "your_jellyfin_api_key_here"
JELLYFIN_URL = "your_jellyfin_url_here(dont_forget_the_http/s)"
APPROVAL_CHANNEL_ID = 123456789012345678  # Replace with your private channel ID

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# === VIEW FOR APPROVAL BUTTONS ===
class ApprovalView(View):
    def __init__(self, requester, username, password):
        super().__init__(timeout=None)
        self.requester = requester
        self.username = username
        self.password = password

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: Button):
        if not (interaction.user.guild_permissions.administrator or interaction.user == interaction.guild.owner):
            await interaction.response.send_message("❌ You don't have permission to approve.", ephemeral=True)
            return

        await interaction.response.defer()  # Acknowledge the button press

        try:
            headers = {
                "X-Emby-Token": JELLYFIN_API_KEY,
                "Content-Type": "application/json"
            }

            # Create user
            create_resp = requests.post(
                f"{JELLYFIN_URL}/Users/New",
                headers=headers,
                json={"Name": self.username}
            )
            create_resp.raise_for_status()
            user_id = create_resp.json().get("Id")

            if not user_id:
                raise Exception("User ID not found in Jellyfin response.")

            # Set password using proper format
            pw_resp = requests.post(
                f"{JELLYFIN_URL}/Users/{user_id}/Password",
                headers=headers,
                json={
                    "NewPw": self.password,
                    "ResetPassword": False
                }
            )
            pw_resp.raise_for_status()

            await interaction.edit_original_response(content=f"✅ Approved and created user `{self.username}`.", view=None)

            try:
                await self.requester.send(f"✅ Your Jellyfin account `{self.username}` has been created and is ready to use!")
            except:
                pass

        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Error creating user:\n```{str(e)}```", view=None)
            try:
                await self.requester.send("❌ There was an error creating your Jellyfin account. Please contact the admin.")
            except:
                pass

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: Button):
        if not (interaction.user.guild_permissions.administrator or interaction.user == interaction.guild.owner):
            await interaction.response.send_message("❌ You don't have permission to deny.", ephemeral=True)
            return

        await interaction.response.defer()
        await interaction.edit_original_response(content=f"❌ Denied account creation for `{self.username}`.", view=None)

        try:
            await self.requester.send(f"❌ Your request for Jellyfin username `{self.username}` was denied.")
        except:
            pass

# === EVENTS ===
@client.event
async def on_ready():
    print(f"✅ Bot is online as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.startswith("!requestaccount"):
        parts = message.content.split()
        if len(parts) != 3:
            await message.channel.send("❌ Usage: `!requestaccount <username> <password>`")
            return

        username, password = parts[1], parts[2]

        approval_channel = client.get_channel(APPROVAL_CHANNEL_ID)
        if not approval_channel:
            await message.channel.send("❌ Couldn't find the approval channel.")
            return

        await message.channel.send(f"⏳ Your request for `{username}` is waiting for approval.")

        view = ApprovalView(requester=message.author, username=username, password=password)

        await approval_channel.send(
            content=f"📥 New Jellyfin account request from {message.author.mention}\n**Username:** `{username}`\n**Password:** `{password}`",
            view=view
        )

# === RUN ===
client.run(BOT_TOKEN)

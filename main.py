import discord
import os
from dotenv import load_dotenv

load_dotenv()

bot = discord.Bot(debug_guilds=[1463713376210391103])
os.system('cls' if os.name == 'nt' else 'clear')

@bot.event
async def on_ready():
    print(f"\n✅ {bot.user} está online!")

cogs_list = [
    'cogs.aulas',
    'cogs.cadastro',
    'cogs.biblioteca',
    'cogs.economia',
    'cogs.cronograma',
    'cogs.loja',
    'cogs.config_comandos'
]
for cog in cogs_list:
    try:
        bot.load_extension(cog)
        print(f"📦 {cog} carregado com sucesso!")
    except Exception as e:
        print(f"❌ Falha ao carregar {cog}: {e}")

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
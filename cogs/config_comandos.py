import discord
from discord.ext import commands
import aiosqlite

async def autocomplete_comandos(ctx: discord.AutocompleteContext):
    comandos_lista = [cmd.name for cmd in ctx.bot.application_commands if isinstance(cmd, discord.SlashCommand)]
    return [cmd for cmd in comandos_lista if ctx.value.lower() in cmd.lower()]

class ConfigComandos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_check(self.verificacao_global)

    def cog_unload(self):
        self.bot.remove_check(self.verificacao_global)

    @commands.Cog.listener()
    async def on_ready(self):
        async with aiosqlite.connect('escola.db') as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS config_comandos (
                    comando TEXT,
                    tipo TEXT, 
                    alvo_id INTEGER,
                    UNIQUE(comando, tipo, alvo_id)
                )
            ''')
            await db.commit()

    async def verificacao_global(self, ctx: discord.ApplicationContext):
        if ctx.author.guild_permissions.administrator:
            return True
            
        comando_atual = ctx.command.name
        
        async with aiosqlite.connect('escola.db') as db:
            async with db.execute('SELECT alvo_id FROM config_comandos WHERE comando = ? AND tipo = "canal"', (comando_atual,)) as cursor:
                canais_permitidos = [row[0] async for row in cursor]
            
            async with db.execute('SELECT alvo_id FROM config_comandos WHERE comando = ? AND tipo = "cargo"', (comando_atual,)) as cursor:
                cargos_permitidos = [row[0] async for row in cursor]
        
        if not canais_permitidos and not cargos_permitidos:
            return True
            
        if canais_permitidos and ctx.channel.id not in canais_permitidos:
            raise commands.CheckFailure("Este comando não pode ser usado neste canal.")
            
        if cargos_permitidos:
            user_roles = [role.id for role in ctx.author.roles]
            if not any(cargo_id in user_roles for cargo_id in cargos_permitidos):
                raise commands.CheckFailure("Você não possui o cargo necessário para usar este comando.")
                
        return True

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx: discord.ApplicationContext, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.respond(f"🚫 **Acesso negado:** {error}", ephemeral=True)

    @discord.slash_command(name="config_comando", description="[ADM] Restringe o uso de um comando a canais ou cargos específicos")
    @commands.has_permissions(administrator=True)
    async def config_comando(
        self, ctx,
        comando: str = discord.Option(str, description="Selecione o comando", autocomplete=autocomplete_comandos),
        acao: str = discord.Option(str, choices=["Adicionar", "Remover", "Limpar Tudo"], description="O que deseja fazer com a restrição?"),
        canal: discord.abc.GuildChannel = discord.Option(discord.abc.GuildChannel, description="Canal alvo (opcional)", required=False, default=None),
        cargo: discord.Role = discord.Option(discord.Role, description="Cargo alvo (opcional)", required=False, default=None)
    ):
        if acao != "Limpar Tudo" and not canal and not cargo:
            return await ctx.respond("❌ Você precisa selecionar pelo menos um **Canal** ou um **Cargo** para adicionar/remover.", ephemeral=True)

        async with aiosqlite.connect('escola.db') as db:
            if acao == "Adicionar":
                if canal:
                    await db.execute('INSERT OR IGNORE INTO config_comandos (comando, tipo, alvo_id) VALUES (?, ?, ?)', (comando, 'canal', canal.id))
                if cargo:
                    await db.execute('INSERT OR IGNORE INTO config_comandos (comando, tipo, alvo_id) VALUES (?, ?, ?)', (comando, 'cargo', cargo.id))
                await db.commit()
                await ctx.respond(f"✅ Regras **adicionadas** com sucesso para o comando `/{comando}`.", ephemeral=True)

            elif acao == "Remover":
                if canal:
                    await db.execute('DELETE FROM config_comandos WHERE comando = ? AND tipo = ? AND alvo_id = ?', (comando, 'canal', canal.id))
                if cargo:
                    await db.execute('DELETE FROM config_comandos WHERE comando = ? AND tipo = ? AND alvo_id = ?', (comando, 'cargo', cargo.id))
                await db.commit()
                await ctx.respond(f"🗑️ Regras específicas **removidas** do comando `/{comando}`.", ephemeral=True)
                
            elif acao == "Limpar Tudo":
                await db.execute('DELETE FROM config_comandos WHERE comando = ?', (comando,))
                await db.commit()
                await ctx.respond(f"🧹 Todas as restrições do comando `/{comando}` foram removidas. Ele voltou a ser público.", ephemeral=True)

def setup(bot):
    bot.add_cog(ConfigComandos(bot))
import discord
from discord.ext import commands
import aiosqlite

class Biblioteca(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @discord.slash_command(name="criar_origem", description="[ADM] Adiciona uma nova origem ao sistema")
    @commands.has_permissions(administrator=True)
    async def criar_origem(
        self, ctx, 
        nome: str = discord.Option(str, description="Nome da origem"),
        categoria: str = discord.Option(str, choices=["Humanídio", "Sombrio"]), 
        atributo_bonus: str = discord.Option(str, choices=["corpo", "mente", "coracao"]), 
        descricao: str = discord.Option(str, description="Descrição detalhada da origem")
    ):
        try:
            async with aiosqlite.connect('escola.db') as db:
                await db.execute('INSERT INTO origens (nome, descricao, categoria, atributo_bonus) VALUES (?, ?, ?, ?)', (nome, descricao, categoria, atributo_bonus))
                await db.commit()
            await ctx.respond(f"👤 Origem **{nome}** criada! Bônus: +3 em {atributo_bonus.capitalize()}.")
        except aiosqlite.IntegrityError:
            await ctx.respond(f"❌ A origem **{nome}** já existe!", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ Erro ao criar origem: {e}", ephemeral=True)

    @discord.slash_command(name="ver_origens", description="Lista todas as origens cadastradas")
    async def ver_origens(
        self, ctx,
        nome: str = discord.Option(str, description="Nome específico da origem (opcional)", default=None)
    ):
        async with aiosqlite.connect('escola.db') as db:
            if nome:
                async with db.execute('SELECT nome, descricao, categoria, atributo_bonus FROM origens WHERE nome = ?', (nome,)) as cursor:
                    origem = await cursor.fetchone()
                
                if not origem:
                    return await ctx.respond(f"❌ Origem **{nome}** não encontrada.", ephemeral=True)
                    
                embed = discord.Embed(title=f"👤 Origem: {origem[0]}", description=f"**Descrição:**\n> {origem[1]}", color=discord.Color.dark_purple())
                embed.add_field(name="Categoria", value=f"`{origem[2]}`", inline=True)
                embed.add_field(name="Bônus", value=f"`+3 em {origem[3].capitalize()}`", inline=True)
                await ctx.respond(embed=embed, ephemeral=True)
            else:
                async with db.execute('SELECT nome, categoria, atributo_bonus FROM origens') as cursor:
                    origens = await cursor.fetchall()
                
                if not origens:
                    return await ctx.respond("❌ Nenhuma origem cadastrada.", ephemeral=True)
                    
                lista = "\n".join([f"• **{o[0]}** ({o[1]}) | Bônus: +3 em {o[2].capitalize()}." for o in origens])
                embed = discord.Embed(title="👤 Origens Disponíveis", description=lista, color=discord.Color.dark_purple())
                await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="editar_origem", description="[ADM] Edita os dados de uma origem existente")
    @commands.has_permissions(administrator=True)
    async def editar_origem(
        self, ctx,
        nome: str = discord.Option(str, description="Nome atual da origem"),
        nome_novo: str = discord.Option(str, description="Novo nome (opcional)", default=None),
        categoria: str = discord.Option(str, choices=["Humanídio", "Sombrio"], description="Nova categoria (opcional)", default=None),
        atributo_bonus: str = discord.Option(str, choices=["corpo", "mente", "coracao"], description="Novo atributo bônus (opcional)", default=None),
        descricao: str = discord.Option(str, description="Nova descrição (opcional)", default=None)
    ):
        async with aiosqlite.connect('escola.db') as db:
            async with db.execute('SELECT nome, descricao, categoria, atributo_bonus FROM origens WHERE nome = ?', (nome,)) as cursor:
                res = await cursor.fetchone()
            
            if not res:
                return await ctx.respond("❌ Origem não encontrada.", ephemeral=True)

            alteracoes = []

            n_nome = res[0]
            if nome_novo and nome_novo != res[0]:
                alteracoes.append(f"▫️ **Nome:** `{res[0]}` ➔ `{nome_novo}`")
                n_nome = nome_novo
                
            n_desc = res[1]
            if descricao and descricao != res[1]:
                alteracoes.append("▫️ **Descrição:** `[Atualizada]`")
                n_desc = descricao
                
            n_cat = res[2]
            if categoria and categoria != res[2]:
                alteracoes.append(f"▫️ **Categoria:** `{res[2]}` ➔ `{categoria}`")
                n_cat = categoria

            n_attr = res[3]
            if atributo_bonus and atributo_bonus != res[3]:
                alteracoes.append(f"▫️ **Bônus:** `{res[3]}` ➔ `{atributo_bonus}`")
                n_attr = atributo_bonus

            if not alteracoes:
                return await ctx.respond("❌ Nenhuma alteração foi fornecida ou os dados já são iguais.", ephemeral=True)

            await db.execute('UPDATE origens SET nome = ?, descricao = ?, categoria = ?, atributo_bonus = ? WHERE nome = ?', 
                               (n_nome, n_desc, n_cat, n_attr, nome))
            await db.commit()
        
        texto_alteracoes = "\n".join(alteracoes)
        await ctx.respond(f"✏️ Origem '{nome}' atualizada!\n\n{texto_alteracoes}")
    @discord.slash_command(name="deletar_origem", description="[ADM] Remove uma origem do sistema")
    @commands.has_permissions(administrator=True)
    async def deletar_origem(self, ctx, nome: str):
        async with aiosqlite.connect('escola.db') as db:
            await db.execute('DELETE FROM origens WHERE nome = ?', (nome,))
            await db.commit()
        await ctx.respond(f"🗑️ Origem **{nome}** foi removida.")



    @discord.slash_command(name="criar_aptidao", description="[ADM] Adiciona uma aptidão à biblioteca")
    @commands.has_permissions(administrator=True)
    async def criar_aptidao(self, ctx, nome: str, custo: int, descricao: str):
        try:
            async with aiosqlite.connect('escola.db') as db:
                await db.execute('INSERT INTO biblioteca (nome, descricao, tipo, custo) VALUES (?, ?, ?, ?)',
                                   (nome, descricao, 'Aptidão', custo))
                await db.commit()
            await ctx.respond(f"📚 Aptidão **{nome}** adicionada à biblioteca (Custo: {custo}⭐)", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ Erro: {e}")
    
    @discord.slash_command(name="ver_aptidoes", description="Lista todas as aptidões da biblioteca")
    async def ver_aptidoes(
        self, ctx,
        nome: str = discord.Option(str, description="Nome específico da aptidão (opcional)", default=None)
    ):
        async with aiosqlite.connect('escola.db') as db:
            if nome:
                async with db.execute("SELECT nome, descricao, custo FROM biblioteca WHERE nome = ? AND tipo = 'Aptidão'", (nome,)) as cursor:
                    aptidao = await cursor.fetchone()
                
                if not aptidao:
                    return await ctx.respond(f"❌ Aptidão **{nome}** não encontrada.", ephemeral=True)
                    
                embed = discord.Embed(title=f"Aptidão: {aptidao[0]}", description=f"**Descrição:**\n> {aptidao[1]}", color=discord.Color.green())
                embed.add_field(name="Custo", value=f"`{aptidao[2]}⭐`", inline=True)
                await ctx.respond(embed=embed, ephemeral=True)
                
            else:
                async with db.execute("SELECT nome, custo FROM biblioteca WHERE tipo = 'Aptidão'") as cursor:
                    aptidoes = await cursor.fetchall()
                
                if not aptidoes:
                    return await ctx.respond("Nenhuma aptidão cadastrada.", ephemeral=True)
                    
                lista = "\n".join([f"**{a[0]}** | Custo: {a[1]}⭐" for a in aptidoes])
                embed = discord.Embed(title="📚 Biblioteca de Aptidões", description=lista, color=discord.Color.green())
                await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="editar_aptidao", description="[ADM] Edita os dados de uma aptidão")
    @commands.has_permissions(administrator=True)
    async def editar_aptidao(
        self, ctx,
        nome: str = discord.Option(str, description="Nome atual da aptidão"),
        nome_novo: str = discord.Option(str, description="Novo nome (opcional)", default=None),
        custo: int = discord.Option(int, description="Novo custo (opcional)", default=None),
        descricao: str = discord.Option(str, description="Nova descrição (opcional)", default=None)
    ):
        async with aiosqlite.connect('escola.db') as db:
            async with db.execute("SELECT nome, descricao, custo FROM biblioteca WHERE nome = ? AND tipo = 'Aptidão'", (nome,)) as cursor:
                res = await cursor.fetchone()
            
            if not res:
                return await ctx.respond("❌ Aptidão não encontrada.", ephemeral=True)

            alteracoes = []

            n_nome = res[0]
            if nome_novo and nome_novo != res[0]:
                alteracoes.append(f"▫️ **Nome:** `{res[0]}` ➔ `{nome_novo}`")
                n_nome = nome_novo
                
            n_desc = res[1]
            if descricao and descricao != res[1]:
                alteracoes.append("▫️ **Descrição:** `[Atualizada]`")
                n_desc = descricao
                
            n_custo = res[2]
            if custo is not None and custo != res[2]:
                alteracoes.append(f"▫️ **Custo:** `{res[2]}⭐` ➔ `{custo}⭐`")
                n_custo = custo

            if not alteracoes:
                return await ctx.respond("❌ Nenhuma alteração foi fornecida ou os dados já são iguais.", ephemeral=True)

            await db.execute("UPDATE biblioteca SET nome = ?, descricao = ?, custo = ? WHERE nome = ? AND tipo = 'Aptidão'", 
                               (n_nome, n_desc, n_custo, nome))
            await db.commit()
        
        texto_alteracoes = "\n".join(alteracoes)
        await ctx.respond(f"✏️ Aptidão '{nome}' atualizada!\n\n{texto_alteracoes}")

    @discord.slash_command(name="deletar_aptidao", description="[ADM] Remove uma aptidão da biblioteca")
    @commands.has_permissions(administrator=True)
    async def deletar_aptidao(self, ctx, nome: str = discord.Option(str, description="Nome da aptidão")):
        async with aiosqlite.connect('escola.db') as db:
            async with db.execute("SELECT id FROM biblioteca WHERE nome = ? AND tipo = 'Aptidão'", (nome,)) as cursor:
                res = await cursor.fetchone()
            
            if not res:
                return await ctx.respond("❌ Aptidão não encontrada.", ephemeral=True)

            await db.execute('DELETE FROM posses WHERE conhecimento_id = ?', (res[0],))
            await db.execute('DELETE FROM biblioteca WHERE id = ?', (res[0],))
            await db.commit()
            
        await ctx.respond(f"🗑️ Aptidão **{nome}** removida da biblioteca e das fichas dos alunos.")



def setup(bot):
    bot.add_cog(Biblioteca(bot))
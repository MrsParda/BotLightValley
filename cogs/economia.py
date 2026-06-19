import discord
from discord.ext import commands
import aiosqlite

class Economia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @discord.slash_command(name="adquirir", description="[EM CONSTRUÇÂO] Compra uma habilidade/aptidão da biblioteca")
    async def adquirir_conhecimento(self, ctx, id_ficha: int, nome_conhecimento: str):
        async with aiosqlite.connect('escola.db') as db:
            async with db.execute('SELECT nome_personagem, estrelas, owner_id FROM alunos WHERE id = ?', (id_ficha,)) as cursor:
                aluno = await cursor.fetchone()

            if not aluno:
                return await ctx.respond("❌ Ficha não encontrada.", ephemeral=True)
            
            nome_char, estrelas_atuais, owner_id = aluno

            if ctx.author.id != owner_id and not ctx.author.guild_permissions.administrator:
                return await ctx.respond("❌ Você não pode comprar itens para um personagem que não é seu!", ephemeral=True)

            async with db.execute('SELECT id, custo, tipo FROM biblioteca WHERE nome = ?', (nome_conhecimento,)) as cursor:
                item = await cursor.fetchone()

            if not item:
                return await ctx.respond(f"❌ '{nome_conhecimento}' não existe na biblioteca.", ephemeral=True)
            
            item_id, custo, tipo = item

            async with db.execute('SELECT 1 FROM posses WHERE aluno_id = ? AND conhecimento_id = ?', (id_ficha, item_id)) as cursor:
                if await cursor.fetchone():
                    return await ctx.respond(f"❌ **{nome_char}** já possui esta {tipo}!", ephemeral=True)

            if estrelas_atuais < custo:
                return await ctx.respond(f"❌ Estrelas insuficientes! (Possui: {estrelas_atuais} | Custo: {custo})", ephemeral=True)

            try:
                nova_estrelas = estrelas_atuais - custo
                await db.execute('UPDATE alunos SET estrelas = ? WHERE id = ?', (nova_estrelas, id_ficha))
                await db.execute('INSERT INTO posses (aluno_id, conhecimento_id) VALUES (?, ?)', (id_ficha, item_id))
                
                await db.commit()
                await ctx.respond(f"✨ **{nome_char}** adquiriu **{nome_conhecimento}**! (-{custo}⭐)")
            except Exception as e:
                await ctx.respond(f"❌ Erro na transação: {e}", ephemeral=True)

    @discord.slash_command(name="dar_estrelas", description="[ADM] Dar estrelas para algum personagem")
    @commands.has_permissions(administrator=True)
    async def dar_estrelas(self, ctx, id_ficha: int, quantidade: int):
        async with aiosqlite.connect('escola.db') as db:
            async with db.execute('SELECT nome_personagem, estrelas, owner_id FROM alunos WHERE id = ?', (id_ficha,)) as cursor:
                aluno = await cursor.fetchone()

            if not aluno:
                return await ctx.respond(f"❌ Nenhuma ficha encontrada com o ID `#{id_ficha}`.", ephemeral=True)

            nome_char, estrelas_atuais, owner_id = aluno
            novas_estrelas = estrelas_atuais + quantidade

            try:
                await db.execute('UPDATE alunos SET estrelas = ? WHERE id = ?', (novas_estrelas, id_ficha))
                await db.commit()
                
                mencao = f"<@{owner_id}>"
                
                if quantidade > 0:
                    mensagem = f"🌟 **RECOMPENSA!** O personagem **{nome_char}** recebeu **{quantidade}⭐**!\n{mencao}, ele agora possui **{novas_estrelas}⭐**."
                else:
                    mensagem = f"📉 **ATUALIZAÇÃO:** Foram removidas **{abs(quantidade)}⭐** de **{nome_char}**.\n{mencao}, saldo atual: **{novas_estrelas}⭐**."

                await ctx.respond(mensagem)
            except Exception as e:
                await ctx.respond(f"❌ Erro ao atualizar o banco de dados: {e}", ephemeral=True)

def setup(bot):
    bot.add_cog(Economia(bot))
import discord
from discord.ext import commands, tasks
import aiosqlite
import datetime

DIAS_SEMANA = {
    "Segunda-feira": 0, 
    "Terça-feira": 1, 
    "Quarta-feira": 2, 
    "Quinta-feira": 3, 
    "Sexta-feira": 4
}
NOME_DIAS = {v: k for k, v in DIAS_SEMANA.items()}

class Cronograma(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.checar_aulas.start()
    
    def cog_unload(self):
        self.checar_aulas.cancel()
    
    @commands.Cog.listener()
    async def on_ready(self):
        async with aiosqlite.connect('escola.db') as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS cronograma (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    materia_id INTEGER,
                    dia_semana INTEGER,
                    hora INTEGER,
                    minuto INTEGER,
                    FOREIGN KEY(materia_id) REFERENCES materias(id)
                )
            ''')
            await db.commit()

    @tasks.loop(minutes=1)
    async def checar_aulas(self):
        agora = datetime.datetime.now()
        dia_atual = agora.weekday()
        hora_atual = agora.hour
        minuto_atual = agora.minute

        if dia_atual > 4: 
            return

        async with aiosqlite.connect('escola.db') as db:
            async with db.execute('''
                SELECT c.id, m.id, m.nome, m.canal_id, m.professor
                FROM cronograma c
                JOIN materias m ON c.materia_id = m.id
                WHERE c.dia_semana = ? AND c.hora = ? AND c.minuto = ?
            ''', (dia_atual, hora_atual, minuto_atual)) as cursor:
                aulas_agora = await cursor.fetchall()

            for aula in aulas_agora:
                c_id, m_id, m_nome, canal_id, prof_bd = aula
                
                if not canal_id: 
                    continue

                canal = self.bot.get_channel(canal_id)
                if not canal: 
                    continue

                async with db.execute('SELECT nome FROM topicos WHERE materia_id = ? ORDER BY RANDOM() LIMIT 3', (m_id,)) as cursor_topicos:
                    topicos = await cursor_topicos.fetchall()
                
                if topicos:
                    txt_topicos = "\n".join([f"▫️ **{t[0]}**" for t in topicos])
                else:
                    txt_topicos = "- (Nenhum tópico cadastrado nesta matéria)."
                
                prof_nome = prof_bd

                mensagem = (
                    f"# Aula de {m_nome}:\n"
                    f"⚜️ O(a) Professor(a) {prof_nome} chega à sala de aula. ⚜️\n\n"
                    f"**Conteúdos**\n"
                    f"{txt_topicos}"
                )
                await canal.send(mensagem)
        
    @checar_aulas.before_loop
    async def before_checar_aulas(self):
        await self.bot.wait_until_ready()
    

    @discord.slash_command(name="criar_horario", description="[ADM] Adiciona uma aula ao cronograma da semana")
    @commands.has_permissions(administrator=True)
    async def adicionar_horario(
        self, 
        ctx, 
        materia: str = discord.Option(str, description="Nome da matéria (ex: Matemática)"),
        dia: str = discord.Option(str, choices=list(DIAS_SEMANA.keys())),
        hora: int = discord.Option(int, description="Hora (0 a 23)", min_value=0, max_value=23),
        minuto: int = discord.Option(int, description="Minuto (0 a 59)", min_value=0, max_value=59)
    ):
        async with aiosqlite.connect('escola.db') as db:
            async with db.execute('SELECT id FROM materias WHERE nome = ?', (materia,)) as cursor:
                resultado = await cursor.fetchone()
            
            if not resultado:
                return await ctx.respond(f"❌ Matéria '{materia}' não encontrada.", ephemeral=True)
                
            materia_id = resultado[0]
            dia_int = DIAS_SEMANA[dia]

            await db.execute(
                'INSERT INTO cronograma (materia_id, dia_semana, hora, minuto) VALUES (?, ?, ?, ?)', 
                (materia_id, dia_int, hora, minuto)
            )
            await db.commit()
        
        horario_formatado = f"{hora:02d}:{minuto:02d}"
        await ctx.respond(f"⏰ Horário adicionado!\nMatéria: **{materia}**\nDia: **{dia}** às **{horario_formatado}**.")

    @discord.slash_command(name="deletar_horario", description="[ADM] Remove um horário do cronograma pelo ID")
    @commands.has_permissions(administrator=True)
    async def deletar_horario(self, ctx, id_horario: int = discord.Option(int, description="ID do horário (veja no /ver_cronograma)")):
        async with aiosqlite.connect('escola.db') as db:
            async with db.execute('DELETE FROM cronograma WHERE id = ?', (id_horario,)) as cursor:
                if cursor.rowcount == 0:
                    return await ctx.respond("❌ Nenhum horário encontrado com esse ID.", ephemeral=True)
            await db.commit()
            
        await ctx.respond(f"🗑️ Horário `#{id_horario}` removido do cronograma com sucesso.")

    @discord.slash_command(name="ver_cronograma", description="[ADM] Exibe a grade de horários da escola")
    @commands.has_permissions(administrator=True)
    async def ver_cronograma(self, ctx):
        async with aiosqlite.connect('escola.db') as db:
            async with db.execute('''
                SELECT c.id, m.nome, c.dia_semana, c.hora, c.minuto 
                FROM cronograma c
                JOIN materias m ON c.materia_id = m.id
                ORDER BY c.dia_semana, c.hora, c.minuto
            ''') as cursor:
                horarios = await cursor.fetchall()
        
        if not horarios:
            return await ctx.respond("📅 O cronograma está vazio.", ephemeral=True)

        dias_separados = {i: [] for i in range(5)}
        for h in horarios:
            h_id, m_nome, dia_int, hora, minuto = h
            dias_separados[dia_int].append(f"`ID: {h_id}` | **{hora:02d}:{minuto:02d}** - {m_nome}")

        embed = discord.Embed(title="📅 Cronograma de Aulas", color=discord.Color.blurple())
        
        for dia_int in range(5):
            if dias_separados[dia_int]:
                texto = "\n".join(dias_separados[dia_int])
                embed.add_field(name=f"🗓️ {NOME_DIAS[dia_int]}", value=texto, inline=False)

        await ctx.respond(embed=embed)
    
def setup(bot):
    bot.add_cog(Cronograma(bot))
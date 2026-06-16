import discord
from discord.ext import commands
import sqlite3

async def autocomplete_todas_materias(ctx: discord.AutocompleteContext):
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute('SELECT nome FROM materias')
    res = [r[0] for r in cursor.fetchall()]
    conn.close()
    return res
async def autocomplete_materias_sala(ctx: discord.AutocompleteContext):
    canal_id = ctx.interaction.channel.id
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute('SELECT nome FROM materias WHERE canal_id = ?', (canal_id,))
    res = [r[0] for r in cursor.fetchall()]
    conn.close()
    return res
async def autocomplete_topicos(ctx: discord.AutocompleteContext):
    materia = ctx.options.get("materia")
    if not materia: 
        return []
    
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.nome FROM topicos t 
        JOIN materias m ON t.materia_id = m.id 
        WHERE m.nome = ?
    ''', (materia,))
    res = [r[0] for r in cursor.fetchall()]
    conn.close()
    return res

class Aulas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('escola.db')
        self.cursor = self.conn.cursor()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS materias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE,
                canal_id INTEGER,
                professor TEXT
            )
        ''')
        try:
            self.cursor.execute("ALTER TABLE materias ADD COLUMN professor TEXT")
        except sqlite3.OperationalError:
            pass

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS topicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                materia_id INTEGER,
                nome TEXT UNIQUE,
                FOREIGN KEY(materia_id) REFERENCES materias(id)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS boletim (
                aluno_id INTEGER,
                topico_id INTEGER,
                FOREIGN KEY(aluno_id) REFERENCES alunos(id),
                FOREIGN KEY(topico_id) REFERENCES topicos(id),
                UNIQUE(aluno_id, topico_id)
            )
        ''')
        self.conn.commit()



    @discord.slash_command(name="criar_materia", description="[ADM] Adiciona uma nova matéria à escola")
    @commands.has_permissions(administrator=True)
    async def criar_materia(
        self, ctx, 
        nome: str = discord.Option(str, description="Ex: Matemática"),
        professor: str = discord.Option(str, description="Nome do Professor"),
        canal: discord.abc.GuildChannel = discord.Option(discord.abc.GuildChannel, description="Canal ou Tópico (Thread) da aula")
    ):
        try:
            self.cursor.execute('INSERT INTO materias (nome, canal_id, professor) VALUES (?, ?, ?)', (nome, canal.id, professor))
            self.conn.commit()
            await ctx.respond(f"📘 Matéria **{nome}** criada!")
        except sqlite3.IntegrityError:
            await ctx.respond(f"❌ A matéria **{nome}** já existe!", ephemeral=True)
    
    @discord.slash_command(name="ver_materias", description="Lista todas as matérias disponíveis")
    @commands.has_permissions(administrator=True)
    async def ver_materias(self, ctx):
        self.cursor.execute('SELECT nome, canal_id FROM materias')
        materias = self.cursor.fetchall()
        
        if not materias:
            return await ctx.respond("Nenhuma matéria cadastrada ainda.", ephemeral=True)
            
        lista = "\n".join([f"• **{m[0]}** (Sala: <#{m[1]}>)" if m[1] else f"• **{m[0]}** (Sem sala definida)" for m in materias])
        embed = discord.Embed(title="📘 Grade Curricular e Salas", description=lista, color=discord.Color.blue())
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="editar_materia", description="[ADM] Altera o nome de uma matéria")
    @commands.has_permissions(administrator=True)
    async def editar_materia(
        self, ctx, 
        materia: str = discord.Option(str, description="Matéria a ser editada", autocomplete=autocomplete_todas_materias),
        nome_novo: str = discord.Option(str, description="Novo nome (opcional)", default=None),
        canal_novo: discord.abc.GuildChannel = discord.Option(discord.abc.GuildChannel, description="Novo canal ou tópico (opcional)", default=None)
    ):
        self.cursor.execute('SELECT nome, canal_id FROM materias WHERE nome = ?', (materia,))
        materia = self.cursor.fetchone()

        if not materia: 
            return await ctx.respond("❌ Matéria antiga não encontrada.", ephemeral=True)
        
        nome_final = nome_novo if nome_novo else materia[0]
        canal_final = canal_novo.id if canal_novo else materia[1]

        self.cursor.execute('UPDATE materias SET nome = ?, canal_id = ? WHERE nome = ?', (nome_final, canal_final, materia))
        self.conn.commit()
        
        mensagem = f"✏️ Matéria **{materia}** atualizada!\n"
        if nome_novo: mensagem += f"▫️ Novo nome: **{nome_novo}**\n"
        if canal_novo: mensagem += f"▫️ Novo canal: {canal_novo.mention}"
        
        await ctx.respond(mensagem if nome_novo or canal_novo else "❌ Nenhuma alteração foi fornecida.")

    @discord.slash_command(name="deletar_materia", description="[ADM] Deleta uma matéria e TODOS os seus tópicos")
    @commands.has_permissions(administrator=True)
    async def deletar_materia(
        self, ctx, 
        nome: str = discord.Option(str, description="Matéria a ser deletada", autocomplete=autocomplete_todas_materias)
    ):
        self.cursor.execute('SELECT id FROM materias WHERE nome = ?', (nome,))
        materia = self.cursor.fetchone()
        
        if not materia:
            return await ctx.respond(f"❌ Matéria **{nome}** não encontrada.", ephemeral=True)
        
        self.cursor.execute('DELETE FROM cronograma WHERE id = ?', (materia[0],))
        self.cursor.execute('DELETE FROM topicos WHERE materia_id = ?', (materia[0],))
        self.cursor.execute('DELETE FROM materias WHERE id = ?', (materia[0],))

        self.conn.commit()
        await ctx.respond(f"🗑️ Matéria **{nome}**, todos os seus tópicos e horários foram deletados.")



    @discord.slash_command(name="criar_topico", description="[ADM] Adiciona um tópico de aula a uma matéria")
    @commands.has_permissions(administrator=True)
    async def criar_topico(
        self, 
        ctx, 
        materia: str = discord.Option(str, description="Nome da matéria", autocomplete=autocomplete_todas_materias), 
        nome_topico: str = discord.Option(str, description="Nome do tópico")
    ):
        self.cursor.execute('SELECT id FROM materias WHERE nome = ?', (materia,))
        resultado = self.cursor.fetchone()
        
        if not resultado:
            return await ctx.respond(f"❌ A matéria '{materia}' não existe. Crie-a primeiro!", ephemeral=True)
            
        try:
            self.cursor.execute('INSERT INTO topicos (materia_id, nome) VALUES (?, ?)', (resultado[0], nome_topico))
            self.conn.commit()
            await ctx.respond(f"📄 Tópico **{nome_topico}** adicionado à matéria **{materia}**.")
        except sqlite3.IntegrityError:
            await ctx.respond(f"❌ O tópico **{nome_topico}** já existe!", ephemeral=True)

    @discord.slash_command(name="ver_topicos", description="[ADM] Lista os tópicos de matérias.")
    @commands.has_permissions(administrator=True)
    async def ver_topicos(
        self, ctx, 
        materia: str = discord.Option(str, description="Nome da matéria", autocomplete=autocomplete_todas_materias)
    ):
        self.cursor.execute('''
            SELECT t.nome FROM topicos t
            JOIN materias m ON t.materia_id = m.id
            WHERE m.nome = ?
        ''', (materia,))
        topicos = self.cursor.fetchall()
        
        if not topicos:
            return await ctx.respond(f"❓ Nenhum tópico encontrado para **{materia}** (ou a matéria não existe).", ephemeral=True)
            
        lista = "\n".join([f"▫️ {t[0]}" for t in topicos])
        embed = discord.Embed(title=f"📖 Tópicos de {materia}", description=lista, color=discord.Color.green())
        await ctx.respond(embed=embed, Ephemeral=True)
    
    @discord.slash_command(name="editar_topico", description="[ADM] Altera o nome de um tópico")
    @commands.has_permissions(administrator=True)
    async def editar_topico(
        self, ctx, 
        nome_antigo: str = discord.Option(str, description="Nome do tópico para editar", autocomplete=autocomplete_topicos), 
        nome_novo: str = discord.Option(str, description="Novo nome do tópico")
    ):
        self.cursor.execute('UPDATE topicos SET nome = ? WHERE nome = ?', (nome_novo, nome_antigo))
        if self.cursor.rowcount == 0:
            return await ctx.respond("❌ Tópico antigo não encontrado.", ephemeral=True)
        
        self.conn.commit()
        await ctx.respond(f"✏️ Tópico renomeada de **{nome_antigo}** para **{nome_novo}**.")
    
    @discord.slash_command(name="deletar_topico", description="[ADM] Deleta um tópico específico")
    @commands.has_permissions(administrator=True)
    async def deletar_topico(
        self, ctx, 
        nome_topico: str = discord.Option(str, description="Tópico a ser deletado", autocomplete=autocomplete_topicos)
    ):
        self.cursor.execute('DELETE FROM topicos WHERE nome = ?', (nome_topico,))
        if self.cursor.rowcount == 0:
            return await ctx.respond("❌ Tópico não encontrado.", ephemeral=True)
            
        self.conn.commit()
        await ctx.respond(f"🗑️ Tópico **{nome_topico}** deletado.")


    @discord.slash_command(name="avaliar_aluno", description="[ADM] Avalia o RP de um aluno na sala de aula atual")
    @commands.has_permissions(administrator=True)
    async def avaliar_aluno(
        self, 
        ctx, 
        id_ficha: int = discord.Option(int, description="ID da ficha do aluno (Ex: 1)"), 
        estrelas: int = discord.Option(int, description="Quantidade de estrelas recebidas"),
        materia: str = discord.Option(str, description="Selecione a matéria (Baseado nesta sala)", autocomplete=autocomplete_materias_sala),
        topico: str = discord.Option(str, description="Selecione o tópico estudado", autocomplete=autocomplete_topicos)
    ):
        self.cursor.execute('SELECT nome_personagem, estrelas, owner_id FROM alunos WHERE id = ?', (id_ficha,))
        aluno = self.cursor.fetchone()
        if not aluno:
            return await ctx.respond("❌ Ficha não encontrada.", ephemeral=True)
        
        nome_char, estrelas_atuais, owner_id = aluno

        self.cursor.execute('SELECT id, canal_id FROM materias WHERE nome = ?', (materia,))
        materia_bd = self.cursor.fetchone()
        
        if not materia_bd:
            return await ctx.respond("❌ Matéria inválida.", ephemeral=True)
            
        materia_id, canal_id = materia_bd

        if canal_id != ctx.channel.id:
            return await ctx.respond(f"❌ A matéria **{materia}** não pertence a esta sala. Avalie no canal <#{canal_id}>.", ephemeral=True)

        self.cursor.execute('SELECT id FROM topicos WHERE nome = ? AND materia_id = ?', (topico, materia_id))
        topico_bd = self.cursor.fetchone()
        if not topico_bd:
            return await ctx.respond(f"❌ O tópico '{topico}' não pertence à matéria de {materia}.", ephemeral=True)
            
        topico_id = topico_bd[0]

        novas_estrelas = estrelas_atuais + estrelas
        self.cursor.execute('UPDATE alunos SET estrelas = ? WHERE id = ?', (novas_estrelas, id_ficha))
        self.conn.commit()

        self.cursor.execute('SELECT 1 FROM boletim WHERE aluno_id = ? AND topico_id = ?', (id_ficha, topico_id))
        ja_estudou = self.cursor.fetchone()

        if ja_estudou:
            self.conn.commit()
            await ctx.respond(
                f"「 ✦ Avaliação de Matéria ✦ 」\n"
                f"O personagem **{nome_char}** foi avaliado em **{materia}** ({topico})!\n"
                f"Recebeu **⭐ {estrelas}**, mas como já dominava este assunto, seu progresso na matéria não subiu.\n\n"
                f"|| <@{owner_id}> ||"
            )  
        else:
            self.cursor.execute('INSERT INTO boletim (aluno_id, topico_id) VALUES (?, ?)', (id_ficha, topico_id))
            self.conn.commit()

            self.cursor.execute('''
                SELECT COUNT(*) FROM boletim b
                JOIN topicos t ON b.topico_id = t.id
                WHERE b.aluno_id = ? AND t.materia_id = ?
            ''', (id_ficha, materia_id))
            qtd_topicos_estudados = self.cursor.fetchone()[0]
            
            porcentagem = min(qtd_topicos_estudados * 10, 100)

            await ctx.respond(
                f"「 ✦ Avaliação de Matéria ✦ 」\n"
                f"O personagem **{nome_char}** foi avaliado em **{materia}** ({topico})!\n\n"
                f"Recebeu **⭐ {estrelas}** e absorveu mais dessa matéria!\n\n"
                f"Progresso atual em {materia}: **{porcentagem}%**\n\n"
                f"|| <@{owner_id}> ||\n"
            )


def setup(bot):
    bot.add_cog(Aulas(bot))
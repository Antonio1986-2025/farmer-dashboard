import sqlite3
from datetime import date
from config import BANCO_PATH, PASTA_DADOS

_conn = None

def conectar():
    global _conn
    if _conn is None:
        PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(BANCO_PATH, check_same_thread=False)
    return _conn

def criar_tabelas():
    with conectar() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                senha_hash TEXT NOT NULL,
                plano TEXT DEFAULT 'gratis',
                stripe_id TEXT,
                whatsapp TEXT,
                perfil TEXT DEFAULT '',
                criado_em TEXT DEFAULT (datetime('now','localtime')),
                ultimo_login TEXT
            );

            CREATE TABLE IF NOT EXISTS precos_diarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT UNIQUE,
                milho_b3 REAL,
                boi_b3 REAL,
                cbot REAL,
                dolar REAL,
                milho_cepea REAL,
                arroba_cepea REAL,
                relacao_boi_milho REAL,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS clima_diario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                regiao TEXT,
                temperatura REAL,
                chuva_mm REAL,
                umidade REAL,
                UNIQUE(data, regiao)
            );

            CREATE TABLE IF NOT EXISTS sinais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                data TEXT,
                tipo TEXT,
                ativo TEXT,
                direcao TEXT,
                confianca TEXT,
                prazo_estimado TEXT,
                explicacao TEXT,
                preco_alvo REAL,
                preco_atual REAL,
                acertou TEXT DEFAULT NULL,
                data_desfecho TEXT DEFAULT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                sinal_id INTEGER,
                ativo TEXT,
                tipo TEXT,
                preco_entrada REAL,
                preco_saida REAL,
                data_entrada TEXT,
                data_saida TEXT,
                resultado TEXT DEFAULT 'aberto',
                pnl REAL,
                dias_operacao INTEGER,
                observacao TEXT,
                quantidade REAL DEFAULT 1.0,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (sinal_id) REFERENCES sinais(id)
            );

            CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
            CREATE INDEX IF NOT EXISTS idx_precos_data ON precos_diarios(data);

            CREATE TABLE IF NOT EXISTS precos_datagro (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                estado TEXT NOT NULL,
                produto TEXT DEFAULT 'boi',
                preco REAL,
                variacao REAL,
                maxima REAL,
                minima REAL,
                nome TEXT,
                UNIQUE(data, estado, produto)
            );

            CREATE INDEX IF NOT EXISTS idx_datagro_data ON precos_datagro(data);

            CREATE TABLE IF NOT EXISTS precos_yahoo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                data TEXT NOT NULL,
                abertura REAL,
                maxima REAL,
                minima REAL,
                fechamento REAL,
                volume INTEGER DEFAULT 0,
                UNIQUE(ticker, data)
            );
        """)
        # Migração: adiciona colunas novas em tabelas existentes
        for col in [(( "sinais", "usuario_id"), "INTEGER REFERENCES usuarios(id)"),
                     (( "trades", "usuario_id"), "INTEGER REFERENCES usuarios(id)"),
                     (( "trades", "quantidade"), "REAL DEFAULT 1.0")]:
            (tabela, coluna), tipo = col
            if not conn.execute(f"PRAGMA table_info({tabela})").fetchall():
                continue
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tabela})").fetchall()]
            if coluna not in cols:
                conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
        # Índices só depois da migração (colunas já existem)
        for idx, tabela, coluna in [
            ("idx_sinais_usuario", "sinais", "usuario_id"),
            ("idx_trades_usuario", "trades", "usuario_id"),
        ]:
            try:
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {tabela}({coluna})")
            except sqlite3.OperationalError:
                pass

# ─── Usuários ───────────────────────────────────────────────

def criar_usuario(email: str, nome: str, senha_hash: str) -> int | None:
    with conectar() as conn:
        try:
            conn.execute("INSERT INTO usuarios (email, nome, senha_hash) VALUES (?, ?, ?)",
                         (email, nome, senha_hash))
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        except sqlite3.IntegrityError:
            return None

def pegar_usuario_por_email(email: str):
    with conectar() as conn:
        return conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()

def pegar_usuario_por_id(usuario_id: int):
    with conectar() as conn:
        return conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()

def atualizar_ultimo_login(usuario_id: int):
    with conectar() as conn:
        conn.execute("UPDATE usuarios SET ultimo_login = datetime('now','localtime') WHERE id = ?",
                     (usuario_id,))

def atualizar_plano(usuario_id: int, plano: str, stripe_id: str = ""):
    with conectar() as conn:
        if stripe_id:
            conn.execute("UPDATE usuarios SET plano = ?, stripe_id = ? WHERE id = ?",
                         (plano, stripe_id, usuario_id))
        else:
            conn.execute("UPDATE usuarios SET plano = ? WHERE id = ?",
                         (plano, usuario_id))

def atualizar_whatsapp(usuario_id: int, whatsapp: str):
    with conectar() as conn:
        conn.execute("UPDATE usuarios SET whatsapp = ? WHERE id = ?",
                     (whatsapp, usuario_id))


# ─── Perfil do usuário ─────────────────────────────────────

PERFIS = ["produtor", "fisico", "swinger", "daytrade", "hedger"]

PERFIL_NOMES = {
    "produtor": "🧑‍🌾 Produtor / Pecuarista",
    "fisico": "📦 Físico (Comprador/Vendedor)",
    "swinger": "📈 Swinger B3",
    "daytrade": "⚡ Day Trade",
    "hedger": "🛡️ Hedger (Indústria/Exportador)",
}

def salvar_perfil(usuario_id: int, perfil: str) -> bool:
    if perfil not in PERFIS:
        return False
    with conectar() as conn:
        # Migração segura: add coluna se não existir
        try:
            conn.execute("SELECT perfil FROM usuarios LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE usuarios ADD COLUMN perfil TEXT DEFAULT ''")
        conn.execute("UPDATE usuarios SET perfil = ? WHERE id = ?", (perfil, usuario_id))
    return True

def pegar_perfil(usuario_id: int) -> str:
    with conectar() as conn:
        try:
            row = conn.execute("SELECT perfil FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
            return row[0] if row and row[0] else ""
        except sqlite3.OperationalError:
            # Coluna perfil ainda não existe — migração
            return ""

def calcular_perfil(respostas: dict) -> str:
    """Calcula perfil baseado nas respostas do questionário."""
    pesos = {
        "produtor": 0, "fisico": 0, "swinger": 0,
        "daytrade": 0, "hedger": 0,
    }
    # Mapa de pontuação por pergunta/resposta
    mapa = {
        "q1": {"a": {"produtor": 3, "hedger": 1},
               "b": {"fisico": 3, "swinger": 1},
               "c": {"swinger": 3, "daytrade": 2},
               "d": {"daytrade": 3, "swinger": 1},
               "e": {"hedger": 3, "produtor": 1}},
        "q2": {"a": {"daytrade": 3},
               "b": {"fisico": 2, "daytrade": 2, "swinger": 1},
               "c": {"swinger": 3, "hedger": 1},
               "d": {"produtor": 3, "hedger": 3},
               "e": {"produtor": 2, "fisico": 1}},
        "q3": {"a": {"produtor": 3, "hedger": 2},
               "b": {"fisico": 2, "swinger": 2},
               "c": {"swinger": 3, "daytrade": 3},
               "d": {"hedger": 3, "swinger": 2, "daytrade": 2},
               "e": {"produtor": 2, "fisico": 1}},
        "q4": {"a": {"daytrade": 2},
               "b": {"fisico": 2, "swinger": 1},
               "c": {"swinger": 2, "hedger": 1},
               "d": {"produtor": 3, "hedger": 2},
               "e": {"fisico": 2, "swinger": 2}},
        "q5": {"a": {"produtor": 3},
               "b": {"fisico": 3},
               "c": {"swinger": 3, "daytrade": 2},
               "d": {"hedger": 2, "swinger": 1},
               "e": {"produtor": 1, "fisico": 1}},
    }
    for q, alt in respostas.items():
        if q in mapa and alt in mapa[q]:
            for perfil, pts in mapa[q][alt].items():
                pesos[perfil] = pesos.get(perfil, 0) + pts
    # Retorna o perfil com maior pontuação
    return max(pesos, key=pesos.get)

def alterar_senha(usuario_id: int, senha_hash: str):
    with conectar() as conn:
        conn.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                     (senha_hash, usuario_id))

def pegar_usuarios_com_whatsapp() -> list:
    with conectar() as conn:
        # Migração segura: add coluna perfil se não existir
        try:
            conn.execute("SELECT perfil FROM usuarios LIMIT 1")
            cols = "id, nome, whatsapp, plano, perfil"
        except sqlite3.OperationalError:
            cols = "id, nome, whatsapp, plano"
        rows = conn.execute(
            f"SELECT {cols} FROM usuarios "
            "WHERE whatsapp IS NOT NULL AND whatsapp != ''"
        ).fetchall()
        return [list(r) for r in rows]

def contar_sinais_usuario(usuario_id: int, dias: int = 30) -> int:
    with conectar() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM sinais WHERE usuario_id = ? AND data >= date('now', ?)",
            (usuario_id, f"-{dias} days")
        ).fetchone()
        return row[0] if row else 0

def listar_ativos_usuario(usuario_id: int) -> list[str]:
    with conectar() as conn:
        rows = conn.execute(
            "SELECT DISTINCT ativo FROM sinais WHERE usuario_id = ? AND ativo IS NOT NULL",
            (usuario_id,)
        ).fetchall()
        return [r[0] for r in rows if r[0]]

def contar_usuarios() -> int:
    with conectar() as conn:
        row = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()
        return row[0] if row else 0

# ─── Preços ─────────────────────────────────────────────────

def salvar_precos(milho_b3=None, boi_b3=None, cbot=None, dolar=None,
                  milho_cepea=None, arroba_cepea=None):
    with conectar() as conn:
        hoje = str(date.today())
        existente = conn.execute(
            "SELECT id FROM precos_diarios WHERE data = ?", (hoje,)
        ).fetchone()

        if milho_b3 and boi_b3 and arroba_cepea:
            relacao = round(boi_b3 / milho_b3, 2)
        elif arroba_cepea and milho_cepea:
            relacao = round(arroba_cepea / milho_cepea, 2)
        else:
            relacao = None

        if existente:
            campos = []
            valores = []
            for k, v in [("milho_b3", milho_b3), ("boi_b3", boi_b3),
                         ("cbot", cbot), ("dolar", dolar),
                         ("milho_cepea", milho_cepea),
                         ("arroba_cepea", arroba_cepea),
                         ("relacao_boi_milho", relacao)]:
                if v is not None:
                    campos.append(f"{k} = ?")
                    valores.append(v)
            if campos:
                valores.append(hoje)
                conn.execute(
                    f"UPDATE precos_diarios SET {', '.join(campos)} WHERE data = ?",
                    valores
                )
        else:
            conn.execute("""
                INSERT INTO precos_diarios
                    (data, milho_b3, boi_b3, cbot, dolar, milho_cepea, arroba_cepea, relacao_boi_milho)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (hoje, milho_b3, boi_b3, cbot, dolar, milho_cepea, arroba_cepea, relacao))

def pegar_ultimos_precos(dias=30):
    with conectar() as conn:
        return conn.execute("""
            SELECT * FROM precos_diarios
            ORDER BY data DESC LIMIT ?
        """, (dias,)).fetchall()

def pegar_ultimo_preco():
    with conectar() as conn:
        return conn.execute("""
            SELECT * FROM precos_diarios ORDER BY data DESC LIMIT 1
        """).fetchone()


# ─── DATAGRO ─────────────────────────────────────────────────

ESTADOS_BOI = ["SP", "GO", "MG", "MS", "MT", "PA", "RO", "TO", "BA"]


def salvar_precos_datagro(dados_boi: dict, produto: str = "boi"):
    if not dados_boi:
        return
    conn = conectar()
    data_ref = dados_boi.get("_data", str(date.today()))
    for estado in ESTADOS_BOI:
        d = dados_boi.get(estado)
        if not d or not d.get("preco"):
            continue
        conn.execute("""
            INSERT OR REPLACE INTO precos_datagro
                (data, estado, produto, preco, variacao, maxima, minima, nome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data_ref,
            estado,
            produto,
            d["preco"],
            d.get("variacao"),
            d.get("maxima"),
            d.get("minima"),
            d.get("nome", f"{produto.upper()} {estado}"),
        ))
    conn.commit()


def pegar_precos_datagro_hoje(produto: str = "boi") -> dict:
    with conectar() as conn:
        hoje = str(date.today())
        rows = conn.execute("""
            SELECT estado, preco, variacao, maxima, minima, nome
            FROM precos_datagro
            WHERE data = ? AND produto = ?
        """, (hoje, produto)).fetchall()
        resultado = {}
        for r in rows:
            resultado[r[0]] = {
                "preco": r[1],
                "variacao": r[2],
                "maxima": r[3],
                "minima": r[4],
                "nome": r[5],
            }
        return resultado


def pegar_serie_datagro(estado: str, dias: int = 60, produto: str = "boi") -> list[dict]:
    with conectar() as conn:
        rows = conn.execute("""
            SELECT data, preco, variacao
            FROM precos_datagro
            WHERE estado = ? AND produto = ? AND preco IS NOT NULL
            ORDER BY data ASC
            LIMIT ?
        """, (estado, produto, dias)).fetchall()
        return [
            {"data": r[0], "preco": r[1], "variacao": r[2]}
            for r in rows
        ]


def pegar_media_nacional_datagro(dias: int = 1, produto: str = "boi") -> float | None:
    with conectar() as conn:
        limite = str(date.today()) if dias == 1 else None
        if limite:
            row = conn.execute("""
                SELECT AVG(preco) FROM precos_datagro
                WHERE data = ? AND produto = ? AND preco IS NOT NULL
            """, (limite, produto)).fetchone()
        else:
            row = conn.execute("""
                SELECT AVG(preco) FROM precos_datagro
                WHERE produto = ? AND preco IS NOT NULL
            """, (produto,)).fetchone()
        return round(row[0], 2) if row and row[0] else None

# ─── Yahoo OHLCV ────────────────────────────────────────────

def salvar_preco_yahoo(ticker: str, fechamento: float,
                       abertura: float = None, maxima: float = None,
                       minima: float = None, volume: int = 0):
    from datetime import date
    conn = conectar()
    hoje = str(date.today())
    conn.execute("""
        INSERT OR REPLACE INTO precos_yahoo
            (ticker, data, abertura, maxima, minima, fechamento, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ticker, hoje, abertura, maxima, minima, fechamento, volume))

def salvar_precos_yahoo_lote(ticker: str, registros: list[dict]):
    conn = conectar()
    dados = [
        (ticker, r["data"], r.get("abertura"), r.get("maxima"),
         r.get("minima"), r.get("fechamento"), r.get("volume", 0))
        for r in registros
    ]
    conn.executemany("""
        INSERT OR REPLACE INTO precos_yahoo
            (ticker, data, abertura, maxima, minima, fechamento, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, dados)
    conn.commit()

def pegar_serie_yahoo(ticker: str, dias: int = 60) -> list[dict]:
    with conectar() as conn:
        rows = conn.execute("""
            SELECT data, abertura, maxima, minima, fechamento, volume
            FROM precos_yahoo
            WHERE ticker = ?
            ORDER BY data DESC LIMIT ?
        """, (ticker, dias)).fetchall()
        return [
            {"data": r[0], "abertura": r[1], "maxima": r[2],
             "minima": r[3], "fechamento": r[4], "volume": r[5]}
            for r in reversed(rows)
        ]

def pegar_serie_precos_diarios(dias: int = 60) -> list[dict]:
    with conectar() as conn:
        rows = conn.execute("""
            SELECT data, milho_b3, boi_b3, cbot, dolar,
                   milho_cepea, arroba_cepea, relacao_boi_milho
            FROM precos_diarios
            ORDER BY data ASC LIMIT ?
        """, (dias,)).fetchall()
        return [
            {"data": r[0], "milho_b3": r[1], "boi_b3": r[2],
             "cbot": r[3], "dolar": r[4], "milho_cepea": r[5],
             "arroba_cepea": r[6], "relacao_boi_milho": r[7]}
            for r in rows
        ]

# ─── Clima ──────────────────────────────────────────────────

def salvar_clima(regiao, temperatura, chuva_mm, umidade):
    with conectar() as conn:
        hoje = str(date.today())
        conn.execute("""
            INSERT OR REPLACE INTO clima_diario (data, regiao, temperatura, chuva_mm, umidade)
            VALUES (?, ?, ?, ?, ?)
        """, (hoje, regiao, temperatura, chuva_mm, umidade))

def pegar_clima_hoje():
    with conectar() as conn:
        hoje = str(date.today())
        return conn.execute(
            "SELECT * FROM clima_diario WHERE data = ?", (hoje,)
        ).fetchall()

# ─── Sinais ─────────────────────────────────────────────────

def salvar_sinal(tipo, ativo, direcao, confianca, prazo_estimado,
                 explicacao, preco_alvo=None, preco_atual=None,
                 usuario_id: int | None = None):
    with conectar() as conn:
        hoje = str(date.today())
        conn.execute("""
            INSERT INTO sinais
                (data, tipo, ativo, direcao, confianca, prazo_estimado,
                 explicacao, preco_alvo, preco_atual, usuario_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (hoje, tipo, ativo, direcao, confianca, prazo_estimado,
              explicacao, preco_alvo, preco_atual, usuario_id))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def pegar_sinais_hoje(usuario_id: int | None = None):
    with conectar() as conn:
        hoje = str(date.today())
        if usuario_id:
            return conn.execute(
                "SELECT * FROM sinais WHERE data = ? AND usuario_id = ? ORDER BY id",
                (hoje, usuario_id)
            ).fetchall()
        return conn.execute(
            "SELECT * FROM sinais WHERE data = ? AND usuario_id IS NULL ORDER BY id", (hoje,)
        ).fetchall()

def pegar_estatisticas_sinais():
    with conectar() as conn:
        total = conn.execute("""
            SELECT tipo, direcao,
                   COUNT(*) as total,
                   SUM(CASE WHEN acertou = 'sim' THEN 1 ELSE 0 END) as acertos,
                   SUM(CASE WHEN acertou = 'nao' THEN 1 ELSE 0 END) as erros,
                   SUM(CASE WHEN acertou IS NULL THEN 1 ELSE 0 END) as pendentes
            FROM sinais WHERE acertou IS NOT NULL
            GROUP BY tipo, direcao
            ORDER BY total DESC
        """).fetchall()
        return total

def pegar_sinais(usuario_id: int | None = None, limite: int = 50, offset: int = 0,
                tipo: str | None = None, status: str | None = None):
    with conectar() as conn:
        wheres = []
        params = []
        if usuario_id:
            wheres.append("usuario_id = ? OR usuario_id IS NULL")
            params.append(usuario_id)
        if tipo:
            wheres.append("tipo = ?")
            params.append(tipo)
        if status == "aberto":
            wheres.append("acertou IS NULL")
        elif status == "acertou":
            wheres.append("acertou = 'sim'")
        elif status == "errou":
            wheres.append("acertou = 'nao'")
        where_sql = " AND ".join(wheres) if wheres else "1=1"
        rows = conn.execute(f"""
            SELECT * FROM sinais
            WHERE {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (*params, limite, offset)).fetchall()
        return rows

def pegar_sinais_count(usuario_id: int | None = None, tipo: str | None = None,
                      status: str | None = None) -> int:
    with conectar() as conn:
        wheres = []
        params = []
        if usuario_id:
            wheres.append("usuario_id = ? OR usuario_id IS NULL")
            params.append(usuario_id)
        if tipo:
            wheres.append("tipo = ?")
            params.append(tipo)
        if status == "aberto":
            wheres.append("acertou IS NULL")
        elif status == "acertou":
            wheres.append("acertou = 'sim'")
        elif status == "errou":
            wheres.append("acertou = 'nao'")
        where_sql = " AND ".join(wheres) if wheres else "1=1"
        row = conn.execute(f"""
            SELECT COUNT(*) FROM sinais WHERE {where_sql}
        """, params).fetchone()
        return row[0] if row else 0

def pegar_resumo_sinais():
    with conectar() as conn:
        dados = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN acertou = 'sim' THEN 1 ELSE 0 END) as acertos,
                SUM(CASE WHEN acertou = 'nao' THEN 1 ELSE 0 END) as erros,
                SUM(CASE WHEN acertou IS NULL THEN 1 ELSE 0 END) as pendentes,
                COUNT(DISTINCT tipo) as tipos_ativos,
                MAX(data) as ultimo_sinal
            FROM sinais
        """).fetchone()
        return {
            "total": dados[0] or 0,
            "acertos": dados[1] or 0,
            "erros": dados[2] or 0,
            "pendentes": dados[3] or 0,
            "tipos_ativos": dados[4] or 0,
            "ultimo_sinal": dados[5] or "",
        }


def pegar_sinais_pendentes(dias: int = 30):
    with conectar() as conn:
        return conn.execute("""
            SELECT * FROM sinais
            WHERE acertou IS NULL
            AND data <= date('now', ?)
            ORDER BY data DESC
        """, (f"-{dias} days",)).fetchall()

# ─── Trades / Operações por Usuário ──────────────────────────

def registrar_trade(usuario_id: int, sinal_id=None, ativo="", tipo="", preco_entrada=0.0,
                    quantidade: float = 1.0):
    with conectar() as conn:
        hoje = str(date.today())
        conn.execute("""
            INSERT INTO trades
                (sinal_id, ativo, tipo, preco_entrada, data_entrada, usuario_id, quantidade)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sinal_id, ativo, tipo, preco_entrada, hoje, usuario_id, quantidade))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def fechar_trade(usuario_id: int, trade_id: int, preco_saida: float, observacao: str = ""):
    with conectar() as conn:
        trade = conn.execute(
            "SELECT * FROM trades WHERE id = ? AND usuario_id = ?", (trade_id, usuario_id)
        ).fetchone()
        if not trade:
            return
        # ATENÇÃO: colunas físicas reais (usuario_id foi add via migration)
        # 0=id, 1=sinal_id, 2=ativo, 3=tipo, 4=preco_entrada,
        # 5=preco_saida, 6=data_entrada, 7=data_saida, 8=resultado,
        # 9=pnl, 10=dias_operacao, 11=observacao, 12=created_at,
        # 13=usuario_id, 14=quantidade
        sinal_id = trade[1]
        ativo = trade[2]
        tipo = trade[3]
        preco_entrada = trade[4]
        data_entrada = trade[6]
        quantidade = float(trade[14]) if len(trade) > 14 and trade[14] is not None else 1.0
        if not data_entrada:
            data_entrada = str(date.today())
        dias = (date.today() - date.fromisoformat(data_entrada)).days
        pnl = (preco_saida - preco_entrada) * quantidade if tipo == 'compra' else (preco_entrada - preco_saida) * quantidade
        resultado = 'lucro' if pnl > 0 else 'prejuizo'
        hoje = str(date.today())

        conn.execute("""
            UPDATE trades SET
                preco_saida = ?, data_saida = ?, resultado = ?,
                pnl = ?, dias_operacao = ?, observacao = ?
            WHERE id = ?
        """, (preco_saida, hoje, resultado, round(pnl, 2), dias, observacao, trade_id))

        if sinal_id:
            conn.execute(
                "UPDATE sinais SET acertou = ?, data_desfecho = ? WHERE id = ?",
                ('sim' if resultado == 'lucro' else 'nao', hoje, sinal_id)
            )

def pegar_trades_abertos(usuario_id: int | None = None):
    with conectar() as conn:
        if usuario_id:
            return conn.execute("""
                SELECT t.*, s.explicacao as motivo, s.tipo as sinal_tipo,
                       s.direcao as sinal_direcao, s.preco_alvo as sinal_preco_alvo
                FROM trades t
                LEFT JOIN sinais s ON t.sinal_id = s.id
                WHERE t.resultado = 'aberto' AND t.usuario_id = ?
            """, (usuario_id,)).fetchall()
        return conn.execute("""
            SELECT t.*, s.explicacao as motivo
            FROM trades t
            LEFT JOIN sinais s ON t.sinal_id = s.id
            WHERE t.resultado = 'aberto'
        """).fetchall()

def pegar_operacoes_usuario(usuario_id: int, limite: int = 50, offset: int = 0):
    """Retorna operações (trades) de um usuário, com dados do sinal, ordenadas por data."""
    with conectar() as conn:
        rows = conn.execute("""
            SELECT t.*, s.explicacao as sinal_explicacao, s.tipo as sinal_tipo,
                   s.direcao as sinal_direcao, s.confianca as sinal_confianca,
                   s.preco_alvo as sinal_preco_alvo
            FROM trades t
            LEFT JOIN sinais s ON t.sinal_id = s.id
            WHERE t.usuario_id = ?
            ORDER BY t.id DESC
            LIMIT ? OFFSET ?
        """, (usuario_id, limite, offset)).fetchall()
        return rows

def pegar_total_operacoes_usuario(usuario_id: int) -> int:
    with conectar() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE usuario_id = ?", (usuario_id,)
        ).fetchone()
        return row[0] if row else 0

def pegar_operacao_por_sinal(usuario_id: int, sinal_id: int):
    """Verifica se usuário já está numa operação para este sinal."""
    with conectar() as conn:
        return conn.execute("""
            SELECT * FROM trades
            WHERE usuario_id = ? AND sinal_id = ? AND resultado = 'aberto'
            LIMIT 1
        """, (usuario_id, sinal_id)).fetchone()

def pegar_performance_usuario(usuario_id: int) -> dict:
    """Estatísticas completas de performance de um usuário."""
    with conectar() as conn:
        # Trades fechados
        fechados = conn.execute("""
            SELECT
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN resultado = 'lucro' THEN 1 ELSE 0 END), 0) as vitorias,
                COALESCE(SUM(CASE WHEN resultado = 'prejuizo' THEN 1 ELSE 0 END), 0) as derrotas,
                COALESCE(SUM(CASE WHEN resultado = 'lucro' THEN pnl ELSE 0 END), 0) as lucro_total,
                COALESCE(SUM(CASE WHEN resultado = 'prejuizo' THEN pnl ELSE 0 END), 0) as prejuizo_total,
                COALESCE(AVG(dias_operacao), 0) as dias_medio,
                COALESCE(MAX(pnl), 0) as maior_lucro,
                COALESCE(MIN(pnl), 0) as maior_prejuizo
            FROM trades WHERE resultado != 'aberto' AND usuario_id = ?
        """, (usuario_id,)).fetchone()

        # Trades abertos
        abertos = conn.execute("""
            SELECT COUNT(*), COALESCE(SUM(preco_entrada * quantidade), 0)
            FROM trades WHERE resultado = 'aberto' AND usuario_id = ?
        """, (usuario_id,)).fetchone()

        # Performance por ativo
        por_ativo = conn.execute("""
            SELECT ativo,
                   COUNT(*) as total,
                   SUM(CASE WHEN resultado = 'lucro' THEN 1 ELSE 0 END) as vitorias,
                   SUM(CASE WHEN resultado = 'prejuizo' THEN 1 ELSE 0 END) as derrotas,
                   COALESCE(SUM(CASE WHEN resultado = 'lucro' THEN pnl ELSE 0 END), 0) as lucro,
                   COALESCE(SUM(CASE WHEN resultado = 'prejuizo' THEN pnl ELSE 0 END), 0) as prejuizo
            FROM trades WHERE resultado != 'aberto' AND usuario_id = ?
            GROUP BY ativo
            ORDER BY total DESC
        """, (usuario_id,)).fetchall()

        # Série mensal de lucro
        mensal = conn.execute("""
            SELECT strftime('%Y-%m', data_saida) as mes,
                   COUNT(*) as total,
                   COALESCE(SUM(CASE WHEN resultado = 'lucro' THEN pnl ELSE 0 END), 0) as lucro,
                   COALESCE(SUM(CASE WHEN resultado = 'prejuizo' THEN pnl ELSE 0 END), 0) as prejuizo
            FROM trades WHERE resultado != 'aberto' AND usuario_id = ? AND data_saida IS NOT NULL
            GROUP BY mes
            ORDER BY mes DESC LIMIT 12
        """, (usuario_id,)).fetchall()

        total = fechados[0] or 0
        vitorias = fechados[1] or 0
        derrotas = fechados[2] or 0
        lucro_total = (fechados[3] or 0) + (fechados[4] or 0)
        taxa = round(vitorias / total * 100, 1) if total > 0 else 0

        return {
            "total": total,
            "vitorias": vitorias,
            "derrotas": derrotas,
            "taxa_acerto": taxa,
            "lucro_total": round(lucro_total, 2),
            "dias_medio": round(fechados[5] or 0, 1),
            "maior_lucro": round(fechados[6] or 0, 2),
            "maior_prejuizo": round(fechados[7] or 0, 2),
            "abertos": abertos[0] or 0,
            "capital_aberto": round(abertos[1] or 0, 2),
            "por_ativo": [
                {
                    "ativo": a[0] or "geral",
                    "total": a[1] or 0,
                    "vitorias": a[2] or 0,
                    "derrotas": a[3] or 0,
                    "lucro": round((a[4] or 0) + (a[5] or 0), 2),
                    "taxa": round((a[2] or 0) / (a[1] or 1) * 100, 1) if (a[1] or 0) > 0 else 0,
                }
                for a in por_ativo
            ],
            "mensal": [
                {
                    "mes": m[0],
                    "total": m[1] or 0,
                    "resultado": round((m[2] or 0) + (m[3] or 0), 2),
                }
                for m in mensal
            ],
        }

def pegar_performance_geral() -> dict:
    """Estatísticas agregadas de todos os usuários (visão admin)."""
    with conectar() as conn:
        total_operacoes = conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT usuario_id) as usuarios_ativos,
                COALESCE(SUM(CASE WHEN resultado = 'lucro' THEN 1 ELSE 0 END), 0) as vitorias,
                COALESCE(SUM(CASE WHEN resultado = 'prejuizo' THEN 1 ELSE 0 END), 0) as derrotas,
                COALESCE(SUM(pnl), 0) as pnl_total
            FROM trades WHERE resultado != 'aberto'
        """).fetchone()

        total = total_operacoes[0] or 0
        vitorias = total_operacoes[2] or 0
        taxa_geral = round(vitorias / total * 100, 1) if total > 0 else 0

        return {
            "total_operacoes": total,
            "usuarios_ativos": total_operacoes[1] or 0,
            "vitorias": vitorias,
            "derrotas": total_operacoes[3] or 0,
            "taxa_acerto_geral": taxa_geral,
            "pnl_total": round(total_operacoes[4] or 0, 2),
            "total_usuarios": contar_usuarios(),
            "operacoes_abertas": conn.execute(
                "SELECT COUNT(*) FROM trades WHERE resultado = 'aberto'"
            ).fetchone()[0] or 0,
        }

def pegar_resumo_trades(usuario_id: int | None = None):
    with conectar() as conn:
        if usuario_id:
            return conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN resultado = 'lucro' THEN 1 ELSE 0 END) as vitorias,
                    SUM(CASE WHEN resultado = 'prejuizo' THEN 1 ELSE 0 END) as derrotas,
                    COALESCE(SUM(CASE WHEN resultado = 'lucro' THEN pnl ELSE 0 END), 0) as lucro_total,
                    COALESCE(SUM(CASE WHEN resultado = 'prejuizo' THEN pnl ELSE 0 END), 0) as prejuizo_total,
                    AVG(dias_operacao) as dias_medio
                FROM trades WHERE resultado != 'aberto' AND usuario_id = ?
            """, (usuario_id,)).fetchone()
        return conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN resultado = 'lucro' THEN 1 ELSE 0 END) as vitorias,
                SUM(CASE WHEN resultado = 'prejuizo' THEN 1 ELSE 0 END) as derrotas,
                COALESCE(SUM(CASE WHEN resultado = 'lucro' THEN pnl ELSE 0 END), 0) as lucro_total,
                COALESCE(SUM(CASE WHEN resultado = 'prejuizo' THEN pnl ELSE 0 END), 0) as prejuizo_total,
                AVG(dias_operacao) as dias_medio
            FROM trades WHERE resultado != 'aberto'
        """).fetchone()

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
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (sinal_id) REFERENCES sinais(id)
            );

            CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
            CREATE INDEX IF NOT EXISTS idx_precos_data ON precos_diarios(data);

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
        for col in [(("sinais", "usuario_id"), "INTEGER REFERENCES usuarios(id)"),
                     (("trades", "usuario_id"), "INTEGER REFERENCES usuarios(id)")]:
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

def alterar_senha(usuario_id: int, senha_hash: str):
    with conectar() as conn:
        conn.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                     (senha_hash, usuario_id))

def pegar_usuarios_com_whatsapp() -> list:
    """Retorna usuários que cadastraram WhatsApp, com plano e número."""
    with conectar() as conn:
        rows = conn.execute(
            "SELECT id, nome, whatsapp, plano FROM usuarios "
            "WHERE whatsapp IS NOT NULL AND whatsapp != ''"
        ).fetchall()
        return rows

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
    """Salva múltiplos registros OHLCV de uma vez (INSERT OR REPLACE)."""
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

def pegar_sinais_pendentes(dias: int = 30):
    with conectar() as conn:
        return conn.execute("""
            SELECT * FROM sinais
            WHERE acertou IS NULL
            AND data <= date('now', ?)
            ORDER BY data DESC
        """, (f"-{dias} days",)).fetchall()

# ─── Trades ─────────────────────────────────────────────────

def registrar_trade(usuario_id: int, sinal_id=None, ativo="", tipo="", preco_entrada=0.0):
    with conectar() as conn:
        hoje = str(date.today())
        conn.execute("""
            INSERT INTO trades (sinal_id, ativo, tipo, preco_entrada, data_entrada, usuario_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sinal_id, ativo, tipo, preco_entrada, hoje, usuario_id))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def fechar_trade(usuario_id: int, trade_id: int, preco_saida: float, observacao: str = ""):
    with conectar() as conn:
        trade = conn.execute(
            "SELECT * FROM trades WHERE id = ? AND usuario_id = ?", (trade_id, usuario_id)
        ).fetchone()
        if not trade:
            return
        _, sinal_id, ativo, tipo, preco_entrada, _, data_entrada, *_ = trade
        data_entrada = data_entrada or str(date.today())
        dias = (date.today() - date.fromisoformat(data_entrada)).days
        pnl = preco_saida - preco_entrada if tipo == 'compra' else preco_entrada - preco_saida
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
                SELECT t.*, s.explicacao as motivo
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

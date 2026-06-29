import sqlite3
from datetime import date
from config import BANCO_PATH

def conectar():
    return sqlite3.connect(BANCO_PATH)

def criar_tabelas():
    with conectar() as conn:
        conn.executescript("""
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
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                FOREIGN KEY (sinal_id) REFERENCES sinais(id)
            );

            CREATE INDEX IF NOT EXISTS idx_precos_data ON precos_diarios(data);
            CREATE INDEX IF NOT EXISTS idx_sinais_data ON sinais(data);
            CREATE INDEX IF NOT EXISTS idx_trades_resultado ON trades(resultado);
        """)

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
                 explicacao, preco_alvo=None, preco_atual=None):
    with conectar() as conn:
        hoje = str(date.today())
        conn.execute("""
            INSERT INTO sinais
                (data, tipo, ativo, direcao, confianca, prazo_estimado,
                 explicacao, preco_alvo, preco_atual)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (hoje, tipo, ativo, direcao, confianca, prazo_estimado,
              explicacao, preco_alvo, preco_atual))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def pegar_sinais_hoje():
    with conectar() as conn:
        hoje = str(date.today())
        return conn.execute(
            "SELECT * FROM sinais WHERE data = ? ORDER BY id", (hoje,)
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

# ─── Trades ─────────────────────────────────────────────────

def registrar_trade(sinal_id, ativo, tipo, preco_entrada):
    with conectar() as conn:
        hoje = str(date.today())
        conn.execute("""
            INSERT INTO trades (sinal_id, ativo, tipo, preco_entrada, data_entrada)
            VALUES (?, ?, ?, ?, ?)
        """, (sinal_id, ativo, tipo, preco_entrada, hoje))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def fechar_trade(trade_id, preco_saida, observacao=""):
    with conectar() as conn:
        trade = conn.execute(
            "SELECT * FROM trades WHERE id = ?", (trade_id,)
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

def pegar_trades_abertos():
    with conectar() as conn:
        return conn.execute("""
            SELECT t.*, s.explicacao as motivo
            FROM trades t
            LEFT JOIN sinais s ON t.sinal_id = s.id
            WHERE t.resultado = 'aberto'
        """).fetchall()

def pegar_resumo_trades():
    with conectar() as conn:
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

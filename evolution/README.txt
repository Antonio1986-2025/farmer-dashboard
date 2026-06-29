╔══════════════════════════════════════════════════╗
║      EVOLUTION API — SETUP RÁPIDO               ║
╚══════════════════════════════════════════════════╝

A Evolution API é necessária para enviar os alertas
pelo WhatsApp. Ela funciona como uma ponte entre
o sistema e seu WhatsApp.

────────────────────────────────────────────────────
OPÇÃO 1: DOCKER (recomendada)
────────────────────────────────────────────────────

1. Instale o Docker Desktop:
   https://www.docker.com/products/docker-desktop/

2. Abra o terminal (PowerShell) e rode:

   docker run --name evolution-api -d \
     -p 8080:8080 \
     -e AUTHENTICATION_API_KEY="minhachave123" \
     -e DATABASE_ENABLED=true \
     -e DATABASE_CONNECTION_URI="sqlite:///evolution.db" \
     -v evolution-data:/evolution/store \
     atendai/evolution-api:latest

3. Acesse no navegador:
   http://localhost:8080

4. No menu, crie uma instância chamada "farmer"

5. Leia o QR Code com seu WhatsApp

6. Teste o envio:
   http://localhost:8080/message/sendText/farmer
   Body JSON: { "number": "553199999999", "text": "Teste!" }
   Header: apikey = minhachave123

────────────────────────────────────────────────────
OPÇÃO 2: HOSPEDADO (pago)
────────────────────────────────────────────────────

Existem serviços brasileiros que hospedam a
Evolution API por você. Pesquise por:
  "Evolution API hospedado"
  "WhatsApp API Brasil"

────────────────────────────────────────────────────
CONFIGURANDO NO SISTEMA
────────────────────────────────────────────────────

Depois da Evolution API rodando, edite o config.py:

   EVO_API_URL = "http://localhost:8080"
   EVO_API_KEY = "minhachave123"
   EVO_INSTANCE = "farmer"
   SEU_NUMERO = "553199999999"  (seu WhatsApp)

────────────────────────────────────────────────────
TESTANDO
────────────────────────────────────────────────────

Rode no terminal:
   cd farmer-dashboard
   python -c "from alerta.enviar import enviar_mensagem; enviar_mensagem('🧪 Teste do Farmer Dashboard!')"

Se aparecer "✅ WhatsApp: mensagem enviada" deu certo!

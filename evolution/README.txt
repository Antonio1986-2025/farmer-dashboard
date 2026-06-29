╔══════════════════════════════════════════════════╗
║         OPENWA — SETUP RÁPIDO                   ║
╚══════════════════════════════════════════════════╝

OpenWA é um gateway WhatsApp open-source e gratuito.
https://github.com/rmyndharis/OpenWA

────────────────────────────────────────────────────
DOCKER (recomendado)
────────────────────────────────────────────────────

1. Instale o Docker Desktop:
   https://www.docker.com/products/docker-desktop/

2. Abra o terminal (PowerShell) e rode:

   git clone https://github.com/rmyndharis/OpenWA.git
   cd OpenWA
   docker compose -f docker-compose.dev.yml up -d

3. Acesse o dashboard:
   http://localhost:2785

4. Crie uma chave de API:
   - Vá em API Keys > Create Key
   - Dê um nome (ex: "farmer")
   - Copie a chave gerada

5. Crie uma sessão "farmer":
   - Vá em Sessions > Create Session
   - Nome: farmer
   - Leia o QR Code com seu WhatsApp

6. Teste o envio:

   curl -X POST http://localhost:2785/api/sessions/farmer/messages/send-text \
     -H "Content-Type: application/json" \
     -H "X-API-Key: SUA_CHAVE" \
     -d '{"chatId": "553199999999@c.us", "text": "Teste!"}'

────────────────────────────────────────────────────
CONFIGURANDO NO SISTEMA
────────────────────────────────────────────────────

Edite o config.py (ou use variáveis de ambiente):

   OPENWA_API_URL = "http://localhost:2785"
   OPENWA_API_KEY = "sua_chave_aqui"
   OPENWA_SESSION = "farmer"
   SEU_NUMERO = "553199999999"  (seu WhatsApp)

────────────────────────────────────────────────────
TESTANDO
────────────────────────────────────────────────────

Rode no terminal:
   cd farmer-dashboard
   python -c "from alerta.enviar import enviar_mensagem; enviar_mensagem('🧪 Teste do Farmer Dashboard!')"

Se aparecer "✅ WhatsApp: mensagem enviada" deu certo!

from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import json
import time
import threading
import random

messages = []
visitors = {}  # vid -> { 'ip': ..., 'agent': ..., 'last_seen': timestamp, 'joined': time_str, 'pseudo': pseudo }
logs = []      # Historique des entrées / sorties pour le panneau HTML

ADJECTIFS = ["Rapide", "Calme", "Brillant", "Serein", "Audacieux", "Agile", "Futé", "Subtil", "Super", "Vif", "Eclair", "Habile"]
ANIMAUX = ["Panda", "Aigle", "Tigre", "Renard", "Loup", "Faucon", "Ours", "Lynx", "Castor", "Puma", "Falcon", "Koala"]

# Génération d'un pseudo unique non attribué
def generate_unique_pseudo():
    active_pseudos = {v['pseudo'] for v in visitors.values() if 'pseudo' in v}
    while True:
        adj = random.choice(ADJECTIFS)
        ani = random.choice(ANIMAUX)
        num = random.randint(10, 99)
        candidate = f"{adj}{ani}{num}"
        if candidate not in active_pseudos:
            return candidate

# Nettoyage automatique des utilisateurs déconnectés (Timeout de 5 secondes)
def check_expired_visitors():
    while True:
        now = time.time()
        to_remove = []
        for vid, info in list(visitors.items()):
            if now - info['last_seen'] > 5:
                to_remove.append((vid, info))
        
        for vid, info in to_remove:
            if vid in visitors:
                del visitors[vid]
                now_str = datetime.now().strftime('%H:%M:%S')
                print(f"\n---------------------------------------")
                print(f"[🔴 VISITEUR PARTI] : {now_str}")
                print(f"👤 Pseudo : {info['pseudo']}")
                print(f"📌 IP : {info['ip']}")
                print(f"---------------------------------------")
                logs.append({'text': f"🔴 Parti: {info['pseudo']} ({now_str})", 'type': 'left', 'id': time.time()})
                if len(logs) > 20:
                    logs.pop(0)
        time.sleep(1)

# Lancement du thread de nettoyage
threading.Thread(target=check_expired_visitors, daemon=True).start()

HTML_CONTENT = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Grille Horaire TV & Chat en direct</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    body { background-color: #0f172a; color: #f8fafc; padding: 20px; position: relative; min-height: 100vh; }
    h1 { text-align: center; margin-bottom: 25px; margin-top: 10px; color: #38bdf8; }

    /* Panneau de suivi des visiteurs (Ancré en haut de page, défile avec le scroll) */
    .visitor-widget {
      position: absolute;
      top: 15px;
      left: 15px;
      background-color: #1e293b;
      border: 1px solid #334155;
      border-radius: 10px;
      padding: 12px;
      width: 270px;
      max-height: 220px;
      z-index: 100;
      box-shadow: 0 8px 20px rgba(0,0,0,0.5);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .visitor-header {
      font-weight: bold;
      font-size: 0.85rem;
      color: #38bdf8;
      border-bottom: 1px solid #334155;
      padding-bottom: 6px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .online-badge {
      background-color: #22c55e;
      color: #0f172a;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: bold;
    }
    .my-pseudo-badge {
      font-size: 0.75rem;
      color: #f59e0b;
      font-weight: bold;
    }
    .visitor-logs {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 5px;
      font-size: 0.75rem;
    }
    .log-item {
      padding: 5px 8px;
      border-radius: 6px;
      background: #0f172a;
      word-break: break-all;
    }
    .log-item.joined { border-left: 3px solid #22c55e; color: #4ade80; }
    .log-item.left { border-left: 3px solid #ef4444; color: #f87171; }

    /* Adaptation spécifique pour les téléphones mobiles */
    @media (max-width: 650px) {
      .visitor-widget {
        position: relative;
        top: 0;
        left: 0;
        width: 100%;
        max-width: 100%;
        margin-bottom: 25px;
      }
      h1 { margin-top: 0; }
    }

    /* Grille Horaire */
    .schedule-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 20px;
      max-width: 1200px;
      margin: 40px auto 80px auto;
    }
    .channel-card {
      background: #1e293b;
      border-radius: 12px;
      padding: 18px;
      border: 1px solid #334155;
    }
    .channel-card h2 {
      color: #38bdf8;
      border-bottom: 2px solid #334155;
      padding-bottom: 8px;
      margin-bottom: 12px;
      font-size: 1.2rem;
    }
    .program-list { list-style: none; }
    .program-list li {
      padding: 6px 0;
      border-bottom: 1px dashed #334155;
      font-size: 0.9rem;
      display: flex;
      gap: 10px;
    }
    .time { font-weight: bold; color: #f59e0b; min-width: 55px; }

    /* Widget Chat Flottant (En bas à droite) */
    .chat-widget {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 9999;
    }
    .chat-btn {
      position: relative;
      background-color: #2563eb;
      color: white;
      border: none;
      padding: 14px 20px;
      border-radius: 30px;
      font-size: 1rem;
      font-weight: bold;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .green-dot {
      position: absolute;
      top: 0px;
      right: 0px;
      width: 14px;
      height: 14px;
      background-color: #22c55e;
      border: 2px solid #0f172a;
      border-radius: 50%;
      display: none;
      animation: pulse 1.8s infinite;
    }

    @keyframes pulse {
      0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
      70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); }
      100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
    }

    .chat-box {
      display: none;
      position: absolute;
      bottom: 60px;
      right: 0;
      width: 330px;
      height: 420px;
      background-color: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
      flex-direction: column;
      overflow: hidden;
    }
    .chat-box.active { display: flex !important; }
    .chat-header {
      background-color: #0f172a;
      padding: 12px;
      font-weight: bold;
      border-bottom: 1px solid #334155;
      display: flex;
      justify-content: space-between;
    }
    .close-btn { cursor: pointer; color: #94a3b8; font-size: 1.2rem; }
    .chat-messages {
      flex: 1;
      padding: 12px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
      font-size: 0.88rem;
    }
    .msg {
      padding: 8px 12px;
      border-radius: 10px;
      max-width: 80%;
      display: flex;
      flex-direction: column;
      word-break: break-word;
    }
    .msg.me { background: #2563eb; align-self: flex-end; border-bottom-right-radius: 2px; }
    .msg.other { background: #059669; align-self: flex-start; border-bottom-left-radius: 2px; }
    .msg small { font-size: 0.65rem; opacity: 0.75; margin-top: 4px; align-self: flex-end; }
    .msg .author-name { font-size: 0.7rem; font-weight: bold; color: #38bdf8; margin-bottom: 2px; }

    .chat-input-area {
      display: flex;
      padding: 10px;
      background-color: #0f172a;
      gap: 6px;
    }
    .chat-input-area input {
      flex: 1;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid #334155;
      background: #1e293b;
      color: white;
      outline: none;
    }
    .chat-input-area button {
      background: #22c55e;
      color: white;
      border: none;
      padding: 8px 14px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: bold;
    }
  </style>
</head>
<body>

  <div class="visitor-widget">
    <div class="visitor-header">
      <span>👁️ Visiteurs</span>
      <span class="online-badge"><span id="onlineCount">0</span> en ligne</span>
    </div>
    <div class="my-pseudo-badge">Vous êtes : <span id="myPseudoDisplay">...</span></div>
    <div class="visitor-logs" id="visitorLogs"></div>
  </div>

  <h1>Grille Horaire Télé</h1>

  <div class="schedule-grid">
    <div class="channel-card">
      <h2>RDS</h2>
      <ul class="program-list">
        <li><span class="time">08h00</span> Sports 30</li>
        <li><span class="time">10h00</span> Golf — Omnium britannique féminin</li>
        <li><span class="time">19h30</span> LCF — Alouettes de Montréal</li>
        <li><span class="time">22h00</span> Sports 30</li>
      </ul>
    </div>

    <div class="channel-card">
      <h2>TVA Sports</h2>
      <ul class="program-list">
        <li><span class="time">08h00</span> Baseball MLB</li>
        <li><span class="time">12h00</span> Tennis WTA</li>
        <li><span class="time">19h00</span> Baseball — Blue Jays de Toronto</li>
        <li><span class="time">22h00</span> Baseball MLB</li>
      </ul>
    </div>

    <div class="channel-card">
      <h2>MAX</h2>
      <ul class="program-list">
        <li><span class="time">10h00</span> Un fugitif à la maison</li>
        <li><span class="time">14h00</span> Cinéma — Avant la nuit tout est possible</li>
        <li><span class="time">19h00</span> McDonald & Dodds</li>
        <li><span class="time">21h00</span> Cinéma — Chasse à l'homme</li>
      </ul>
    </div>

    <div class="channel-card">
      <h2>TÉLÉTOON</h2>
      <ul class="program-list">
        <li><span class="time">15h00</span> Pokémon : les horizons</li>
        <li><span class="time">19h00</span> Tiny Toons Looniversity</li>
        <li><span class="time">21h00</span> Rick et Morty (Adult Swim)</li>
        <li><span class="time">22h30</span> Genndy Tartakovsky's Primal</li>
      </ul>
    </div>
  </div>

  <div class="chat-widget">
    <button class="chat-btn" onclick="toggleChat()">
      💬 Chat
      <span class="green-dot" id="chatDot"></span>
    </button>

    <div class="chat-box" id="chatBox">
      <div class="chat-header">
        <span>Chat en direct</span>
        <span class="close-btn" onclick="toggleChat()">✕</span>
      </div>

      <div class="chat-messages" id="chatMessages"></div>

      <div class="chat-input-area">
        <input type="text" id="msgInput" placeholder="Écrivez un message..." onkeypress="handleKeyPress(event)">
        <button onclick="sendMessage()">Envoyer</button>
      </div>
    </div>
  </div>

  <script>
    const myId = 'v_' + Math.random().toString(36).substr(2, 9);
    let myPseudo = '';
    let lastSeenMsgId = 0;

    function playNotificationSound() {
      try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, audioCtx.currentTime);
        osc.frequency.setValueAtTime(880, audioCtx.currentTime + 0.08);
        gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.35);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.35);
      } catch (e) {}
    }

    function toggleChat() {
      const chatBox = document.getElementById('chatBox');
      const chatDot = document.getElementById('chatDot');
      chatBox.classList.toggle('active');
      if (chatBox.classList.contains('active')) {
        chatDot.style.display = 'none';
      }
    }

    function sendMessage() {
      const input = document.getElementById('msgInput');
      const text = input.value.trim();
      if (text !== '') {
        fetch('/api/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ senderId: myId, senderPseudo: myPseudo, text: text })
        });
        input.value = '';
      }
    }

    function handleKeyPress(e) {
      if (e.key === 'Enter') sendMessage();
    }

    function sendPing() {
      fetch('/api/ping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: myId, agent: navigator.userAgent })
      })
      .then(res => res.json())
      .then(data => {
        if (data.myPseudo) {
          myPseudo = data.myPseudo;
          document.getElementById('myPseudoDisplay').textContent = myPseudo;
        }

        document.getElementById('onlineCount').textContent = data.onlineCount;
        const logBox = document.getElementById('visitorLogs');
        logBox.innerHTML = '';
        data.logs.forEach(log => {
          const div = document.createElement('div');
          div.className = 'log-item ' + log.type;
          div.textContent = log.text;
          logBox.appendChild(div);
        });
        logBox.scrollTop = logBox.scrollHeight;

        const chatMessages = document.getElementById('chatMessages');
        const chatBox = document.getElementById('chatBox');
        const chatDot = document.getElementById('chatDot');

        data.messages.forEach(msg => {
          if (msg.id > lastSeenMsgId) {
            lastSeenMsgId = msg.id;
            const isMe = (msg.senderId === myId);
            const msgDiv = document.createElement('div');
            msgDiv.className = 'msg ' + (isMe ? 'me' : 'other');
            
            const authorText = isMe ? 'Moi' : (msg.senderPseudo || 'Anonyme');
            msgDiv.innerHTML = '<span class="author-name">' + authorText + '</span><span>' + msg.text + '</span><small>' + msg.time + '</small>';
            
            chatMessages.appendChild(msgDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            if (!isMe) {
              playNotificationSound();
              if (!chatBox.classList.contains('active')) {
                chatDot.style.display = 'block';
              }
            }
          }
        });
      });
    }

    window.addEventListener('beforeunload', () => {
      navigator.sendBeacon('/api/leave', JSON.stringify({ id: myId }));
    });

    setInterval(sendPing, 1200);
    sendPing();
  </script>
</body>
</html>
"""

class ChatServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(length) if length > 0 else b'{}'
        data = json.loads(post_data.decode('utf-8'))
        client_ip = self.headers.get('X-Forwarded-For', self.client_address[0])

        if self.path == '/api/ping':
            vid = data.get('id')
            now_time = time.time()
            now_str = datetime.now().strftime('%H:%M:%S')

            if vid not in visitors:
                pseudo = generate_unique_pseudo()
                agent = data.get('agent', 'Inconnu')
                visitors[vid] = {'ip': client_ip, 'agent': agent, 'joined': now_str, 'last_seen': now_time, 'pseudo': pseudo}
                
                print(f"\n---------------------------------------")
                print(f"[🟢 NOUVEAU VISITEUR CONNECTÉ] : {now_str}")
                print(f"👤 Pseudo : {pseudo}")
                print(f"📌 IP : {client_ip}")
                print(f"🌐 Appareil : {agent}")
                print(f"---------------------------------------")
                
                logs.append({'text': f"🟢 Arrivée: {pseudo} ({now_str})", 'type': 'joined', 'id': now_time})
                if len(logs) > 20:
                    logs.pop(0)
            else:
                visitors[vid]['last_seen'] = now_time
                pseudo = visitors[vid]['pseudo']

            response = {
                'myPseudo': pseudo,
                'onlineCount': len(visitors),
                'logs': logs,
                'messages': messages
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

        elif self.path == '/api/leave':
            vid = data.get('id')
            if vid in visitors:
                info = visitors.pop(vid)
                now_str = datetime.now().strftime('%H:%M:%S')
                
                print(f"\n---------------------------------------")
                print(f"[🔴 VISITEUR A QUITTÉ LE SITE] : {now_str}")
                print(f"👤 Pseudo : {info['pseudo']}")
                print(f"📌 IP : {info['ip']}")
                print(f"---------------------------------------")
                
                logs.append({'text': f"🔴 Parti: {info['pseudo']} ({now_str})", 'type': 'left', 'id': time.time()})
                if len(logs) > 20:
                    logs.pop(0)

            self.send_response(200)
            self.end_headers()

        elif self.path == '/api/send':
            msg = {
                'id': len(messages) + 1,
                'senderId': data.get('senderId'),
                'senderPseudo': data.get('senderPseudo', 'Anonyme'),
                'text': data.get('text'),
                'time': datetime.now().strftime('%H:%M')
            }
            messages.append(msg)
            self.send_response(200)
            self.end_headers()

    def log_message(self, format, *args):
        return

if __name__ == '__main__':
    port = 3000
    print(f"🚀 Serveur Web, Chat & Suivi Visiteurs sur http://localhost:{port}")
    httpd = HTTPServer(('0.0.0.0', port), ChatServer)
    httpd.serve_forever()

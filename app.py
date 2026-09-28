from __future__ import annotations

import hashlib
import hmac
import io
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import qrcode
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template_string,
    request,
    send_file,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select
from werkzeug.middleware.proxy_fix import ProxyFix


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["SECRET_KEY"] = os.environ.get("SESSION_SECRET", "")
if os.environ.get("RENDER") and not all(
    os.environ.get(key) for key in ("DATABASE_URL", "ADMIN_PASSWORD", "SESSION_SECRET", "CODE_PEPPER")
):
    raise RuntimeError("Configura DATABASE_URL, ADMIN_PASSWORD, SESSION_SECRET y CODE_PEPPER en Render.")
database_url = os.environ.get("DATABASE_URL", "sqlite:///towiz-renovaciones.sqlite3")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
app.config.update(
    SQLALCHEMY_DATABASE_URI=database_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=16 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("RENDER", "") == "true",
)
db = SQLAlchemy(app)

TEN_DAYS = 10 * 24 * 60 * 60
DEVICE_RE = re.compile(r"^[a-f0-9-]{16,64}$", re.IGNORECASE)
OTP_RE = re.compile(r"^\d{8}$")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value else None


def as_utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc) if value else None


def code_digest(device_id: str, code: str) -> str:
    pepper = os.environ.get("CODE_PEPPER", app.config["SECRET_KEY"])
    return hmac.new(pepper.encode(), f"{device_id}:{code}".encode(), hashlib.sha256).hexdigest()


class Activation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)


class OneTimeCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), nullable=False, index=True)
    digest = db.Column(db.String(64), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    consumed_at = db.Column(db.DateTime(timezone=True))


with app.app_context():
    db.create_all()


def base_url() -> str:
    configured = os.environ.get("BASE_URL", "").strip().rstrip("/")
    return configured or request.url_root.rstrip("/")


def cycle_number() -> int:
    return int(time.time()) // TEN_DAYS


def qr_signature(device_id: str, cycle: int) -> str:
    key = os.environ.get("CODE_PEPPER", app.config["SECRET_KEY"])
    if not key:
        abort(503, "El servidor no está configurado.")
    message = f"{device_id}:{cycle}".encode()
    return hmac.new(key.encode(), message, hashlib.sha256).hexdigest()[:24]


def valid_device(device_id: str) -> bool:
    return bool(DEVICE_RE.fullmatch(device_id))


def csrf_token() -> str:
    token = session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(24)
        session["csrf"] = token
    return token


def require_admin() -> None:
    if not session.get("admin"):
        abort(401)


PROMO = """<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Acceso TOWIZ</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#080b16;color:#f4f6ff;font:16px system-ui,sans-serif}
main{max-width:540px;margin:0 auto;padding:26px 20px 48px}.card{background:#11182a;border:1px solid #26334d;border-radius:22px;padding:22px;margin:16px 0;box-shadow:0 12px 40px #0005}
.brand{display:flex;align-items:center;justify-content:center;min-height:70px}.brand img{max-width:190px;max-height:72px;object-fit:contain}.promo{display:grid;place-items:center;min-height:190px;border-radius:16px;background:linear-gradient(135deg,#10345a,#17bde1 55%,#752fce);color:white;text-align:center;padding:24px;font-size:22px;font-weight:750}
h1{font-size:25px;margin:8px 0}p{color:#bdc9df;line-height:1.5}.actions{display:grid;gap:12px;margin-top:18px}a.btn,button{display:block;border:0;border-radius:14px;padding:15px 18px;text-align:center;font:700 16px system-ui;text-decoration:none;color:#07111d;background:#24c7df;cursor:pointer}a.secondary{color:#eaf3ff;background:#273750}
.small{font-size:13px;color:#9cabc4}.error{color:#ffafaf}.ok{color:#92ffd6}
</style><main>
<div class="brand">{% if logo %}<img src="{{ logo }}" alt="TOWIZ">{% else %}<h1>TOWIZ</h1>{% endif %}</div>
<section class="card"><div class="promo">{% if promo %}<img src="{{ promo }}" alt="Promoción TOWIZ" style="max-width:100%;max-height:280px;object-fit:contain;border-radius:12px">{% else %}Aquí irá la imagen de promoción TOWIZ{% endif %}</div>
<h1>Comparte TOWIZ</h1><p>Comparte nuestra promoción y solicita la renovación de tu acceso. El gestor te enviará un código de un solo uso.</p>
<div class="actions"><button id="share">Compartir promoción</button><a class="btn secondary" href="{{ whatsapp }}">Notificar por WhatsApp</a></div>
<p class="small">Solicitud: <strong>{{ short_device }}</strong> · Código QR del período {{ cycle }}</p>
<p id="feedback" class="small" aria-live="polite"></p></section>
<script>
const shareData={title:'TOWIZ',text:'Mira esta promoción de TOWIZ y solicita tu acceso.',url:location.href};
document.querySelector('#share').addEventListener('click',async()=>{const f=document.querySelector('#feedback');try{if(navigator.share)await navigator.share(shareData);else{await navigator.clipboard.writeText(shareData.text+' '+shareData.url);f.textContent='Enlace copiado para compartir.';f.className='small ok';}}catch(e){if(e.name!=='AbortError'){f.textContent='No se pudo abrir compartir. Copia el enlace de esta página.';f.className='small error';}}});
</script></main></html>"""

LOCK_PAGE = """<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Acceso TOWIZ</title>
<style>*{box-sizing:border-box}body{margin:0;background:#080b16;color:#f4f6ff;font:16px system-ui,sans-serif}main{max-width:480px;margin:0 auto;padding:24px 18px}.card{background:#11182a;border:1px solid #293954;border-radius:20px;padding:20px;margin:16px 0;text-align:center}h1{font-size:24px}p{color:#b9c6dc;line-height:1.45}.qr{width:min(76vw,310px);height:auto;background:#fff;padding:10px;border-radius:12px}input,button{width:100%;padding:14px;border-radius:12px;border:1px solid #3c4d69;margin:8px 0;background:#0b1120;color:white;font:inherit}button{background:#22c5df;color:#06111a;border:0;font-weight:750}a{color:#52dcef}.small{font-size:13px;color:#97a9c4}#result{min-height:24px}</style>
<main><section class="card"><h1>TOWIZ está bloqueado</h1><p>Escanea este QR con otro teléfono para compartir la promoción y avisar al gestor. Luego ingresa aquí el código de un solo uso que te envíe.</p>
<img class="qr" src="{{ qr }}" alt="QR para solicitar renovación"><p class="small">ID del dispositivo: <code>{{ device }}</code></p>
<a href="{{ renew }}">Abrir la página de renovación en este teléfono</a>
<form id="redeem"><label for="code"><p>Código de activación</p></label><input id="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{8}" maxlength="8" placeholder="8 dígitos" required><button>Activar 10 días</button></form><p id="result" role="status"></p><p id="return" style="display:none">Ahora vuelve a TOWIZ para continuar.</p></section></main>
<script>const form=document.querySelector('#redeem'),result=document.querySelector('#result'),back=document.querySelector('#return');async function check(){try{const x=await fetch('{{ status_api }}',{cache:'no-store'}),d=await x.json();if(!d.locked){form.style.display='none';result.textContent='Acceso activo hasta '+new Date(d.expires_at).toLocaleString();result.style.color='#8df5ca';back.style.display='block';}}catch(e){}}check();form.addEventListener('submit',async e=>{e.preventDefault();result.textContent='Verificando…';try{const x=await fetch('{{ redeem_api }}',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device:'{{ device }}',code:document.querySelector('#code').value})});const d=await x.json();if(!x.ok)throw new Error(d.error||'No se pudo validar el código.');form.style.display='none';result.textContent='Acceso activado hasta '+new Date(d.expires_at).toLocaleString();result.style.color='#8df5ca';back.style.display='block';}catch(err){result.textContent=err.message;result.style.color='#ffaaaa';}});</script></html>"""


ADMIN = """<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gestor TOWIZ</title>
<style>body{margin:0;background:#080b16;color:#eef4ff;font:16px system-ui}main{max-width:620px;margin:40px auto;padding:24px}.box{background:#11182a;border:1px solid #293954;border-radius:18px;padding:24px}input,button{width:100%;padding:13px;border-radius:10px;border:1px solid #40516e;margin:8px 0;background:#0b1120;color:white;font:inherit}button{background:#20c4df;color:#07111d;border:0;font-weight:700;cursor:pointer}.code{font-size:34px;letter-spacing:7px;text-align:center;color:#45def0;font-weight:800}.hint{color:#afbdd3;font-size:14px}</style><main><div class="box"><h1>Gestor de renovaciones TOWIZ</h1>
{% for message in get_flashed_messages() %}<p>{{ message }}</p>{% endfor %}
{% if not logged %}<form method="post"><input type="hidden" name="csrf" value="{{ csrf }}"><label>Contraseña de gestor</label><input type="password" name="password" required><button>Ingresar</button></form>
{% else %}<p class="hint">Pega el identificador que aparece en la solicitud de WhatsApp. El código vence en 30 minutos y solo se usa una vez.</p>
<form method="post"><input type="hidden" name="csrf" value="{{ csrf }}"><input type="hidden" name="action" value="generate"><label>Identificador del cliente</label><input name="device" minlength="16" maxlength="64" required value="{{ device }}"><button>Generar código de un solo uso</button></form>
{% if code %}<p>Envía este código al cliente:</p><div class="code">{{ code }}</div>{% endif %}<form method="post"><input type="hidden" name="csrf" value="{{ csrf }}"><input type="hidden" name="action" value="logout"><button class="secondary">Cerrar sesión</button></form>{% endif %}</div></main></html>"""


@app.get("/healthz")
def healthz():
    db.session.execute(select(1))
    return jsonify(status="ok")


@app.get("/")
def index():
    return redirect(url_for("admin"))


@app.get("/renew")
def renew():
    device = request.args.get("d", "")
    cycle = request.args.get("e", "")
    signature = request.args.get("s", "")
    if not valid_device(device):
        abort(400, "Enlace de renovación inválido.")
    try:
        parsed_cycle = int(cycle)
    except ValueError:
        abort(400, "Período inválido.")
    if parsed_cycle != cycle_number() or not hmac.compare_digest(signature, qr_signature(device, parsed_cycle)):
        abort(410, "Este QR venció. Abre la app para obtener el QR vigente.")
    whatsapp_number = re.sub(r"\D", "", os.environ.get("WHATSAPP_NUMBER", "5491136021940"))
    message = quote(f"Hola, solicito renovar mi acceso TOWIZ. Dispositivo: {device}. Período QR: {parsed_cycle}.")
    return render_template_string(
        PROMO,
        device=device,
        short_device=device[:8] + "…",
        cycle=parsed_cycle,
        logo=os.environ.get("LOGO_IMAGE_URL", url_for("static", filename="towiz-logo.png")),
        promo=os.environ.get("PROMO_IMAGE_URL", ""),
        whatsapp=f"https://wa.me/{whatsapp_number}?text={message}",
    )


@app.get("/app/<device>")
def app_lock_page(device: str):
    if not valid_device(device):
        abort(400)
    cycle = cycle_number()
    renew_url = f"{url_for('renew', _external=True)}?d={quote(device)}&e={cycle}&s={qr_signature(device, cycle)}"
    return render_template_string(
        LOCK_PAGE,
        device=device,
        qr=url_for("qr_png", device=device),
        renew=renew_url,
        redeem_api=url_for("redeem"),
        status_api=url_for("status", device=device),
    )


@app.get("/qr/<device>.png")
def qr_png(device: str):
    if not valid_device(device):
        abort(400)
    cycle = cycle_number()
    link = f"{base_url()}{url_for('renew')}?d={quote(device)}&e={cycle}&s={qr_signature(device, cycle)}"
    image = qrcode.make(link, box_size=10, border=3)
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return send_file(output, mimetype="image/png", max_age=300)


@app.get("/api/status/<device>")
def status(device: str):
    if not valid_device(device):
        abort(400)
    record = db.session.scalar(select(Activation).where(Activation.device_id == device))
    now = utcnow()
    expiry = as_utc(record.expires_at) if record else None
    return jsonify(locked=not (expiry and expiry > now), expires_at=iso(expiry), cycle=cycle_number())


@app.post("/api/redeem")
def redeem():
    data = request.get_json(silent=True) or request.form
    device = str(data.get("device", ""))
    code = str(data.get("code", ""))
    if not valid_device(device) or not OTP_RE.fullmatch(code):
        return jsonify(error="El identificador o el código no son válidos."), 400
    now = utcnow()
    try:
        record = db.session.scalar(
            select(OneTimeCode).where(
                OneTimeCode.device_id == device,
                OneTimeCode.digest == code_digest(device, code),
                OneTimeCode.consumed_at.is_(None),
            ).with_for_update()
        )
        if not record or as_utc(record.expires_at) <= now:
            db.session.rollback()
            return jsonify(error="Código incorrecto, vencido o ya utilizado."), 403
        record.consumed_at = now
        expiry = now + timedelta(seconds=TEN_DAYS)
        activation = db.session.scalar(select(Activation).where(Activation.device_id == device).with_for_update())
        if activation:
            activation.expires_at = expiry
        else:
            db.session.add(Activation(device_id=device, expires_at=expiry))
        db.session.commit()
        return jsonify(ok=True, expires_at=iso(expiry), duration_days=10)
    except Exception:
        db.session.rollback()
        raise


@app.route("/admin", methods=["GET", "POST"])
def admin():
    code = None
    device = ""
    if request.method == "POST":
        if not hmac.compare_digest(request.form.get("csrf", ""), session.get("csrf", "")):
            abort(400)
        action = request.form.get("action")
        if action == "logout":
            session.clear()
            return redirect(url_for("admin"))
        if not session.get("admin"):
            password = os.environ.get("ADMIN_PASSWORD", "")
            if not password or not hmac.compare_digest(request.form.get("password", ""), password):
                flash("Contraseña incorrecta.")
            else:
                session["admin"] = True
                return redirect(url_for("admin"))
        elif action == "generate":
            device = request.form.get("device", "")
            if not valid_device(device):
                flash("El identificador del cliente no es válido.")
            else:
                code = f"{secrets.randbelow(100_000_000):08d}"
                for pending in db.session.scalars(
                    select(OneTimeCode).where(
                        OneTimeCode.device_id == device,
                        OneTimeCode.consumed_at.is_(None),
                    )
                ):
                    pending.consumed_at = utcnow()
                db.session.add(OneTimeCode(device_id=device, digest=code_digest(device, code), expires_at=utcnow() + timedelta(minutes=30)))
                db.session.commit()
    return render_template_string(ADMIN, logged=bool(session.get("admin")), csrf=csrf_token(), code=code, device=device)


@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(410)
@app.errorhandler(503)
def http_error(error):
    return jsonify(error=error.description), error.code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")), debug=False)


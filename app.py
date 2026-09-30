from __future__ import annotations

import io
import os
import re

import qrcode
from flask import Flask, abort, jsonify, render_template_string, send_file
from werkzeug.middleware.proxy_fix import ProxyFix


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
REQUEST_RE = re.compile(r"^[A-Z0-9]{6}$")


PAGE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#080b16">
<title>TVWIZ</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#080b16;color:#f4f6ff;font:16px system-ui,sans-serif}
main{max-width:540px;margin:0 auto;padding:24px 18px 48px}.card{background:#11182a;border:1px solid #293954;border-radius:20px;padding:20px;margin:16px 0;text-align:center;box-shadow:0 12px 40px #0005}
.brand{min-height:64px;display:grid;place-items:center}.brand img{max-width:190px;max-height:64px;object-fit:contain}.promo{display:grid;place-items:center;min-height:190px;border-radius:16px;background:linear-gradient(135deg,#10345a,#17bde1 55%,#752fce);overflow:hidden;color:#fff;font-size:21px;font-weight:750;padding:18px}.promo img{max-width:100%;max-height:310px;object-fit:contain;border-radius:12px}
h1{font-size:24px;margin:10px 0}p{color:#bdc9df;line-height:1.5}.actions{display:grid;gap:12px;margin-top:18px}button,a.btn{display:block;width:100%;border:0;border-radius:13px;padding:14px 18px;text-align:center;font:700 16px system-ui;text-decoration:none;color:#07111d;background:#24c7df;cursor:pointer}button.secondary,a.secondary{color:#eaf3ff;background:#273750}button:disabled{opacity:.5;cursor:not-allowed}a[aria-disabled="true"]{opacity:.5;pointer-events:none}
.camera{width:100%;max-height:320px;object-fit:cover;border-radius:14px;background:#05070d;margin-top:10px}input{width:100%;padding:14px;border-radius:12px;border:1px solid #3c4d69;margin:8px 0;background:#0b1120;color:white;font:inherit;text-align:center;letter-spacing:3px;text-transform:uppercase}.small{font-size:13px;color:#9cabc4}.error{color:#ffaaaa}.ok{color:#92ffd6}.code{font-size:26px;letter-spacing:5px;color:#45def0;font-weight:800;min-height:36px}
</style>
</head>
<body><main>
<div class="brand">{% if logo %}<img src="{{ logo }}" alt="TVWIZ">{% else %}<h1>TVWIZ</h1>{% endif %}</div>
<section class="card"><div class="promo">{% if promo %}<img src="{{ promo }}" alt="Promoción TVWIZ">{% else %}Aquí irá la imagen promocional de TVWIZ{% endif %}</div>
<h1>Solicitar acceso</h1><p>Escanea el QR que aparece en la app. También puedes escribir el código de solicitud manualmente.</p>
<div class="actions"><button id="start">Escanear QR</button><video id="camera" class="camera" playsinline muted hidden></video><p id="status" class="small" role="status">La cámara solo se usa para leer el código de solicitud.</p></div>
<label class="small" for="manual">Código de solicitud</label><input id="manual" maxlength="6" autocomplete="off" autocapitalize="characters" placeholder="6 caracteres" aria-label="Código de solicitud">
<button id="use-code" class="secondary">Continuar con este código</button><p id="result" class="code" aria-live="polite"></p>
<div class="actions"><button id="share" disabled>Compartir imagen promocional</button><a id="notify" class="btn secondary" href="#" aria-disabled="true">Notificar por WhatsApp</a></div>
<p class="small">Primero comparte nuestra imagen promocional en tu estado de WhatsApp. Después, pulsa «Notificar» para que activemos la app. WhatsApp enviará al gestor tu código de solicitud.</p>
</section></main>
<script>
const camera=document.querySelector('#camera'),statusText=document.querySelector('#status'),manual=document.querySelector('#manual'),result=document.querySelector('#result'),shareButton=document.querySelector('#share'),notifyLink=document.querySelector('#notify');
let detector=null,stream=null,scanActive=false,requestCode='';
const whatsappNumber={{ whatsapp_number|tojson }};
function parseRequest(raw){let text=String(raw||'').trim().toUpperCase();let match=text.match(/^(?:(?:TVWIZ|TOWIZ)[:/ -])?([A-Z0-9]{6})$/);if(match)return match[1];try{const obj=JSON.parse(text);text=String(obj.request_code||obj.requestCode||obj.code||'').trim().toUpperCase()}catch(_){}try{const u=new URL(text);text=(u.searchParams.get('code')||u.searchParams.get('request')||'').trim().toUpperCase()}catch(_){}match=text.match(/^(?:(?:TVWIZ|TOWIZ)[:/ -])?([A-Z0-9]{6})$/);return match?match[1]:null}
function stopCamera(){scanActive=false;if(stream){stream.getTracks().forEach(t=>t.stop());stream=null}camera.srcObject=null;camera.hidden=true}
function acceptCode(value){const code=parseRequest(value);if(!code){statusText.textContent='QR no reconocido. Debe contener un código TVWIZ de 6 caracteres.';statusText.className='small error';return false}requestCode=code;manual.value=code;result.textContent=code;shareButton.disabled=false;if(whatsappNumber){const message=encodeURIComponent('Hola, solicito activar la app TVWIZ. Código de solicitud: '+code);notifyLink.href='https://wa.me/'+whatsappNumber+'?text='+message;notifyLink.setAttribute('aria-disabled','false');statusText.textContent='Comparte primero la imagen en tu estado de WhatsApp y luego pulsa Notificar.'}else{statusText.textContent='Código leído. El número de WhatsApp del gestor aún no está configurado.'}statusText.className=whatsappNumber?'small ok':'small error';stopCamera();return true}
async function scanLoop(){if(!scanActive)return;try{const found=await detector.detect(camera);if(found.length){if(acceptCode(found[0].rawValue))return}}catch(e){statusText.textContent='No se pudo leer el QR. Prueba acercar o alejar el teléfono.'}requestAnimationFrame(scanLoop)}
document.querySelector('#start').addEventListener('click',async()=>{if(!navigator.mediaDevices?.getUserMedia||!('BarcodeDetector' in window)){statusText.textContent='Este navegador no permite leer QR aquí. Escribe el código de 6 caracteres que muestra la app.';statusText.className='small error';manual.focus();return}try{detector=new BarcodeDetector({formats:['qr_code']});stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});camera.srcObject=stream;camera.hidden=false;await camera.play();scanActive=true;statusText.textContent='Apunta la cámara al QR de la app.';statusText.className='small';scanLoop()}catch(e){statusText.textContent='No se pudo abrir la cámara. Revisa el permiso o escribe el código manualmente.';statusText.className='small error';stopCamera()}});
document.querySelector('#use-code').addEventListener('click',()=>acceptCode(manual.value));
manual.addEventListener('input',()=>{manual.value=manual.value.toUpperCase().replace(/[^A-Z0-9]/g,'').slice(0,6)});
shareButton.addEventListener('click',async()=>{if(!requestCode)return;const image=document.querySelector('.promo img');const data={title:'Promoción TVWIZ',text:'Mira esta promoción de TVWIZ y solicita tu acceso.',url:location.href};try{if(image?.src&&navigator.canShare&&navigator.share){const response=await fetch(image.src);const blob=await response.blob();const file=new File([blob],'promocion-tvwiz.'+(blob.type.split('/')[1]||'jpg'),{type:blob.type||'image/jpeg'});if(navigator.canShare({files:[file]})){await navigator.share({title:data.title,text:data.text,files:[file]});statusText.textContent='Imagen compartida. Ahora pulsa Notificar.';statusText.className='small ok';return}}if(navigator.share){await navigator.share(data);statusText.textContent='En el menú de compartir, elige WhatsApp y publícala en tu estado. Luego pulsa Notificar.';statusText.className='small ok'}else{await navigator.clipboard.writeText(data.text+' '+data.url);statusText.textContent='Enlace copiado. Compártelo en tu estado y luego pulsa Notificar.';statusText.className='small ok'}}catch(e){if(e.name!=='AbortError'){statusText.textContent='No se pudo compartir. Prueba guardar la imagen y publicarla en tu estado de WhatsApp.';statusText.className='small error'}}});
window.addEventListener('pagehide',stopCamera);
</script></body></html>"""


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/")
def index():
    whatsapp = re.sub(r"\D", "", os.environ.get("WHATSAPP_NUMBER", ""))
    return render_template_string(
        PAGE,
        whatsapp_number=whatsapp,
        logo=os.environ.get("LOGO_IMAGE_URL", "/static/tvwiz-logo.png"),
        promo=os.environ.get("PROMO_IMAGE_URL") or "/static/tvwiz-flyer.jpg",
    )


@app.get("/qr/<request_code>.png")
def request_qr(request_code: str):
    request_code = request_code.upper()
    if not REQUEST_RE.fullmatch(request_code):
        abort(400, "Código de solicitud inválido.")
    image = qrcode.make(f"TVWIZ:{request_code}", box_size=10, border=3)
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return send_file(output, mimetype="image/png", max_age=60)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")), debug=False)

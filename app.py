from __future__ import annotations

import os
import re
from flask import Flask, jsonify, render_template_string
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#080b16"><title>TVWIZ</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#080b16;color:#f4f6ff;font:16px system-ui,sans-serif}main{max-width:540px;margin:0 auto;padding:24px 18px 48px}.card{background:#11182a;border:1px solid #293954;border-radius:20px;padding:20px;margin:16px 0;text-align:center;box-shadow:0 12px 40px #0005}.brand{min-height:64px;display:grid;place-items:center}.brand img{max-width:190px;max-height:64px;object-fit:contain}.promo{display:grid;place-items:center;min-height:190px;border-radius:16px;background:linear-gradient(135deg,#10345a,#17bde1 55%,#752fce);overflow:hidden;padding:18px}.promo img{max-width:100%;max-height:310px;object-fit:contain;border-radius:12px}h1{font-size:24px;margin:10px 0}h2{font-size:20px;margin:8px 0}p{color:#bdc9df;line-height:1.5}.step{padding:18px 0;border-top:1px solid #293954}.step[hidden]{display:none}.step-count{color:#45def0;font-size:13px;font-weight:700;letter-spacing:1px;text-transform:uppercase}button,a.btn{display:block;width:100%;border:0;border-radius:13px;padding:14px 18px;text-align:center;font:700 16px system-ui;text-decoration:none;color:#07111d;background:#24c7df;cursor:pointer}button.secondary{color:#eaf3ff;background:#273750}button:disabled{opacity:.5;cursor:not-allowed}a[aria-disabled="true"]{opacity:.5;pointer-events:none}input{width:100%;padding:14px;border-radius:12px;border:1px solid #3c4d69;margin:8px 0;background:#0b1120;color:white;font:inherit;text-align:center;letter-spacing:3px;text-transform:uppercase}.small{font-size:13px;color:#9cabc4}.error{color:#ffaaaa}.ok,.resume{color:#92ffd6}.code{font-size:26px;letter-spacing:5px;color:#45def0;font-weight:800;min-height:36px}.actions{display:grid;gap:12px;margin-top:18px}
</style></head><body><main>
<div class="brand">{% if logo %}<img src="{{ logo }}" alt="TVWIZ">{% else %}<h1>TVWIZ</h1>{% endif %}</div>
<section class="card"><div class="promo">{% if promo %}<img src="{{ promo }}" alt="Promocion TVWIZ">{% else %}Aqui ira la imagen promocional de TVWIZ{% endif %}</div><h1>Solicitar acceso</h1>
<p>Sigue estos pasos. Tu codigo y el progreso se guardan en este telefono para que puedas volver si se cierra la pagina.</p><p id="resume" class="resume" role="status"></p>
<section id="step1" class="step"><div class="step-count">Paso 1 de 3</div><h2>Ingresa tu codigo</h2><p>Escribe el codigo de solicitud de 6 caracteres que muestra la app.</p><label class="small" for="manual">Codigo de solicitud</label><input id="manual" maxlength="6" autocomplete="off" autocapitalize="characters" placeholder="6 caracteres" aria-label="Codigo de solicitud"><button id="save-code">Guardar y continuar</button><p id="code-status" class="small" role="status"></p></section>
<section id="step2" class="step" hidden><div class="step-count">Paso 2 de 3</div><h2>Comparte el flyer</h2><p>Publica la imagen promocional en tu estado de WhatsApp. El enlace para solicitar la activacion ira junto con la imagen.</p><button id="share">Compartir flyer</button><p class="small">Cuando regreses, toca el boton de abajo para continuar. Tu codigo ya esta guardado.</p><button id="shared" class="secondary">Ya lo comparti, continuar</button></section>
<section id="step3" class="step" hidden><div class="step-count">Paso 3 de 3</div><h2>Notifica para activar</h2><p>Se abrira WhatsApp con tu codigo listo para enviar al gestor.</p><p id="result" class="code" aria-live="polite"></p><a id="notify" class="btn" href="#" aria-disabled="true">Notificar por WhatsApp</a><div class="actions"><button id="restart" class="secondary">Empezar otra solicitud</button></div></section>
</section></main>
<script>
const STORAGE_KEY='tvwiz-renewal-v1',manual=document.querySelector('#manual'),codeStatus=document.querySelector('#code-status'),resumeText=document.querySelector('#resume'),result=document.querySelector('#result'),notifyLink=document.querySelector('#notify'),shareButton=document.querySelector('#share');
const whatsappNumber={{ whatsapp_number|tojson }};let requestCode='',currentStep=1;
function validCode(value){return /^[A-Z0-9]{6}$/.test(String(value||'').trim().toUpperCase())}
function saveState(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify({code:requestCode,step:currentStep,updated:Date.now()}));resumeText.textContent='Progreso guardado en este telefono.';return true}catch(e){resumeText.textContent='No se pudo guardar en este navegador. Manten esta pagina abierta hasta terminar.';return false}}
function configureNotification(){result.textContent=requestCode;if(whatsappNumber){const msg=encodeURIComponent('Hola, solicito activar la app TVWIZ. Codigo de solicitud: '+requestCode);notifyLink.href='https://wa.me/'+whatsappNumber+'?text='+msg;notifyLink.setAttribute('aria-disabled','false')}else{notifyLink.href='#';notifyLink.setAttribute('aria-disabled','true')}}
function showStep(step){currentStep=step;document.querySelectorAll('.step').forEach((el,i)=>{el.hidden=i+1!==step});if(requestCode)configureNotification();saveState()}
function loadState(){try{const saved=JSON.parse(localStorage.getItem(STORAGE_KEY)||'null');if(saved&&validCode(saved.code)){requestCode=saved.code.toUpperCase();manual.value=requestCode;currentStep=Math.min(3,Math.max(1,Number(saved.step)||1));resumeText.textContent='Encontre tu codigo guardado. Continua desde el paso '+currentStep+'.';showStep(currentStep)}}catch(e){try{localStorage.removeItem(STORAGE_KEY)}catch(_){}}}
manual.addEventListener('input',()=>{manual.value=manual.value.toUpperCase().replace(/[^A-Z0-9]/g,'').slice(0,6)});
document.querySelector('#save-code').addEventListener('click',()=>{const code=manual.value.trim().toUpperCase();if(!validCode(code)){codeStatus.textContent='El codigo debe tener 6 letras o numeros.';codeStatus.className='small error';return}requestCode=code;showStep(2)});
shareButton.addEventListener('click',async()=>{if(!requestCode)return;const image=document.querySelector('.promo img');const whatsappUrl=whatsappNumber?'https://wa.me/'+whatsappNumber+'?text='+encodeURIComponent('Hola, solicito activar la app TVWIZ. Codigo de solicitud: '+requestCode):location.href;const data={title:'Promocion TVWIZ',text:'Solicita tu acceso a TVWIZ por WhatsApp: '+whatsappUrl,url:whatsappUrl};try{if(image?.src&&navigator.canShare&&navigator.share){const response=await fetch(image.src);const blob=await response.blob();const file=new File([blob],'promocion-tvwiz.'+(blob.type.split('/')[1]||'jpg'),{type:blob.type||'image/jpeg'});if(navigator.canShare({files:[file]})){await navigator.share({title:data.title,text:data.text,files:[file]});return}}if(navigator.share){await navigator.share(data)}else{await navigator.clipboard.writeText(data.text);codeStatus.textContent='Enlace de WhatsApp copiado. Comparte el flyer y luego vuelve aqui.';codeStatus.className='small ok'}}catch(e){if(e.name!=='AbortError'){codeStatus.textContent='No se pudo abrir el menu para compartir. Puedes guardar la imagen y publicarla manualmente.';codeStatus.className='small error'}}});
document.querySelector('#shared').addEventListener('click',()=>showStep(3));
document.querySelector('#restart').addEventListener('click',()=>{requestCode='';manual.value='';try{localStorage.removeItem(STORAGE_KEY)}catch(e){}resumeText.textContent='';codeStatus.textContent='';showStep(1)});
loadState();
</script></body></html>"""

@app.get("/healthz")
def healthz():
    return jsonify(status="ok")

@app.get("/")
def index():
    whatsapp = re.sub(r"\D", "", os.environ.get("WHATSAPP_NUMBER", ""))
    return render_template_string(PAGE, whatsapp_number=whatsapp, logo=os.environ.get("LOGO_IMAGE_URL", "/static/tvwiz-logo.png"), promo=os.environ.get("PROMO_IMAGE_URL") or "/static/tvwiz-flyer.jpg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")), debug=False)

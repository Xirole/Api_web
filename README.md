# Renovaciones TOWIZ

Página ligera para leer el código QR de solicitud de TOWIZ, compartir la promoción y avisar al gestor por WhatsApp. La activación se calcula localmente con el generador privado de Python y se verifica dentro de la app; este sitio no valida códigos ni guarda datos de clientes.

## Flujo

1. La app muestra un código de solicitud de 6 caracteres y un QR con el contenido `TOWIZ:<código>`.
2. El cliente abre esta página desde otro teléfono, pulsa **Escanear QR** y concede permiso a la cámara. Si el navegador no admite el lector, puede escribir el código manualmente.
3. La página muestra la promoción y habilita **Compartir promoción** y **Notificar por WhatsApp**.
4. WhatsApp prepara un mensaje al gestor con el código de solicitud.
5. El gestor usa su copia privada de `generar_codigo_activacion.py` para crear el código de activación de 6 caracteres. El cliente lo ingresa en la app; la app lo valida sin internet y comienza los 10 días.

El endpoint `GET /qr/<código>.png` devuelve el QR para la app. No hay PostgreSQL, SQLite, archivos JSON de clientes, panel de administración ni almacenamiento de solicitudes en este servicio.

## Despliegue en Render

El repositorio puede conectarse como Web Service con el Blueprint `render.yaml`. El servicio no necesita base de datos ni secretos de sesión. En **Environment** configura:

- `WHATSAPP_NUMBER`: número del gestor en formato internacional, sin `+` ni espacios (por ejemplo, `549...`).
- `PROMO_IMAGE_URL`: opcional; URL HTTPS de la imagen promocional.
- `LOGO_IMAGE_URL`: opcional; URL HTTPS del logo. Si se omite, usa `static/towiz-logo.png`.

El lector de cámara requiere que la página se sirva por HTTPS, como la dirección `https://...onrender.com`.

## Ejecutar localmente

```powershell
python -m pip install -r requirements.txt
$env:WHATSAPP_NUMBER = "549XXXXXXXXXX"
python app.py
```

Abre `http://127.0.0.1:10000` para revisar la página. Los navegadores normalmente solo permiten usar la cámara en HTTPS o en `localhost`.

## Rutas

- `GET /` — lector QR, promoción y enlace de WhatsApp.
- `GET /qr/<código>.png` — genera un QR con `TOWIZ:<código>`.
- `GET /healthz` — estado del servicio para Render.

## Seguridad y límites del modo offline

El generador Python contiene la misma clave local que la APK: no publiques ni compartas ese archivo. Como la app valida sin servidor, un análisis del APK puede extraer la clave y el reloj del teléfono puede alterarse. Este mecanismo funciona como bloqueo básico, no como control de acceso resistente a manipulación. La página no recibe ni necesita esa clave.

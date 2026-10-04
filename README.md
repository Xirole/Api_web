# TVWIZ

Página ligera de TVWIZ para leer el código QR de solicitud, compartir la imagen promocional en el estado de WhatsApp y avisar al gestor. La activación se calcula localmente con el generador privado de Python y se verifica dentro de la app; este sitio no valida códigos ni guarda datos de clientes.

## Flujo

1. La app muestra un código de solicitud de 6 caracteres y pide su QR a este servicio (`/qr/<código>.png`), que apunta a esta página con el código ya cargado (`.../?code=<código>`).
2. El cliente escanea el QR con otro teléfono: la página se abre con el código listo y pasa al paso 2. También puede escribir el código a mano.
3. La página indica que primero se comparta la imagen promocional en el estado de WhatsApp. El botón **Compartir flyer** abre el menú de compartir; cuando hay una imagen configurada, intenta compartir el archivo directamente.
4. WhatsApp prepara un mensaje al gestor con el código de solicitud.
5. El gestor usa su copia privada de `generar_codigo_activacion.py` para crear el código de activación de 6 caracteres. El cliente lo ingresa en la app; la app lo valida sin internet y comienza los 10 días.

El endpoint `GET /qr/<código>.png` devuelve el QR para la app (con el enlace a esta página y el código de solicitud) y la página incluye un botón **Descargar app** que apunta a la APK publicada en este repositorio. No hay PostgreSQL, SQLite, archivos JSON de clientes, panel de administración ni almacenamiento de solicitudes en este servicio.

## Despliegue en Render

El repositorio puede conectarse como Web Service con el Blueprint `render.yaml`. El servicio no necesita base de datos ni secretos de sesión. En **Environment** configura:

- `WHATSAPP_NUMBER`: número del gestor en formato internacional, sin `+` ni espacios (por ejemplo, `549...`).
- `PROMO_IMAGE_URL`: opcional; URL HTTPS de la imagen promocional. Cuando se configura, la página muestra la imagen e intenta adjuntarla al menú de compartir del teléfono.
- `LOGO_IMAGE_URL`: opcional; URL HTTPS del logo. Si se omite, muestra el nombre TVWIZ.
- `APK_URL`: opcional; enlace de descarga de la APK. Por defecto apunta al archivo `TVWIZ.apk` de este repositorio servido por GitHub raw.

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
- `GET /qr/<código>.png` — genera un QR que abre esta página con el código de solicitud ya cargado.
- `GET /healthz` — estado del servicio para Render.

## Seguridad y límites del modo offline

El generador Python contiene la misma clave local que la APK: no publiques ni compartas ese archivo. Como la app valida sin servidor, un análisis del APK puede extraer la clave y el reloj del teléfono puede alterarse. Este mecanismo funciona como bloqueo básico, no como control de acceso resistente a manipulación. La página no recibe ni necesita esa clave.

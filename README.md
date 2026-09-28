# Renovaciones TOWIZ

Servicio web para las solicitudes de renovación por WhatsApp y códigos de activación de un solo uso.

## Flujo preparado

1. La app obtiene un identificador estable del dispositivo y consulta `/api/status/<device>`.
2. Si no tiene una activación vigente, muestra el QR servido por `/qr/<device>.png`.
3. El cliente escanea el QR. El enlace abre una página TOWIZ que deja compartir la promoción o iniciar un WhatsApp al gestor con el identificador del cliente.
4. El gestor abre `/admin`, pega ese identificador y genera un código de ocho dígitos. El código vence en 30 minutos y solo sirve una vez.
5. La app envía el identificador y el código a `POST /api/redeem`. Si es correcto, el servidor habilita ese dispositivo durante 10 días.
6. El QR incluye una firma del servidor para el período actual de 10 días. Al comenzar otro período, el QR anterior vence automáticamente.

La pantalla de la app todavía debe integrarse con estos endpoints y con la URL pública que Render asigne al servicio. Este servicio por sí solo no coloca el bloqueo en el APK.

## Ejecutar en Render

1. Sube esta carpeta a un repositorio Git y crea un Web Service de Render conectado a ese repositorio, o usa el Blueprint `render.yaml`.
2. Crea y vincula una base PostgreSQL persistente; carga su `DATABASE_URL` como variable secreta del servicio. La base es necesaria para conservar activaciones y códigos entre reinicios.
3. Define `ADMIN_PASSWORD` y `CODE_PEPPER` con valores aleatorios largos. Render genera `SESSION_SECRET` desde el Blueprint.
4. Render asigna una dirección `https://...onrender.com`; el servicio la detecta para crear los QR. Envíame esa dirección para conectarla al APK.
5. Configura `WHATSAPP_NUMBER` en Render con el número autorizado, en formato internacional y sin `+` (por ejemplo, un móvil argentino comienza con `549`).
6. La página ya incluye el logo TOWIZ. Para añadir la imagen promocional después, publícala y configura `PROMO_IMAGE_URL` con su URL HTTPS.

El Blueprint deja el servicio web en plan gratuito para una prueba. No adjunta una base gratuita que caduque ni una base local efímera: sin configurar PostgreSQL persistente, no se considera listo para operar. El plan gratuito de servicios puede suspenderse cuando consume sus horas mensuales; comprueba los límites vigentes de Render antes de usarlo con clientes.

## Endpoints

- `GET /healthz` — estado del servicio.
- `GET /qr/<device>.png` — QR firmado que abre la solicitud de ese dispositivo.
- `GET /app/<device>` — página web de bloqueo con QR y campo para canjear el código; falta conectarla desde el APK.
- `GET /renew?d=<device>&e=<period>&s=<signature>` — promoción, compartir y WhatsApp.
- `GET /api/status/<device>` — indica si la activación sigue vigente.
- `POST /api/redeem` — recibe `{"device":"…","code":"12345678"}` y consume el código.
- `/admin` — acceso del gestor y emisión de códigos.

Para probar localmente, instala `requirements.txt`, configura las variables de `.env.example` en el entorno y ejecuta `python app.py`. La app crea SQLite local solo para desarrollo. En Render debe usarse PostgreSQL.


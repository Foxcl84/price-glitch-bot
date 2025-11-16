import requests
from bs4 import BeautifulSoup
import time
from telegram import Bot
from telegram.constants import ParseMode
import threading
from flask import Flask

# ======================================================
# CONFIGURACIÓN DEL BOT
# ======================================================

TOKEN = "AQUI_TU_TOKEN"
CHAT_ID = "AQUI_TU_CHAT_ID"

bot = Bot(token=TOKEN)

# ======================================================
# TIENDAS RETAIL
# ======================================================

TIENDAS = [
    {
        "nombre": "Falabella",
        "categorias": [
            "https://www.falabella.com/falabella-cl/category/cat2550004/tecnologia",
            "https://www.falabella.com/falabella-cl/category/cat2549004/electrohogar",
            "https://www.falabella.com/falabella-cl/category/cat70008/mujer",
            "https://www.falabella.com/falabella-cl/category/cat70027/hombre",
            "https://www.falabella.com/falabella-cl/category/cat70010/zapatos-y-zapatillas-mujer",
        ],
        "selector_item": ".pod-product",
        "selector_precio": ".copy10.primary.medium.jsx-3451234166",
        "selector_normal": ".copy10.strike.medium.jsx-3451234166",
        "prefijo": "https://www.falabella.com"
    },
    {
        "nombre": "Paris",
        "categorias": [
            "https://www.paris.cl/c/tecnologia/",
            "https://www.paris.cl/c/electrohogar/",
            "https://www.paris.cl/c/moda-mujer/",
            "https://www.paris.cl/c/moda-hombre/",
            "https://www.paris.cl/c/calzado/"
        ],
        "selector_item": ".vtex-product-summary-2-x-container",
        "selector_precio": ".parox-price-1-x-sellingPrice",
        "selector_normal": ".parox-price-1-x-listPrice",
        "prefijo": "https://www.paris.cl"
    },
    {
        "nombre": "Ripley",
        "categorias": [
            "https://simple.ripley.cl/tecnologia",
            "https://simple.ripley.cl/electro",
            "https://simple.ripley.cl/moda-mujer",
            "https://simple.ripley.cl/moda-hombre",
            "https://simple.ripley.cl/calzado"
        ],
        "selector_item": ".catalog-product-item",
        "selector_precio": ".catalog-product-details__price",
        "selector_normal": ".catalog-product-details__list-price",
        "prefijo": "https://simple.ripley.cl"
    }
]

# ======================================================
# OFERTAS DE VIAJES
# ======================================================

VIAJES = [
    {
        "nombre": "LATAM",
        "url": "https://www.latamairlines.com/cl/es/ofertas",
        "selector_item": ".offer-card",
        "selector_precio": ".offer-card__price"
    },
    {
        "nombre": "Sky Airlines",
        "url": "https://www.skyairline.com/chile/es/ofertas",
        "selector_item": ".offer",
        "selector_precio": ".price"
    },
    {
        "nombre": "JetSmart",
        "url": "https://jetsmart.com/cl/es/ofertas",
        "selector_item": ".promo-offer",
        "selector_precio": ".promo-offer__price"
    },
    {
        "nombre": "Cocha",
        "url": "https://www.cocha.com/ofertas",
        "selector_item": ".col-md-3.col-sm-6.col-xs-6",
        "selector_precio": ".price"
    }
]

# ======================================================
# FUNCIONES DEL BOT
# ======================================================

enviados = set()

def limpiar_precio(texto):
    if not texto:
        return None
    texto = texto.replace("$", "").replace(".", "").replace(",", "").strip()
    return int(texto) if texto.isdigit() else None

def escanear_categoria(url, tienda):
    try:
        html = requests.get(url, timeout=15).text
        soup = BeautifulSoup(html, "lxml")
        items = soup.select(tienda["selector_item"])

        resultados = []

        for item in items:
            precio_txt = item.select_one(tienda["selector_precio"])
            normal_txt = item.select_one(tienda["selector_normal"])

            precio = limpiar_precio(precio_txt.text if precio_txt else None)
            precio_normal = limpiar_precio(normal_txt.text if normal_txt else None)

            if not precio or not precio_normal:
                continue

            descuento = 1 - (precio / precio_normal)

            if precio == 0 or descuento >= 0.70:
                link_tag = item.find("a", href=True)
                link = tienda["prefijo"] + link_tag["href"] if link_tag else url
                nombre = item.text.strip().split("\n")[0][:80]

                resultados.append({
                    "nombre": nombre,
                    "precio": precio,
                    "precio_normal": precio_normal,
                    "url": link,
                    "tienda": tienda["nombre"]
                })

        return resultados

    except Exception:
        return []

def escanear_viajes():
    resultados = []

    for site in VIAJES:
        try:
            html = requests.get(site["url"], timeout=10).text
            soup = BeautifulSoup(html, "lxml")
            items = soup.select(site["selector_item"])

            for item in items:
                precio_txt = item.select_one(site["selector_precio"])
                precio = limpiar_precio(precio_txt.text if precio_txt else None)

                if not precio or precio == 0:
                    continue

                if precio <= 30000:
                    nombre = site["nombre"]
                    resultados.append({
                        "nombre": f"Oferta viaje {nombre}",
                        "precio": precio,
                        "precio_normal": precio * 2,
                        "url": site["url"],
                        "tienda": nombre
                    })

        except Exception:
            continue

    return resultados

def enviar_alerta(prod):
    if prod["url"] in enviados:
        return

    msg = (
        f"🔥 *GLITCH / OFERTA FUERA DE RANGO* 🔥\n\n"
        f"*Tienda:* {prod['tienda']}\n"
        f"*Producto:* {prod['nombre']}\n"
        f"*Precio:* ${prod['precio']:,}\n"
        f"*Normal:* ${prod['precio_normal']:,}\n\n"
        f"[Ver aquí]({prod['url']})"
    )

    bot.send_message(
        chat_id=CHAT_ID,
        text=msg,
        parse_mode=ParseMode.MARKDOWN
    )

    enviados.add(prod["url"])

# ======================================================
# HILO PRINCIPAL DEL BOT (LOOP INFINITO)
# ======================================================

def iniciar_bot():
    print("BOT GLITCH+VIAJES corriendo...")
    while True:
        for tienda in TIENDAS:
            for categoria in tienda["categorias"]:
                glitches = escanear_categoria(categoria, tienda)
                for g in glitches:
                    enviar_alerta(g)
                time.sleep(3)

        ofertas = escanear_viajes()
        for o in ofertas:
            enviar_alerta(o)

        time.sleep(45)

# ======================================================
# SERVIDOR FAKE PARA QUE RENDER NO APAGUE EL BOT
# ======================================================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot price-glitch está corriendo correctamente (Render Free OK)."

def iniciar_servidor():
    app.run(host="0.0.0.0", port=10000)

# ======================================================
# LANZAR EL BOT Y EL SERVIDOR EN PARALELO
# ======================================================

threading.Thread(target=iniciar_bot).start()
threading.Thread(target=iniciar_servidor).start()


import os
import logging
import json
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic
import requests

# ============================================================
# CONFIGURACION
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
GOOGLE_SHEET_ID = "10lI_HXAQbLyxh8rDMzAkdb4RSopI31EiR_m_NJkIsEI"
FRESHDESK_API_KEY = os.environ.get("FRESHDESK_API_KEY")
FRESHDESK_DOMAIN = os.environ.get("FRESHDESK_DOMAIN")
FRESHDESK_GROUP_IDS = {
    "AYB Mingo": 154000227835,
    "Corporativo": 154000228071,
    "Euroking": 154000228066,
    "Eurollantas": 154000227857,
    "Novoretail": 154000227836,
}
# ============================================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar Google Sheets
def init_google_sheets():
    try:
        credentials_json = os.environ.get("GOOGLE_CREDENTIALS")
        if not credentials_json:
            logger.error("No se encontró GOOGLE_CREDENTIALS")
            return None
        credentials_dict = json.loads(credentials_json)
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        gc = gspread.authorize(credentials)
        sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1
        logger.info("✅ Google Sheets conectado correctamente")
        return sheet
    except Exception as e:
        logger.error(f"Error conectando Google Sheets: {e}")
        return None

def guardar_conversacion(sheet, usuario, chat_id, mensaje_usuario, respuesta_bot):
    try:
        if sheet is None:
            return
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        respuesta_limpia = respuesta_bot.replace("[IMAGEN:", "📸[").replace("[VIDEO:", "🎬[")
        sheet.append_row([fecha, usuario, str(chat_id), mensaje_usuario, respuesta_limpia])
    except Exception as e:
        logger.error(f"Error guardando en Google Sheets: {e}")

# Imagenes de Google Drive
IMAGENES = {
    "video_interfaz": "https://drive.google.com/uc?export=download&id=1_vPe5Hhy48gznape5L7NioYFE2CF9B3G",
    "tipo_pastillas": "https://drive.google.com/uc?export=view&id=1TxzgTuryuHhG5LMscxDq0QwQIimuqKRI",
    "tapon_fluxometro": "https://drive.google.com/uc?export=view&id=1qiL2Ay_XotCeSAFKFZpZElYzO-BI1FZ1",
    "sensor_llama_inferior": "https://drive.google.com/uc?export=view&id=1yy5Red3EGJEBJWeomAtMIMH5KvZMoD3q",
    "sapito_en_wc": "https://drive.google.com/uc?export=view&id=1MX7mlpKxpOXgUCzUsCORGR3s24XumKu3",
    "sapito_de_wc": "https://drive.google.com/uc?export=view&id=1dO6yUk8dAA570vxSQ1hsMxa3B74V57z6",
    "reguladores": "https://drive.google.com/uc?export=view&id=1hQUe3q_Z-ABlwH-tvtZ830Sf47YqZoQY",
    "quitar_tapa_sensores": "https://drive.google.com/uc?export=view&id=1z0Z0lZR065aZTlTMV5Ahn_j2zgJ7kNx4",
    "quitar_quemador_inferior": "https://drive.google.com/uc?export=view&id=1U8Y1Fyi6VY5XpWs_4Qn59-iOJRmVDOcz",
    "quemador_inferior": "https://drive.google.com/uc?export=view&id=1A-lxDhuV0k8gsFCaA-vMO9ClPJ60SD_O",
    "pastilla_scuard": "https://drive.google.com/uc?export=view&id=17MsRIemls-tjSbn192UvA3uKWmcwJE1J",
    "pastilla_abb": "https://drive.google.com/uc?export=view&id=1RUpPKHYbM0hjhNJKjvvarb_-lzDV9FaZ",
    "orientacion_valvula": "https://drive.google.com/uc?export=view&id=1lAY8WXtvh04bDc4zoAJFYr1l1f_nbEH5",
    "monitor_kiosko": "https://drive.google.com/uc?export=view&id=1hjrsi98XBZYNCCf_cuKWfjYGZrP9m7WW",
    "medidor_luz": "https://drive.google.com/uc?export=view&id=1-MxfRPLOBIwpQSaab1UxernJkCg4x179",
    "llave_paso_pequena": "https://drive.google.com/uc?export=view&id=1VpCXtnmsb0_iCrc2JpS-B3jtJfc7ukza",
    "limpieza_quemador": "https://drive.google.com/uc?export=view&id=1Pd9GKYDZobEmGVRUniE-mZy8lRTMTs3b",
    "fusibles_poste": "https://drive.google.com/uc?export=view&id=1_0oHNXm3q7beilJ33GquGIXF0khEMwaN",
    "fluxometro_pedal": "https://drive.google.com/uc?export=view&id=1iirAbgMvCMsw-fCHiW9HfaHd_vAyeAfv",
    "fluxometro_palanca": "https://drive.google.com/uc?export=view&id=1uv9Q3DR87SW2Ot5FpxAk0gQUR3DAs06i",
    "donde_tomar_sensores": "https://drive.google.com/uc?export=view&id=1B-LTsC0JHceORe2rrENiyZ-gs2V8OR6v",
    "botones_inicio_paro": "https://drive.google.com/uc?export=view&id=15m80wjZzYSKYXjHN9j_elZ7wjxM24VC1",
    "boton_paro_emergencia": "https://drive.google.com/uc?export=view&id=1R6BQ9KL5x64Wy5ycjRBu4ksBsVA5piBM",
    "ajuste_cadena_sapito": "https://drive.google.com/uc?export=view&id=1F1sj5cnzPR_U9QwNFz9F0BS_QzEFINFN",
    "tinaco": "https://drive.google.com/uc?export=view&id=1Vbcas3ycRQHIj2-InLyyBu5AFV67p-Z2",
    "manometro": "https://drive.google.com/uc?export=view&id=13Elexx6Osd0UUK1bGYB0v-7r9lo6GKB_",
    "bomba_presurizadora": "https://drive.google.com/uc?export=view&id=1MPcSGAE8X1gsmYAuX_CDCI7Xq8YOsX_T",
    "puntos_rojos_tanques": "https://drive.google.com/uc?export=view&id=1HAtVH8Q7zVWNLcqHLGdlrywdaUSylzSJ",
    # Imágenes aires acondicionados
    "abrir_tapa_minisplit": "https://drive.google.com/uc?export=view&id=1EOE2uUY8GhmY9mHkKQvVAusyrzRle-JG",
    "quitar_filtro_minisplit": "https://drive.google.com/uc?export=view&id=1I5q_smikIWFa9petgS8pwH_I8NLD_xXT",
    # Imágenes cambio de pistola surtidora
    "prueba_pico_3pulgadas": "https://drive.google.com/uc?export=view&id=1X8KODfjR1vWNBuiYURCjyn02dsmpIBU1",
    "escalerilla": "https://drive.google.com/uc?export=view&id=10PJfFvFdPKlZVW2R82gtdhNb36puVPvE",
    "apriete_pistola": "https://drive.google.com/uc?export=view&id=1n-meEmbZdnVL3tsnGRtTFGRYLh8FYEK2",
    "llave_tuercas_para_aflojar": "https://drive.google.com/uc?export=view&id=1rM-UjvrTq9ZG4Y3yUWggfEUkl3SjdE4G",
    "retirar_manguera": "https://drive.google.com/uc?export=view&id=1ksQWefdGv-mSuqs3lIdpTJ30wboi1FEH",
}

# Stickers de Mantestito
STICKERS = {
    "gracias": "CAACAgEAAxkBAAIJcmoLJbcGv-50L0Vxm95H9uwg_nBLAAI-BwACweNRRFl740NNdtzfOwQ",
    "empecemos": "CAACAgEAAxkBAAIJgGoLLImOIBLaOoy3KMMYeq-YTOmaAALRBwACs4BQRF-UdFeUjxYVOwQ",
    "llave_palomita": "CAACAgEAAxkBAAIJgmoLLIv30LnQZr5abp3kpGHw-SpvAAKoCAACWO5YRDJS_CGD65WKOwQ",
    "saludo_militar": "CAACAgEAAxkBAAIJhGoLLI37pagpPVjUTPGrmreVmi1IAAJBBwACtJJRRKSnj8jy3AJ7OwQ",
    "a_trabajar": "CAACAgEAAxkBAAIJd2oLJ-R7bB7tAuLp8lkuVw6fW4vrAAIbBwACBSlRRJ-kzNwe9d36OwQ",
}


# Stickers de Mantestito
STICKERS = {
    "empecemos": "CAACAgEAAxkBAAIJgGoLLImOIBLaOoy3KMMYeq-YTOmaAALRBwACs4BQRF-UdFeUjxYVOwQ",
    "a_trabajar": "CAACAgEAAxkBAAIJd2oLJ-R7bB7tAuLp8lkuVw6fW4vrAAIbBwACBSlRRJ-kzNwe9d36OwQ",
    "llave_palomita": "CAACAgEAAxkBAAIJgmoLLIv30LnQZr5abp3kpGHw-SpvAAKoCAACWO5YRDJS_CGD65WKOwQ",
    "gracias": "CAACAgEAAxkBAAIJcmoLJbcGv-50L0Vxm95H9uwg_nBLAAI-BwACweNRRFl740NNdtzfOwQ",
    "saludo_militar": "CAACAgEAAxkBAAIJhGoLLI37pagpPVjUTPGrmreVmi1IAAJBBwACtJJRRKSnj8jy3AJ7OwQ",
}


# ============================================================
# DATOS PARA INTEGRACIÓN CON FRESHDESK
# ============================================================

# Mapeo de unidades de negocio -> correo del gerente (requester del ticket)
UNIDADES_NEGOCIO = {
    "Corporativo": [
        ("Asistente Direccion", "asistentedireccion@grupoeuro.com.mx"),
        ("Gerente Sistemas", "gerente.sistemas@grupoeuro.com.mx"),
        ("Sanjuana Bautista", "coordinador.mantenimiento@grupoeuro.com.mx"),
        ("Seguridad e Higiene", "seguridadehigiene@grupoeuro.com.mx"),
    ],
    "Eurollantas": [
        ("Asistente Compras", "asistente.logistica@eurollantas.com.mx"),
        ("Erik García Rico", "gerencia.honda@motosdsanluis.mx"),
        ("Eurollantas Carranza", "gerencia.carranza@eurollantas.com.mx"),
        ("Eurollantas Zacatecas", "ventas.zacatecas@eurollantas.com.mx"),
        ("Eurollantas Muñoz", "gerencia.munoz@eurollantas.com.mx"),
        ("Eurollantas Glorieta", "gerencia.glorieta@eurollantas.com.mx"),
        ("Gerente Logistica", "gerente.logistica@eurollantas.com.mx"),
        ("Gerente Honda", "motosdsanluis@grupoeuro.com.mx"),
        ("Honda", "administracion@motosdsanluis.mx"),
        ("Importadora", "facturacion@importadoraeuro.com"),
    ],
    "Euroking": [
        ("BK ARAGON", "gerente.bkplazaaragon@grupoeuro.com.mx"),
        ("BK ATLIXCO", "gerente.bkatlixco@grupoeuro.com.mx"),
        ("BK PERINORTE", "gerente.bkgaleriasperinorte@grupoeuro.com.mx"),
        ("BK GALERIAS CUERNAVACA", "gerente.bkgaleriascuernavaca@grupoeuro.com.mx"),
        ("BK GALERIAS SERDAN", "gerente.bkgaleriasserdan@grupoeuro.com.mx"),
        ("BK GALERIAS ATIZAPAN", "gerente.bkatizapan@grupoeuro.com.mx"),
        ("BK GALERIAS TOLUCA", "gerente.bkgaleriastolloacan@grupoeuro.com.mx"),
        ("BK PATIO TOLUCA", "gerente.bkpatio@grupoeuro.com.mx"),
        ("BK PLAZA PLATINO", "gerente.bkplazaplatino@grupoeuro.com.mx"),
        ("BK PLAZA FORUM CUERNAVACA", "gerente.bkforum@grupoeuro.com.mx"),
        ("BK PUEBLA CENTRO", "gerente.bkcentropuebla@grupoeuro.com.mx"),
        ("BK SANTA FE", "gerente.bksantafe@grupoeuro.com.mx"),
        ("BK SANTIAGO TIANGUISTENGO", "gerente.bktianguistenco@grupoeuro.com.mx"),
        ("BK TOLUCA SENDERO", "gerente.bksenderofs@grupoeuro.com.mx"),
        ("BK TOLUCA I PLAZA LAS AMERICAS", "gerente.bkplazaamericas@grupoeuro.com.mx"),
        ("BK CUERNAVACA PLAN DE AYALA", "gerente.bkplandeayala@grupoeuro.com.mx"),
        ("BK TOLUCA II GALERIAS METEPEC", "gerente.bkgaleriasmetepec@grupoeuro.com.mx"),
        ("BK TOLUCA IV ALFREDO DEL MAZO", "gerente.bkalfredo@grupoeuro.com.mx"),
        ("BK TOLUCA SENDERO 2", "gerente.bksenderofc@grupoeuro.com.mx"),
        ("Burger King Pocaluz", "gerente.bkmatehuala1@grupoeuro.com.mx"),
        ("Burger King Citadella", "gerentebk.citadela@grupoeuro.com.mx"),
        ("Burger King Aerogas", "gerente.bkaerogas@grupoeuro.com.mx"),
        ("Burger King Tecnologico", "gerente.bktecnologico@grupoeuro.com.mx"),
        ("Burger King Citadina", "gerente.bkcitadina@grupoeuro.com.mx"),
        ("Burger King San Juan", "gerente.bkgaleriassanjuan@grupoeuro.com.mx"),
        ("Burger King del parque", "bkingplazadelparque@grupoeuro.com.mx"),
        ("Burger King Santa Maria", "bkingstamaria@grupoeuro.com.mx"),
        ("BK COLON", "gerente.bkcolontoluca@grupoeuro.com.mx"),
    ],
    "Novoretail": [
        ("Club KM Pocaluz", "gerente.ckpocaluz@grupoeuro.com.mx"),
        ("Club KM Hacienda 14", "gerente.ckh14@grupoeuro.com.mx"),
        ("Club Kilometro Hacienda", "regaderas.hacienda@grupoeuro.com.mx"),
        ("Club Kilometros Europits", "gerente.ckeuropits@grupoeuro.com.mx"),
        ("Distrital Novo Region Norte", "gerente.distritalnorte@grupoeuro.com.mx"),
        ("Gerente distrital Matehuala", "gerentedist.matehuala@grupoeuro.com.mx"),
        ("Max Store Hacienda", "gerente.maxsta2@grupoeuro.com.mx"),
        ("Max Store Europits", "gerente.maxeuropits@grupoeuro.com.mx"),
        ("Max Store Aerogas", "gerente.maxaerogas@grupoeuro.com.mx"),
        ("Max Store Eurogas", "gerente.maxeurogas@grupoeuro.com.mx"),
        ("Max Store La Carreta", "max.lacarreta@grupoeuro.com.mx"),
        ("Max Store Santa Maria", "gerente.maxsta1@grupoeuro.com.mx"),
        ("Patio Troje Santa Maria", "gerente.latroje@grupoeuro.com.mx"),
        ("Super All", "gerente.superall@grupoeuro.com.mx"),
    ],
    "AYB Mingo": [
        ("Hogazza", "gerente.hogazza@grupoeuro.com.mx"),
        ("Hojaldre", "gerente.hojaldre@grupoeuro.com.mx"),
        ("MINGO Carranza", "mingo@grupoeuro.com.mx"),
        ("MINGO Dorado", "italian.dorado@grupoeuro.com.mx"),
        ("MINGO Citadina", "gerenteic.citadina@grupoeuro.com.mx"),
        ("MINGO Aerogas", "fact.italiancoffee.aerogas@grupoeuro.com.mx"),
        ("MINGO Eurogas", "fact.italian.eurogas@grupoeuro.com.mx"),
        ("MINGO La Hacienda", "fact.italiancoffee.santamaria2@grupoeuro.com.mx"),
        ("MINGO Santa Maria", "italianc.santamaria@grupoeuro.com.mx"),
        ("SUBWAY", "gerencia.subway1@grupoeuro.com.mx"),
        ("The Italian Coffee Europits", "italiancoffee.europits@grupoeuro.com.mx"),
        ("The Italian Coffee Sendero", "italiancoffeeslp@grupoeuro.com.mx"),
    ],
}

# Opciones del campo "Type" (Equipo/Instalación) - solo aplica para Euroking
EQUIPO_TYPES_EUROKING = [
    "PHU", "Aire acondicionado", "Calentador", "Sistema filtrado (agua purificada)",
    "Cuna de papa", "Trampas de grasas", "Hornos", "Tostadores", "Maquina hielos",
    "Hidroneumatico", "Wc mingitorios", "Broiler", "Freidoras", "Taylor", "Camaras",
    "Portatiles", "Extraccion", "Desazolve (drenaje)", "Luminarias", "Area de juegos",
    "Extractor de baños", "Electricidad", "Secadores baños", "Fluxometros", "Tarjas",
    "Tableros Electricos", "Mezcladoras", "Chapas", "Contactos Electricos", "Lavamanos",
    "Candados", "Anuncios luminosos", "Edificio", "Cortinas", "Espectaculares", "Mesas sillas",
    "Pintura", "Plafones",
]

# Prioridades disponibles para familias distintas a Euroking
PRIORIDADES_FRESHDESK = {
    "urgente": 4,
    "alta": 3,
    "media": 2,
    "baja": 1,
}


def buscar_correo_unidad(familia, unidad_negocio):
    """Busca el correo del gerente según familia y unidad de negocio (texto libre).
    Devuelve (nombre_oficial, correo) o (None, None) si no encuentra coincidencia razonable."""
    if familia not in UNIDADES_NEGOCIO:
        return None, None

    unidad_lower = unidad_negocio.lower().strip()
    candidatos = UNIDADES_NEGOCIO[familia]

    # Coincidencia exacta primero
    for nombre, correo in candidatos:
        if nombre.lower() == unidad_lower:
            return nombre, correo

    # Coincidencia parcial (contiene)
    for nombre, correo in candidatos:
        if unidad_lower in nombre.lower() or nombre.lower() in unidad_lower:
            return nombre, correo

    # Coincidencia por palabras clave significativas (ignora BK/Burger King/Max Store etc.)
    import re as _re
    stop_words = {"burger", "king", "bk", "max", "store", "club", "km", "kilometro",
                  "kilometros", "eurollantas", "mingo", "italian", "coffee", "the", "de",
                  "la", "el", "los", "las", "y", "e"}
    palabras_busqueda = set(_re.findall(r'[a-záéíóúüñ]+', unidad_lower)) - stop_words

    mejor_match = None
    mejor_score = 0
    for nombre, correo in candidatos:
        palabras_nombre = set(_re.findall(r'[a-záéíóúüñ]+', nombre.lower())) - stop_words
        if not palabras_busqueda or not palabras_nombre:
            continue
        coincidencias = palabras_busqueda & palabras_nombre
        score = len(coincidencias) / max(len(palabras_busqueda), len(palabras_nombre))
        if score > mejor_score:
            mejor_score = score
            mejor_match = (nombre, correo)

    if mejor_match and mejor_score >= 0.4:
        return mejor_match

    # Fallback para Corporativo: si no se encontró coincidencia, usar Asistente Dirección
    if familia == "Corporativo":
        return "Asistente Direccion", "asistentedireccion@grupoeuro.com.mx"

    return None, None


def crear_ticket_freshdesk(email_solicitante, familia, unidad_negocio, asunto, descripcion, prioridad=None, equipo_type=None, foto_bytes=None):
    """Crea un ticket en Freshdesk vía API. Devuelve (exito, id_ticket_o_error).
    Si foto_bytes está presente, adjunta la imagen al ticket vía multipart/form-data."""
    if not FRESHDESK_API_KEY or not FRESHDESK_DOMAIN:
        logger.error("Freshdesk no configurado (falta API key o domain)")
        return False, "Freshdesk no está configurado"

    url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets"

    data = {
        "email": email_solicitante,
        "subject": asunto,
        "description": descripcion,
        "status": "2",  # Open
    }

    if familia in FRESHDESK_GROUP_IDS:
        data["group_id"] = str(FRESHDESK_GROUP_IDS[familia])

    if familia == "Euroking" and equipo_type:
        # Freshdesk asigna prioridad automáticamente según el Type/Equipo
        data["type"] = equipo_type
    elif prioridad:
        data["priority"] = str(PRIORIDADES_FRESHDESK.get(prioridad.lower(), 2))
    else:
        data["priority"] = "2"  # Media por defecto

    try:
        if foto_bytes:
            # Con foto: multipart/form-data (todos los campos como strings)
            form_data = {
                "email": email_solicitante,
                "subject": asunto,
                "description": descripcion,
                "status": "2",
            }
            if familia in FRESHDESK_GROUP_IDS:
                form_data["group_id"] = str(FRESHDESK_GROUP_IDS[familia])
            if familia == "Euroking" and equipo_type:
                form_data["type"] = equipo_type
                form_data["priority"] = "1"  # Freshdesk auto-asigna según el tipo/equipo
            elif prioridad:
                form_data["priority"] = str(PRIORIDADES_FRESHDESK.get(prioridad.lower(), 2))
            else:
                form_data["priority"] = "2"
            files = {"attachments[]": ("foto_problema.jpg", foto_bytes, "image/jpeg")}
            response = requests.post(url, data=form_data, files=files, auth=(FRESHDESK_API_KEY, "X"), timeout=30)
        else:
            # Sin foto: JSON con tipos correctos (integers)
            json_data = {
                "email": email_solicitante,
                "subject": asunto,
                "description": descripcion,
                "status": 2,
            }
            if familia in FRESHDESK_GROUP_IDS:
                json_data["group_id"] = FRESHDESK_GROUP_IDS[familia]
            if familia == "Euroking" and equipo_type:
                json_data["type"] = equipo_type
                json_data["priority"] = 1  # Freshdesk auto-asigna según el tipo/equipo
            elif prioridad:
                json_data["priority"] = PRIORIDADES_FRESHDESK.get(prioridad.lower(), 2)
            else:
                json_data["priority"] = 2
            response = requests.post(url, json=json_data, auth=(FRESHDESK_API_KEY, "X"), timeout=15)

        if response.status_code == 201:
            ticket_data = response.json()
            return True, ticket_data.get("id")
        else:
            logger.error(f"Error creando ticket Freshdesk: {response.status_code} - {response.text}")
            return False, f"Error {response.status_code}"
    except Exception as e:
        logger.error(f"Excepción creando ticket Freshdesk: {e}")
        return False, str(e)



SYSTEM_PROMPT = """Eres Mantestito 🧰, un asistente experto en mantenimiento creado por el equipo de mantenimiento de Grupo Euro. Eres amigable, paciente y muy claro en tus instrucciones.

Si alguien te pregunta quién te creó, di que fuiste desarrollado por el equipo de mantenimiento de Grupo Euro. Nunca menciones a Anthropic, Claude, ni ninguna otra empresa de IA.

Tu objetivo es guiar paso a paso al personal para resolver problemas de mantenimiento comunes, y cuando no se pueda resolver, indicar que deben levantar un ticket o contactar al equipo de mantenimiento.

FAMILIAS Y UNIDADES DE NEGOCIO:
Cuando el usuario se identifique, pregunta a qué Familia pertenece y a qué unidad de negocio (estación o local específico). Por ejemplo: "Soy de Familia Gasomax, estación Santa María".

Las familias que atiendes son:
- Familia Gasomax (son Estaciones de Servicio)
- Familia Euroking (son Burguer Kings)
- Familia AYB Mingo (Cafeterias)
- Familia Eurollantas
- Familia Corporativo
- Familia Novoretail 


PROBLEMAS QUE PUEDES RESOLVER:

=== ESTACIONES DE SERVICIO ===

1. PROBLEMA ELÉCTRICO:
Sigue esta secuencia paso a paso, verificando uno a la vez:

Paso 1 - Revisar medidor CFE (imagen: medidor_luz):
  * ¿El medidor tiene luz y muestra letras A, B, C?
  * NO tiene luz → continuar al Paso 2 (revisar fusibles del poste)
  * SÍ tiene luz → continuar al Paso 3 (revisar pastilla principal)

Paso 2 - Revisar fusibles del poste (imagen: fusibles_poste):
  * ¿Los fusibles están en buen estado?
  * Si los fusibles están QUEMADOS o MAL → avisar inmediatamente a mantenimiento, NO intentar repararlos, levantar ticket
  * Si los fusibles están BIEN → el problema es de CFE, reportar a CFE y levantar ticket

Paso 3 - Revisar pastilla principal (ubicada cerca del medidor o en el mismo poste):
  * Esta es una pastilla termomagnética principal (puede ser ABB, Siemens, Square D u otra marca)
  * ¿Está en posición correcta (ON) o hay alguna en falla (a la mitad o con ventana roja)?
  * Si está en falla: apagar OFF, esperar 10 seg, encender ON
  * ¿Se resolvió? → Sí: ¡Resuelto! / No: continuar al Paso 4

Paso 4 - Revisar interruptores en cuarto eléctrico (imagen: tipo_pastillas o pastilla_abb):
  * Verificar si alguno está a la mitad o con ventana roja
  * Si hay pastilla en falla: apagar OFF, esperar 10 seg, encender ON
  * ¿Se resolvió? → Sí: ¡Resuelto! / No: levantar ticket al departamento correspondiente

2. PROBLEMA DE DESPACHO DE COMBUSTIBLE:
Primero identificar si el problema es en TODOS los dispensarios o solo en UNO:

CASO A - DISPENSARIOS APAGADOS (todos o varios sin energía):
Sigue esta secuencia paso a paso:

Paso 1 - Revisar pastillas individuales en cuarto eléctrico (imagen: tipo_pastillas o pastilla_abb):
  * ¿Hay alguna pastilla individual de dispensario en falla (a la mitad o con ventana roja)?
  * Si hay falla: apagar OFF, esperar 10 seg, encender ON
  * Si todo está bien → continuar al Paso 2

Paso 2 - Revisar botones de paro de emergencia (imagen: boton_paro_emergencia):
  * ¿Algún botón de paro de emergencia está presionado (hundido)?
  * Si está presionado: jalar hacia afuera para desactivarlo
  * ¿Se resolvió? → Sí: ¡Resuelto! / No: continuar al Paso 3

Paso 3 - Reiniciar con pastilla principal ABB o botón verde/start:
  * Algunas estaciones tienen una pastilla principal ABB en el tablero que controla todos los dispensarios
  * Buscarla en el cuarto eléctrico (imagen: pastilla_abb): apagar OFF, esperar 10 seg, encender ON
  * Si hay botón verde o START: presionarlo para reiniciar (imagen: botones_inicio_paro)
  * ¿Se resolvió? → Sí: ¡Resuelto! / No: continuar al Paso 4

Paso 4 - Revisar reguladores (imagen: reguladores):
  * El regulador controla la energía de TODOS los dispensarios
  * ¿Está encendido? ¿Hay humo o olor a quemado?
  * Si está apagado o con falla: reportar inmediatamente a mantenimiento para reemplazo, levantar ticket
  * Si está bien → levantar ticket, posible problema más profundo

CASO B - DISPENSARIO QUE NO DESPACHA (enciende pero no surte):
  * Revisar monitor de kiosko (imagen: monitor_kiosko): no deben aparecer círculos rojos
  * Si hay círculos rojos en monitor:
    1. Identificar qué dispensario tiene el problema
    2. Ir al cuarto eléctrico y apagar/encender la pastilla individual de ese dispensario (esperar 5 min)
    3. Si persiste: revisar interfaz con video de referencia (video: video_interfaz)
  * Si pantalla hace barrido de ceros pero no despacha: posible problema de motobombas sumergibles, levantar ticket
  * Si sigue sin despachar: posiblemente desprogramados, contactar mantenimiento o ES soft y sistemas
  * IMPORTANTE: NO usar el paro de emergencia general salvo emergencia real

3. CONSOLA DE MONITOREO DE TANQUES:

TIPOS DE CONSOLA:
Primero identificar qué tipo de consola tiene el usuario:
- Pregunta: "¿Tu consola es TLS 350 o TLS 450?"
- Si no sabe: "¿De qué color es tu consola?"
  * Color NEGRO → TLS 450
  * Cualquier otro color (beige, crema, blanca, amarilla, etc.) → TLS 350

TIPOS DE SENSORES Y ALARMAS:
Es muy importante identificar el prefijo de la alarma:
- Prefijo T (ejemplo: T3 Sensor inoperativo) → Sonda de NIVEL del tanque
- Prefijo L (ejemplo: L12 Alarma combustible) → Sensor de LÍQUIDOS

ALARMAS CON PREFIJO T (Sonda de nivel):
- El usuario NO puede sacar la sonda de nivel bajo ninguna circunstancia
  * Sacarla puede afectar el inventario de combustible o descalibrarla
  * Algunas tienen cincho de seguridad metálico, tampoco pueden quitarlo
- Lo único que puede hacer el usuario es:
  * Revisar en la BOCATOMA del tanque con el error si el cable de comunicación está roto, dañado o desconectado
  * Revisar en la tirilla de inventario si aparece o no ese tanque
  * Verificar si existe un punto rojo en el monitor de tanques (imagen: puntos_rojos_tanques)
- Si el cable está roto/dañado o el problema persiste → levantar ticket a mantenimiento inmediatamente

ALARMAS CON PREFIJO L (Sensor de líquidos):
- Estos SÍ se pueden manipular con el procedimiento normal
- CRÍTICO - MANTÉN EL CONTEXTO: Cuando estés resolviendo una alarma L, si el usuario menciona
  palabras como "dispensario", "tanque", "motobomba" u otras ubicaciones, esto es ÚNICAMENTE
  la ubicación física del sensor. NO lo interpretes como un nuevo problema eléctrico o de despacho.
  Mantén el flujo de resolución del sensor L sin desviarte. Por ejemplo, si el usuario dice
  "es el dispensario 5", eso significa que el sensor L está ubicado en el dispensario 5,
  NO que tiene un problema de despacho de combustible.
- IMPORTANTE: La primera vez que aparece la alarma muestra la ubicación (ej: L12 Motobomba T2)
  Después de varios minutos solo muestra "L12 Alarma combustible" sin ubicación
- Si el usuario NO sabe la ubicación del sensor, según el tipo de consola:

  CONSOLA TLS 350 (color beige/crema/blanca/amarilla):
  1. Ir a la consola
  2. Oprimir botón FUNCTION hasta llegar a "Estatus de sensores de líquidos"
  3. Oprimir PRINT → imprimirá una tirilla con la ubicación de todos los sensores
     Ejemplo de tirilla: L1 Dispensario 1 Normal / L12 Motobomba T2 Alarma combustible
     (Las etiquetas y números varían según la configuración de cada estación)
  4. Oprimir botón MODE hasta que aparezca la pantalla de fecha y hora para salir del menú

  CONSOLA TLS 450 (color negro):
  1. Tocar la pantalla en la parte superior izquierda
  2. Ahí aparece directamente la descripción y ubicación de las alarmas

- Una vez identificada la ubicación del sensor, seguir el procedimiento normal:
  1. Localizar el sensor en la ubicación indicada
  2. Sacudirlo suavemente
  3. Colocarlo en posición vertical (no acostado)
  4. Esperar 10 minutos
  5. Ir a la consola y oprimir el botón rojo para resetear la alarma
  6. ¿Se quitó la alarma? → Sí: ¡Resuelto! / No: Levantar ticket a mantenimiento

PUNTOS ROJOS EN MONITOR:
- Identificar qué dispensario o tanque tiene el problema
- PRIMERO: Reiniciar por la pastilla individual del dispensario en el cuarto eléctrico (NO usar paro de emergencia general)
- Apagar pastilla → esperar 5 minutos → encender
- Si persiste: reportar a ES soft y sistemas
- Levantar ticket con el link correspondiente según la familia

CINCHO DE SEGURIDAD METÁLICO:
- Si el sensor tiene un cincho de seguridad metálico, el usuario NO debe intentar moverlo ni quitarlo
- Solo mantenimiento está autorizado para quitar el cincho
- En este caso: levantar ticket inmediatamente con el link correspondiente

4. CAMBIO DE PISTOLA SURTIDORA DE COMBUSTIBLE:
- Este procedimiento puede realizarlo personal capacitado de la estación con los cuidados adecuados
- Si en algún paso no se siente seguro o no puede continuar: levantar ticket a mantenimiento

MEDIDAS DE SEGURIDAD ANTES DE INICIAR:
  * Colocar conos de seguridad para delimitar el área de trabajo
  * Asegurarse de que el dispensario esté apagado desde la pastilla individual en el cuarto eléctrico
  * Tener a la mano: llave de tuercas, sellante de rosca o cinta de teflón, envase aprobado para combustible

RETIRO DE LA PISTOLA ANTIGUA:
  1. Confirmar que el dispensario esté apagado desde el cuarto eléctrico
  2. Con una llave de tuercas, girar la pistola para retirarla de la manguera (imagen: llave_tuercas_para_aflojar)
  3. Retirar la manguera de la pistola con cuidado (imagen: retirar_manguera)
  4. Vaciar el combustible que quede en la manguera y en la pistola vieja dentro de un envase aprobado
  5. Si es instalación nueva: purgar bien la punta de la manguera antes de instalar la pistola nueva

INSTALACIÓN DE LA PISTOLA NUEVA:
  1. Aplicar sellante de rosca en la rosca macho de la manguera o en la conexión roscada (destorcedor)
     * Si no hay sellante disponible: aplicar cinta de teflón como alternativa
  2. Insertar la manguera o conexión roscada en el orificio de entrada de la pistola nueva
  3. Apretar la pistola con la llave de tuercas: firme pero sin excederse para no dañar la rosca (imagen: apriete_pistola)

PRUEBAS DESPUÉS DE INSTALAR:

  PRUEBA DE CAUDAL:
  1. Encender el dispensario desde el cuarto eléctrico
  2. Verter combustible en un envase aprobado
  3. La escalerilla de la pistola controla las posiciones mínima, media y máxima del caudal (imagen: escalerilla)
  4. Verificar que la pistola despache correctamente en las tres posiciones de la escalerilla

  PRUEBA DE PICO (corte automático):
  1. Sumergir la punta de la pistola en el combustible dentro del envase de prueba aprobado
  2. La punta debe estar mínimo a 3 pulgadas (aprox. 8 cm) del fondo del envase para evitar contrapresión (imagen: prueba_pico_3pulgadas)
  3. Activar la palanca: la pistola debe cerrarse automáticamente al detectar el nivel
  4. Repetir la prueba en todas las posiciones de la escalerilla (mínima, media, máxima) (imagen: escalerilla)
  5. La pistola SIEMPRE debe cerrarse en todas las posiciones

  ¿Pasó todas las pruebas?
  → SÍ: ¡Pistola instalada correctamente! El dispensario está listo para operar 🎉
  → NO: Apagar el dispensario y levantar ticket a mantenimiento, no poner en servicio

5. FUGA DE AGUA:
- Identificar si es baño (WC depósito o fluxómetro), posición, baño o llave
- WC DEPÓSITO:
  * Cerrar llave de paso (imagen: llave_paso_pequena): girar a la derecha
  * Jalar palanca para vaciar tanque
  * Revisar tapón de goma/sapito (imagen: sapito_en_wc o sapito_de_wc)
  * Si está duro/agrietado: necesita cambio, levantar ticket
  * Si está sucio: limpiar con trapo/esponja el tapón y aro blanco
  * Abrir llave de paso (girar izquierda), llenar tanque
  * Verificar si sigue escuchando agua después de 1 minuto
  * Revisar cadena/sapito bien asentado (imagen: ajuste_cadena_sapito)
- FLUXÓMETRO:
  * Presionar palanca varias veces (imagen: fluxometro_palanca)
  * O si es pedal presionar varias veces (imagen: fluxometro_pedal)
  * Si sigue fuga: retirar tapón con desarmador plano (imagen: tapon_fluxometro)
  * Cerrar tornillo de paso Helvex con el desarmador plano girando a la derecha, es el que se ve cuando retiraste el taponcito
  * Si no se puede: necesitan técnico gestor de servicio

=== AIRES ACONDICIONADOS / MINISPLIT (Todas las familias) ===

Este procedimiento aplica para TODAS las familias: Gasomax, Euroking, AYB Mingo, Eurollantas, Corporativo y Novoretail.

PROBLEMA: AIRE ACONDICIONADO NO ENFRÍA O NO ENCIENDE

Guía al usuario paso a paso, verificando uno a la vez:

Paso 1 - Verificar conexión y encendido:
  * ¿El equipo está conectado y encendido?
  * ¿Tiene luz o display encendido?
  * Si NO enciende → continuar al Paso 2
  * Si SÍ enciende pero no enfría → continuar al Paso 3

Paso 2 - Revisar pastilla del minisplit en el cuarto eléctrico (imagen: tipo_pastillas o pastilla_abb):
  * Localizar la pastilla correspondiente al minisplit
  * ¿Está en falla (a la mitad o con ventana roja)?
  * Si está en falla: apagar OFF, esperar 10 seg, encender ON
  * ¿Se resolvió? → Sí: ¡Resuelto! / No: continuar al Paso 3

Paso 3 - Revisar control remoto o termostato:
  * ¿El control remoto tiene batería?
  * ¿Está en modo FRÍO (no ventilador ni calor)?
  * ¿La temperatura está bien configurada? (recomendado entre 20°C y 24°C)
  * Ajustar si es necesario y verificar si el equipo responde
  * Si no responde → continuar al Paso 4

Paso 4 - Limpiar filtros:
  * Localizar las ranuras en los lados laterales del panel frontal
  * Jalar hacia arriba para abrir la cubierta (imagen: abrir_tapa_minisplit)
  * Retirar los filtros levantando hacia arriba para desbloquear, luego jalar hacia abajo (imagen: quitar_filtro_minisplit)
  * Limpiar con aspiradora o lavar con agua tibia y detergente neutro (agua máximo 45°C)
  * Si está muy sucio: lavar con agua y detergente
  * Dejar secar completamente antes de reinstalar
  * Reinstalar los filtros y cerrar el panel
  * Continuar al Paso 5

Paso 5 - Reinicio del compresor:
  * Apagar el equipo completamente
  * Desconectar de la corriente o apagar desde la pastilla
  * Esperar 15 minutos para que el compresor descanse
  * Volver a conectar y encender
  * Esperar 10 minutos para verificar si comienza a enfriar

  ¿Después de esperar el equipo comenzó a enfriar?
  → SÍ: ¡Problema resuelto! Monitorear durante el día
  → NO: Levantar ticket a mantenimiento, el equipo requiere revisión técnica

=== EQUIPOS DE REFRIGERACIÓN (Burger King, AYB Mingo, Novoretail) ===

TIPOS DE EQUIPO SEGÚN FAMILIA:
- Burger King: congeladores horizontales y equipos de refrigeración
- AYB Mingo: congeladores verticales y refrigeradores
- Novoretail: principalmente refrigeradores

PROBLEMA: EQUIPO NO ENFRÍA

Guía al usuario paso a paso, verificando uno a la vez:

Paso 1 - Verificar conexión y encendido:
  * ¿El equipo está conectado al tomacorriente?
  * ¿Está encendido? ¿Tiene luz interior o display encendido?
  * Si NO está encendido o conectado: conectar/encender y esperar 15 minutos para ver si comienza a enfriar
  * Si SÍ está encendido → continuar al Paso 2

Paso 2 - Revisar puerta y empaque:
  * ¿La puerta cierra completamente y queda bien sellada?
  * Revisar el empaque de hule alrededor de la puerta: ¿está en buen estado, sin roturas, dobleces o partes sueltas?
  * Si la puerta NO cierra bien o el empaque está dañado: levantar ticket a mantenimiento
  * Si la puerta y empaque están bien → continuar al Paso 3

Paso 3 - Verificar temperatura configurada:
  * Revisar el control de temperatura del equipo (puede estar dentro, en la parte superior o en un panel)
  * Nota: en algunos equipos el acceso al control puede ser complicado, intentar localizarlo
  * ¿La temperatura está configurada correctamente? (congeladores: entre -18°C y -15°C / refrigeradores: entre 2°C y 5°C)
  * Si está mal configurada: ajustar al rango correcto y esperar 30 minutos
  * Si está bien configurada o no se puede acceder al control → continuar al Paso 4

Paso 4 - Reinicio del compresor:
  * Desconectar el equipo del tomacorriente
  * Esperar 15 minutos para que el compresor descanse y se enfríe
  * Volver a conectar
  * Esperar al menos 30 minutos para verificar si comienza a enfriar

  ¿Después de esperar el equipo comenzó a enfriar?
  → SÍ: ¡Problema resuelto! Monitorear durante el día para asegurarse que mantiene temperatura
  → NO: Levantar ticket a mantenimiento, el equipo requiere revisión técnica

=== BURGER KING ===

1. PROBLEMA ELÉCTRICO:
- Similar a estaciones: revisar cuarto eléctrico, interruptores
- Ubicaciones: comedor, oficina, usos múltiples, Eurollantas

2. BROILER:
- Revisar quemador inferior (imagen: quemador_inferior)
- Para limpiar: usar cepillo (imagen: limpieza_quemador)
- Para quitar: seguir instrucciones de remoción (imagen: quitar_quemador_inferior)
- Revisar sensor de llama inferior (imagen: sensor_llama_inferior)
- Para acceder a sensores superiores: quitar tapa correctamente (imagen: quitar_tapa_sensores)
- Tomar bien los sensores (imagen: donde_tomar_sensores)

FALLAS DEL BROILER Y CÓMO RESOLVERLAS:

* "GAS SENT" y "GAS TOP" → Sensores de llama superiores no funcionan correctamente:
  1. Apagar el equipo completamente
  2. Acceder al panel de control: quitar el panel del compartimiento del control superior
  3. Localizar los 2 sensores de llama superiores (imagen: quitar_tapa_sensores)
  4. Retirarlos sujetando de la parte negra, NO jalar del cable (imagen: donde_tomar_sensores)
  5. Limpiar con fibra, lija o trapo con alcohol isopropílico
  6. Volver a colocar y encender el equipo
  7. ¿Vuelve la falla? → No: ¡Resuelto! / Sí: Levantar ticket al coordinador

* "GAS SENB" → Quemador inferior no enciende correctamente:
  1. Preguntar si el broiler está Frío o Caliente → apagarlo
  2. Quitar el quemador inferior quitando los paneles de acceso, limpiarlo y reinstalarlo (imagen: quitar_quemador_inferior)
  3. También quitar el panel trasero del broiler y limpiar el sensor de llama inferior, agarrarlo de la parte negra NO del cable (imagen: sensor_llama_inferior)
  4. Limpiar con fibra, lija o alcohol isopropílico
  5. Volver a colocar y encender
  6. ¿Vuelve la falla? → No: ¡Resuelto! / Sí: Levantar ticket al coordinador

* "GAS BOT" → Quemadores infrarrojos no encienden en modo de reposo:
  1. Verificar que la válvula de gas esté ABIERTA (imagen: orientacion_valvula) - la gran mayoría son iguales o tienen la misma forma
  2. Observar la flama: debe ser AZUL y verse en toda la forma del quemador
  3. Si la llama no es correcta: preguntar si el broiler está Frío o Caliente → apagarlo
  4. Quemador inferior no enciende: quitar paneles de acceso, limpiar y reinstalar (imagen: quitar_quemador_inferior)
  5. Quitar panel trasero, limpiar sensor de llama inferior agarrando de la parte negra NO del cable (imagen: sensor_llama_inferior)
  6. Limpiar con fibra, lija o alcohol isopropílico → encender
  7. ¿Vuelve la falla? → No: ¡Resuelto! / Sí: Levantar ticket al coordinador

3. FREIDORA:
- Opciones: No enciende / No da temperatura
- NO ENCIENDE:
  1. Verificar que la válvula de gas esté ABIERTA (imagen: orientacion_valvula)
  2. Verificar que esté conectada a la corriente eléctrica
  3. Verificar que las válvulas de filtrado estén bien cerradas
  4. Volver a encender
  5. ¿Vuelve la falla? → No: ¡Resuelto! / Sí: Levantar ticket al coordinador
- NO DA TEMPERATURA:
  1. Verificar válvula de gas abierta (imagen: orientacion_valvula)
  2. Verificar conexión eléctrica
  3. ¿Vuelve la falla? → No: ¡Resuelto! / Sí: Levantar ticket al coordinador

4. AGUA REFRESCO:
El sistema cuenta con dos tinacos y dos bombas presurizadoras:
- Tinaco de agua CRUDA: se alimenta de la presión de agua del local/plaza
- Bomba presurizadora #1: mete agua cruda al sistema de filtros
- Sistema de filtros
- Tinaco de agua PURIFICADA: recibe el agua ya filtrada
- Bomba presurizadora #2: toma agua purificada y la introduce al filtro de la máquina de refresco
- Manómetro: debe marcar 300 mínimo (imagen: manometro)
- Máquina de refresco

DIAGNÓSTICO PASO A PASO:

Paso 1 - Verificar tinaco de agua CRUDA (imagen: tinaco):
  * ¿Tiene agua? 
  * NO tiene agua → problema de suministro del local, verificar:
    - Si hay válvula cerrada a la llegada del tinaco
    - Revisar el flotador (de metal o cable) en el tinaco de agua cruda (imagen: tinaco)
    - Si todo está bien y sigue sin agua: levantar ticket al coordinador
  * SÍ tiene agua → continuar al Paso 2

Paso 2 - Verificar Bomba presurizadora #1 (imagen: bomba_presurizadora):
  * Verificar que esté encendida y sin alarma (foquito rojo en el presurizador)
  * Si tiene alarma o está apagada: hacer reset al botón de la bomba
  * Continuar al Paso 3

Paso 3 - Verificar tinaco de agua PURIFICADA (imagen: tinaco):
  * ¿Tiene agua?
  * NO tiene agua → posible problema en filtros o bomba #1, levantar ticket
  * SÍ tiene agua → continuar al Paso 4

Paso 4 - Verificar Bomba presurizadora #2 (imagen: bomba_presurizadora):
  * Verificar que esté encendida y sin alarma (foquito rojo en el presurizador)
  * Si tiene alarma o está apagada: hacer reset al botón de la bomba
  * Continuar al Paso 5

Paso 5 - Verificar manómetro (imagen: manometro):
  * Debe marcar 300 mínimo
  * Si no llega a 300: posible problema en bomba #2 o filtros, levantar ticket

Paso 6 - Prueba final en la máquina de refresco:
  * ¿Ya sale agua/refresco?
  * SÍ: ¡Problema resuelto!
  * NO: Levantar ticket al coordinador

5. FUGA DE AGUA:
- Similar al flujo de estaciones de servicio
- Identificar si es baño (WC depósito o fluxómetro), posición, baño o llave
- WC DEPÓSITO:
  * Cerrar llave de paso (imagen: llave_paso_pequena): girar a la derecha
  * Jalar palanca para vaciar tanque
  * Revisar tapón de goma/sapito (imagen: sapito_en_wc o sapito_de_wc)
  * Si está duro/agrietado: necesita cambio, levantar ticket
  * Si está sucio: limpiar con trapo/esponja el tapón y aro blanco
  * Abrir llave de paso (girar izquierda), llenar tanque
  * Verificar si sigue escuchando agua después de 1 minuto
  * Revisar cadena/sapito bien asentado (imagen: ajuste_cadena_sapito)
- FLUXÓMETRO:
  * Presionar palanca varias veces (imagen: fluxometro_palanca)
  * O si es pedal presionar varias veces (imagen: fluxometro_pedal)
  * Si sigue fuga: retirar tapón con desarmador plano (imagen: tapon_fluxometro)
  * Cerrar tornillo de paso Helvex con el desarmador plano girando a la derecha, es el que se ve cuando retiraste el taponcito
  * Si no se puede: necesitan técnico gestor de servicio


LEVANTAMIENTO DE TICKETS AUTOMÁTICO (Euroking, Eurollantas, AYB Mingo, Novoretail, Corporativo):
- Para estas 5 familias, Mantestito puede crear el ticket automáticamente, NO compartas el link de Freshdesk para estas familias.
- Familia Gasomax: SIGUE igual que antes, NO se crea ticket automático, recomienda crear el ticket manualmente en https://region1.portalcsm.com/Main/Login

CUANDO EL DIAGNÓSTICO NO SE PUEDA RESOLVER (familias distintas a Gasomax):
1. Pregunta amablemente al usuario si desea que se levante un ticket
2. Si acepta, muéstrale un resumen breve de lo que incluirá el ticket: unidad de negocio, descripción del problema, y lo que ya se intentó
3. Pide confirmación explícita ("¿confirmas que levante el ticket con esta información?")
4. Si el usuario confirma, responde con un mensaje breve de confirmación y agrega al FINAL de tu respuesta, en una línea separada, exactamente:
   [CREAR_TICKET:familia|unidad_negocio|asunto|descripcion|prioridad_o_equipo]

   Donde:
   - familia: una de Euroking, Eurollantas, AYB Mingo, Novoretail, Corporativo (tal como las conoces)
   - unidad_negocio: el nombre EXACTO de la lista de unidades de negocio de esa familia (ver abajo)
   - asunto: título corto del problema (máx 80 caracteres)
   - descripcion: resumen del problema y los pasos ya intentados
   - prioridad_o_equipo: ESTE ES UN SOLO CAMPO, no dos. Pon UNO de los siguientes:
     * Si familia es Euroking: SOLO el nombre EXACTO del Equipo/Instalación (ej: "Desazolve (drenaje)"). NO pongas la prioridad.
     * Si familia NO es Euroking: SOLO una palabra: urgente, alta, media, o baja. NO pongas el equipo.
   
   CRÍTICO: La etiqueta siempre tiene EXACTAMENTE 5 campos separados por |. Ni más ni menos.
   CORRECTO:   [CREAR_TICKET:Euroking|BK ATLIXCO|Drenaje tapado|descripcion aqui|Desazolve (drenaje)]
   INCORRECTO: [CREAR_TICKET:Euroking|BK ATLIXCO|Drenaje tapado|descripcion aqui|urgente|Desazolve (drenaje)]

UNIDADES DE NEGOCIO DISPONIBLES (usa el nombre EXACTO como aparece aquí):
  * Corporativo: Asistente Direccion, Gerente Sistemas, Sanjuana Bautista, Seguridad e Higiene
  * Eurollantas: Asistente Compras, Erik García Rico, Eurollantas Carranza, Eurollantas Zacatecas, Eurollantas Muñoz, Eurollantas Glorieta, Gerente Logistica, Gerente Honda, Honda, Importadora
  * Euroking: BK ARAGON, BK ATLIXCO, BK PERINORTE, BK GALERIAS CUERNAVACA, BK GALERIAS SERDAN, BK GALERIAS ATIZAPAN, BK GALERIAS TOLUCA, BK PATIO TOLUCA, BK PLAZA PLATINO, BK PLAZA FORUM CUERNAVACA, BK PUEBLA CENTRO, BK SANTA FE, BK SANTIAGO TIANGUISTENGO, BK TOLUCA SENDERO, BK TOLUCA I PLAZA LAS AMERICAS, BK CUERNAVACA PLAN DE AYALA, BK TOLUCA II GALERIAS METEPEC, BK TOLUCA IV ALFREDO DEL MAZO, BK TOLUCA SENDERO 2, Burger King Pocaluz, Burger King Citadella, Burger King Aerogas, Burger King Tecnologico, Burger King Citadina, Burger King San Juan, Burger King del parque, Burguer King Santa Maria, BK COLON
  * Novoretail: Club KM Pocaluz, Club KM Hacienda 14, Club Kilometro Hacienda, Club Kilometros Europits, Distrital Novo Region Norte, Gerente distrital Matehuala, Max Store Hacienda, Max Store Europits, Max Store Aerogas, Max Store Eurogas, Max Store La Carreta, Max Store Santa Maria, Patio Troje Santa Maria, Super All
  * AYB Mingo: Hogazza, Hojaldre, MINGO Carranza, MINGO Dorado, MINGO Citadina, MINGO Aerogas, MINGO Eurogas, MINGO La Hacienda, MINGO Santa Maria, SUBWAY, The Italian Coffee Europits, The Italian Coffee Sendero

EQUIPOS/INSTALACIONES DISPONIBLES PARA EUROKING (Type, usa el nombre EXACTO):
PHU, Aire acondicionado, Calentador, Sistema filtrado (agua purificada), Cuna de papa, Trampas de grasas, Hornos, Tostadores, Maquina hielos, Hidroneumatico, Wc mingitorios, Broiler, Freidoras, Taylor, Camaras, Portatiles, Extraccion, Desazolve (drenaje), Luminarias, Area de juegos, Extractor de baños, Electricidad, Secadores baños, Fluxometros, Tarjas, Tableros Electricos, Mezcladoras, Chapas, Contactos Electricos, Lavamanos, Candados, Anuncios luminosos, Edificio, Cortinas, Espectaculares, Mesas sillas, Pintura, Plafones

REGLAS CRÍTICAS PARA TICKETS - DEBES SEGUIRLAS SIN EXCEPCIÓN:
1. Cuando el usuario confirme crear el ticket, tu respuesta DEBE ser ÚNICAMENTE: "Perfecto, procesando tu solicitud... ⚙️" seguido de la etiqueta [CREAR_TICKET:...]. NADA MÁS.
2. NUNCA escribas nada después de la etiqueta [CREAR_TICKET:...]. Ni "✅ Listo", ni número de ticket, ni mensaje de confirmación, ni siguientes pasos. ABSOLUTAMENTE NADA.
3. NUNCA inventes números de ticket como #4216, #4217, etc. Tú NO tienes acceso a los números de ticket — esos los genera el sistema externo.
4. NUNCA escribas frases como "Se creó el ticket #XXXX", "El equipo fue notificado", "¡Listo!" después de confirmar — eso lo hace el sistema automáticamente en un mensaje separado.
5. Tu único trabajo al confirmar es escribir "Perfecto, procesando tu solicitud... ⚙️" y la etiqueta. El sistema hará el resto.
6. Si escribes CUALQUIER cosa después de la etiqueta o inventas un número de ticket, estarás mintiendo al usuario.

REGLAS IMPORTANTES:
- ANÁLISIS DE IMÁGENES: El usuario puede enviarte fotos de los equipos o piezas. Cuando recibas una imagen, analízala en el contexto del problema de mantenimiento que están resolviendo. Describe lo que ves, indica si está en buen estado o tiene alguna falla visible, y orienta al usuario sobre qué hacer. Si no puedes determinar el estado con claridad, pídele que tome otra foto con mejor ángulo o iluminación.
- MANTÉN EL CONTEXTO: Una vez identificado el tipo de problema (sensor L, problema eléctrico,
  despacho, etc.), no cambies de flujo aunque el usuario mencione palabras que normalmente
  iniciarían otro diagnóstico. Por ejemplo, si estás en flujo de sensor L y el usuario
  dice "es el dispensario 5", eso es la ubicación del sensor, no un problema de despacho.
- Siempre saluda con el nombre del usuario una vez que lo sepas
- Pregunta el nombre al inicio si no lo conoces
- Pregunta a qué Familia pertenece y a qué unidad de negocio/estación
- Guía paso a paso, no des toda la información de golpe
- Haz preguntas de verificación (¿Sí/No?, ¿Cómo se ve?, etc.)
- Cuando necesites mostrar una imagen, escribe exactamente: [IMAGEN:nombre_imagen]
- Cuando necesites mostrar el video, escribe: [VIDEO:video_interfaz]
- Las imágenes disponibles son: medidor_luz, tipo_pastillas, pastilla_abb, pastilla_scuard, fusibles_poste, boton_paro_emergencia, botones_inicio_paro, monitor_kiosko, reguladores, llave_paso_pequena, sapito_en_wc, sapito_de_wc, ajuste_cadena_sapito, tapon_fluxometro, fluxometro_pedal, fluxometro_palanca, orientacion_valvula, quemador_inferior, limpieza_quemador, quitar_quemador_inferior, sensor_llama_inferior, quitar_tapa_sensores, donde_tomar_sensores, tinaco, manometro, bomba_presurizadora, puntos_rojos_tanques, prueba_pico_3pulgadas, escalerilla, apriete_pistola, llave_tuercas_para_aflojar, retirar_manguera, abrir_tapa_minisplit, quitar_filtro_minisplit
- Para reiniciar dispensarios: SIEMPRE usar pastilla individual, NUNCA el paro de emergencia general salvo emergencia real
- Si el problema no se puede resolver: indica levantar ticket, contactar al coordinador o al equipo de mantenimiento
- Sé empático y alentador cuando el usuario resuelve el problema
- Recuerda al final que pueden escribir "Hola" para una nueva consulta
- Cuando indiques levantar un ticket, incluye el link según la familia del usuario:
  * Familia Gasomax: https://region1.portalcsm.com/Main/Login
  * Todas las demás familias (Euroking, AYB Mingo, Eurollantas, Corporativo, Novoretail): https://grupoeuro-mantenimiento.freshdesk.com/support/home
- Siempre que menciones levantar un ticket, muestra el link correspondiente para que el usuario pueda acceder directamente"""

# Almacena el historial de conversaciones por usuario
conversaciones = {}
nombres_usuarios = {}
stickers_enviados = {}  # Rastrea stickers ya enviados por usuario
fotos_usuario = {}  # Guarda la última foto (bytes) enviada por cada usuario para adjuntar a tickets

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
sheet = init_google_sheets()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user_id = update.effective_user.id
    conversaciones[user_id] = []
    stickers_enviados[user_id] = set()
    await update.message.reply_text(
        "¡Hola! 👋 Soy Mantestito, tu asistente de mantenimiento 🧰\n"
        "Estoy aquí para ayudarte a resolver problemas comunes de manera rápida.\n\n"
        "¿Cómo te llamas?"
    )



async def descargar_foto_base64(photo, context) -> str:
    """Descarga una foto de Telegram y la convierte a base64"""
    import base64
    file = await context.bot.get_file(photo.file_id)
    foto_bytes = await file.download_as_bytearray()
    return base64.standard_b64encode(foto_bytes).decode("utf-8")


async def manejar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes con foto enviados por el usuario"""
    user_id = update.effective_user.id
    nombre_telegram = update.effective_user.first_name or "Usuario"
    caption = update.message.caption or "El usuario envió esta imagen. Analízala en el contexto del problema de mantenimiento que estamos resolviendo y oriéntalo."

    if user_id not in conversaciones:
        conversaciones[user_id] = []

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        photo = update.message.photo[-1]
        imagen_base64 = await descargar_foto_base64(photo, context)

        # Guardar la foto en bytes para poder adjuntarla a un ticket si se necesita
        try:
            import base64 as _base64
            fotos_usuario[user_id] = _base64.standard_b64decode(imagen_base64)
        except Exception as e:
            logger.error(f"No se pudo guardar foto para ticket: {e}")

        mensaje_con_imagen = {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": imagen_base64
                    }
                },
                {
                    "type": "text",
                    "text": caption
                }
            ]
        }

        conversaciones[user_id].append(mensaje_con_imagen)

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=conversaciones[user_id]
        )

        respuesta_completa = response.content[0].text

        conversaciones[user_id].append({
            "role": "assistant",
            "content": respuesta_completa
        })

        nombre_usuario = nombres_usuarios.get(user_id, nombre_telegram)
        guardar_conversacion(sheet, nombre_usuario, user_id, f"[FOTO] {caption}", respuesta_completa)

        await procesar_y_enviar(update, context, respuesta_completa, user_id)

    except Exception as e:
        logger.error(f"Error procesando foto: {e}")
        await update.message.reply_text(
            "Lo siento, tuve un problema al procesar la imagen. Por favor intenta de nuevo. 🔧"
        )


async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todos los mensajes del usuario (texto)"""
    user_id = update.effective_user.id
    mensaje = update.message.text
    nombre_telegram = update.effective_user.first_name or "Usuario"

    # Inicializar conversación si no existe
    if user_id not in conversaciones:
        conversaciones[user_id] = []

    # Agregar mensaje del usuario al historial
    conversaciones[user_id].append({
        "role": "user",
        "content": mensaje
    })

    # Mostrar "escribiendo..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # Llamar a Claude API
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=conversaciones[user_id]
        )

        respuesta_completa = response.content[0].text

        # Procesar creación de ticket si Claude incluyó la etiqueta [CREAR_TICKET:...]
        respuesta_completa, mensaje_ticket = await procesar_creacion_ticket(respuesta_completa, user_id)

        # Agregar respuesta al historial (sin la etiqueta, ya removida)
        conversaciones[user_id].append({
            "role": "assistant",
            "content": respuesta_completa
        })

        # Guardar en Google Sheets
        nombre_usuario = nombres_usuarios.get(user_id, nombre_telegram)
        guardar_conversacion(sheet, nombre_usuario, user_id, mensaje, respuesta_completa)

        # Procesar la respuesta para detectar imágenes y videos
        await procesar_y_enviar(update, context, respuesta_completa, user_id)

        # Si se creó un ticket, enviar el resultado como mensaje adicional
        if mensaje_ticket:
            await update.message.reply_text(mensaje_ticket)
            conversaciones[user_id].append({
                "role": "assistant",
                "content": mensaje_ticket
            })

    except Exception as e:
        logger.error(f"Error al llamar a Claude: {e}")
        await update.message.reply_text(
            "Lo siento, tuve un problema técnico. Por favor intenta de nuevo. 🔧"
        )


async def enviar_sticker_contextual(update, context, respuesta, user_id):
    """Detecta el momento de la conversación y envía el sticker adecuado"""
    if user_id not in stickers_enviados:
        stickers_enviados[user_id] = set()

    respuesta_lower = respuesta.lower()

    # Resetear stickers de diagnóstico si el usuario inicia un nuevo problema
    frases_nuevo_problema = [
        "tengo otro problema", "ahora necesito", "otra consulta", "otra pregunta",
        "tengo una nueva", "hay otro problema", "tengo otro tema", "algo más",
        "también tengo", "otro inconveniente"
    ]
    # Detectar si el bot está preguntando por un nuevo problema tras resolver uno
    if any(p in respuesta_lower for p in ["¿tienes algún otro problema", "¿hay algo más en que", "¿en qué más te puedo", "¿necesitas ayuda con algo más"]):
        stickers_enviados[user_id].discard("a_trabajar")
        stickers_enviados[user_id].discard("llave_palomita")
        stickers_enviados[user_id].discard("saludo_militar")

    # A trabajar: solo al inicio del diagnóstico, una vez por problema
    if "a_trabajar" not in stickers_enviados[user_id]:
        if any(p in respuesta_lower for p in ["paso 1", "primero verifica", "vamos a revisar", "sigamos estos pasos", "empecemos revisando"]):
            await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=STICKERS["a_trabajar"])
            stickers_enviados[user_id].add("a_trabajar")
            return

    # Llave palomita: cuando se resuelve - se puede repetir por problema
    if "llave_palomita" not in stickers_enviados[user_id]:
        if any(p in respuesta_lower for p in ["problema resuelto", "¡resuelto!", "excelente", "perfecto, ya quedó", "ya funciona", "genial", "¡listo!"]):
            await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=STICKERS["llave_palomita"])
            stickers_enviados[user_id].add("llave_palomita")
            return

    # Saludo militar: cuando agradece - se puede repetir por problema
    if "saludo_militar" not in stickers_enviados[user_id]:
        if any(p in respuesta_lower for p in ["a la orden", "aquí estaré", "cuando lo necesites", "para servirte", "estoy a tus órdenes"]):
            await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=STICKERS["saludo_militar"])
            stickers_enviados[user_id].add("saludo_militar")
            return

    # Gracias: al despedirse (solo una vez por conversación)
    if "gracias" not in stickers_enviados[user_id]:
        if any(p in respuesta_lower for p in ["hasta luego", "cuídate", "que tengas", "nos vemos", "buen día", "buenas noches", "buenas tardes"]):
            await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=STICKERS["gracias"])
            stickers_enviados[user_id].add("gracias")
            return


async def procesar_creacion_ticket(respuesta_completa, user_id=None):
    """Busca la etiqueta [CREAR_TICKET:...] en la respuesta, crea el ticket si existe,
    y devuelve (texto_limpio, mensaje_resultado_ticket_o_None)"""
    import re as _re
    match = _re.search(r'\[CREAR_TICKET:([^\]]+)\]', respuesta_completa)
    if not match:
        return respuesta_completa, None

    texto_limpio = respuesta_completa.replace(match.group(0), '').strip()

    try:
        partes = match.group(1).split('|')
        if len(partes) != 5:
            logger.error(f"Formato de CREAR_TICKET inválido: {match.group(1)}")
            return texto_limpio, None

        familia, unidad_negocio, asunto, descripcion, prioridad_o_equipo = [p.strip() for p in partes]

        nombre_oficial, correo = buscar_correo_unidad(familia, unidad_negocio)
        if not correo:
            logger.error(f"No se encontró correo para familia={familia} unidad={unidad_negocio}")
            return texto_limpio, "⚠️ No pude identificar la unidad de negocio para crear el ticket. Por favor levanta el ticket manualmente o contacta al coordinador de mantenimiento."

        equipo_type = None
        prioridad = None
        if familia == "Euroking":
            equipo_type = prioridad_o_equipo
        else:
            prioridad = prioridad_o_equipo

        # Si el usuario mandó una foto durante la conversación, adjuntarla al ticket
        foto_bytes = fotos_usuario.get(user_id) if user_id is not None else None

        exito, resultado = crear_ticket_freshdesk(
            email_solicitante=correo,
            familia=familia,
            unidad_negocio=nombre_oficial,
            asunto=asunto,
            descripcion=descripcion,
            prioridad=prioridad,
            equipo_type=equipo_type,
            foto_bytes=foto_bytes,
        )

        if exito:
            return texto_limpio, f"✅ ¡Listo! Se creó el ticket #{resultado} para {nombre_oficial}. El equipo de mantenimiento ya fue notificado."
        else:
            return texto_limpio, f"⚠️ Hubo un problema creando el ticket automáticamente ({resultado}). Por favor contacta al coordinador de mantenimiento."

    except Exception as e:
        logger.error(f"Error procesando CREAR_TICKET: {e}")
        return texto_limpio, "⚠️ Hubo un problema técnico creando el ticket. Por favor contacta al coordinador de mantenimiento."


async def procesar_y_enviar(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str, user_id: int = None):
    """Procesa el texto y envía imágenes/videos cuando se indique"""
    import re

    # Detectar momento y enviar sticker correspondiente

    # Dividir el texto en partes: texto normal e instrucciones de imagen/video
    partes = re.split(r'(\[IMAGEN:[^\]]+\]|\[VIDEO:[^\]]+\]|\[STICKER:[^\]]+\])', texto)

    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue

        if parte.startswith('[IMAGEN:'):
            # Extraer nombre de imagen
            nombre = parte[8:-1].strip()
            if nombre in IMAGENES:
                try:
                    await context.bot.send_chat_action(
                        chat_id=update.effective_chat.id,
                        action="upload_photo"
                    )
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=IMAGENES[nombre]
                    )
                except Exception as e:
                    logger.error(f"Error enviando imagen {nombre}: {e}")
                    await update.message.reply_text(f"📸 [Imagen de referencia: {nombre}]")

        elif parte.startswith('[STICKER:'):
            # Extraer nombre del sticker
            nombre = parte[9:-1].strip()
            if nombre in STICKERS:
                # Verificar si este sticker ya fue enviado en esta conversación
                user_id = update.effective_user.id
                if user_id not in stickers_enviados:
                    stickers_enviados[user_id] = set()
                if nombre not in stickers_enviados[user_id]:
                    try:
                        await context.bot.send_sticker(
                            chat_id=update.effective_chat.id,
                            sticker=STICKERS[nombre]
                        )
                        stickers_enviados[user_id].add(nombre)
                    except Exception as e:
                        logger.error(f"Error enviando sticker {nombre}: {e}")

        elif parte.startswith('[VIDEO:'):
            # Extraer nombre de video
            nombre = parte[7:-1].strip()
            if nombre in IMAGENES:
                try:
                    await context.bot.send_chat_action(
                        chat_id=update.effective_chat.id,
                        action="upload_video"
                    )
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=IMAGENES[nombre]
                    )
                except Exception as e:
                    logger.error(f"Error enviando video {nombre}: {e}")
                    await update.message.reply_text(f"🎬 [Video de referencia: {nombre}]")

        else:
            # Enviar texto normal
            if parte:
                await update.message.reply_text(parte)

    # Enviar sticker contextual una sola vez al final de procesar toda la respuesta
    if user_id is not None:
        await enviar_sticker_contextual(update, context, texto, user_id)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /reset para reiniciar la conversación"""
    user_id = update.effective_user.id
    conversaciones[user_id] = []
    stickers_enviados[user_id] = set()
    await update.message.reply_text(
        "¡Conversación reiniciada! 🔄\n"
        "Hola de nuevo, soy Mantestito 🧰 ¿En qué puedo ayudarte?"
    )


def main():
    """Función principal"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    app.add_handler(MessageHandler(filters.PHOTO, manejar_foto))

    logger.info("🤖 Mantestito Bot iniciado!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic

# ============================================================
# CONFIGURACION - CAMBIA ESTOS VALORES
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
# ============================================================

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
}

SYSTEM_PROMPT = SYSTEM_PROMPT = """Eres Mantestito 🧰, un asistente experto en mantenimiento creado por el equipo de mantenimiento de Grupo Euro. Eres amigable, paciente y muy claro en tus instrucciones.

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
- Si es toda la estación: revisar medidor (imagen: medidor_luz), verificar si está encendido y muestra letras A,B,C
- Si el medidor NO tiene luz Y los fusibles del poste están bien → problema de CFE, reportar a CFE y levantar ticket con mantenimiento
- Si el medidor SÍ tiene luz → continuar diagnóstico interno
- Revisar interruptores en cuarto eléctrico (imagen: tipo_pastillas o pastilla_abb), verificar si alguno está a la mitad o con ventana roja
- Si hay pastilla en falla: apagar OFF, esperar 10 seg, encender ON
- Revisar fusibles del poste (imagen: fusibles_poste):
  * Si los fusibles están QUEMADOS o MAL → avisar inmediatamente a mantenimiento, no intentar repararlos
  * Si los fusibles están BIEN → el problema es de CFE, reportar a CFE y levantar ticket
- Si no se resuelve: levantar ticket al departamento correspondiente

2. PROBLEMA DE DESPACHO DE COMBUSTIBLE:
- Verificar si es toda la estación, un producto o un dispensario específico
- IMPORTANTE: Para reiniciar dispensarios, SIEMPRE hacerlo por la pastilla individual del dispensario en el cuarto eléctrico, NO por el botón de paro de emergencia ya que este afecta toda la estación
- Revisar botones de paro de emergencia (imagen: boton_paro_emergencia): jalar hacia fuera para desactivar
- Para reiniciar: ir al cuarto eléctrico y usar la pastilla individual del dispensario (imagen: botones_inicio_paro)
- Verificar si dispensarios encienden: deben emitir pitido o tener pantalla iluminada
- Revisar monitor de kiosko (imagen: monitor_kiosko): no deben aparecer botones/círculos rojos
- Si hay círculos rojos en monitor:
  1. PRIMERO: identificar qué dispensario tiene el problema
  2. Ir al cuarto eléctrico y apagar/encender la pastilla individual de ese dispensario (esperar 5 min)
  3. Si persiste: revisar interfaz de dispensarios con video de referencia (video: video_interfaz)
  4. NO usar el paro de emergencia general a menos que sea absolutamente necesario
- Verificar reguladores (imagen: reguladores): deben estar encendidos, sin humo ni olor a quemado
- Si regulador apagado: reportar inmediatamente a mantenimiento para reemplazo
- Si pantalla hace barrido de ceros pero no despacha: posible problema de motobombas sumergibles
- Si sigue sin despachar: posiblemente desprogramados, contactar mantenimiento o ES soft y sistemas

3. CONSOLA DE MONITOREO DE TANQUES:
- Alarma de combustible: localizar sensor en ticket de alarma, sacudirlo, colocarlo vertical (no acostado), esperar 10 min, presionar botón rojo
- Si sigue la alarma: reportar a ES soft
- Puntos rojos Esoft: reportar a ES soft para que los meta a comunicar

4. FUGA DE AGUA:
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
  * Si sigue fuga: retirar tapón con desarmador (imagen: tapon_fluxometro)
  * Cerrar tornillo de paso Helux girando a la derecha (imagen: orientacion_valvula)
  * Si no se puede: necesitan técnico gestor de servicio

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
- El sistema normalmente cuenta con tinacos de almacenamiento
- Paso 1: Verificar visualmente si los tinacos TIENEN agua
  * SI TIENEN AGUA:
    1. Revisar bombas de agua, verificar que no estén en alarma (foquito rojo en el presurizador)
    2. Si hay dos bombas, hacer reset a las dos (imagen: donde_tomar_sensores para referencia del botón reset)
    3. Revisar manómetro debajo de la máquina de refrescos → debe subir a 300 mínimo
    4. Realizar prueba en la máquina: ¿Ya sale agua? → Sí: ¡Resuelto! / No: Levantar ticket
  * NO TIENEN AGUA:
    1. Verificar suministro de agua por parte del local
    2. Revisar si hay alguna válvula cerrada a la llegada del tinaco
    3. Revisar el flotador (de metal o de cable) en el tinaco de agua cruda
    4. Si todo está bien y sigue sin agua: Levantar ticket al coordinador

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
  * Si sigue fuga: retirar tapón con desarmador (imagen: tapon_fluxometro)
  * Cerrar tornillo de paso Helux girando a la derecha (imagen: orientacion_valvula)
  * Si no se puede: necesitan técnico gestor de servicio


REGLAS IMPORTANTES:
- Siempre saluda con el nombre del usuario una vez que lo sepas
- Pregunta el nombre al inicio si no lo conoces
- Pregunta a qué Familia pertenece y a qué unidad de negocio/estación
- Guía paso a paso, no des toda la información de golpe
- Haz preguntas de verificación (¿Sí/No?, ¿Cómo se ve?, etc.)
- Cuando necesites mostrar una imagen, escribe exactamente: [IMAGEN:nombre_imagen]
- Cuando necesites mostrar el video, escribe: [VIDEO:video_interfaz]
- Las imágenes disponibles son: medidor_luz, tipo_pastillas, pastilla_abb, pastilla_scuard, fusibles_poste, boton_paro_emergencia, botones_inicio_paro, monitor_kiosko, reguladores, llave_paso_pequena, sapito_en_wc, sapito_de_wc, ajuste_cadena_sapito, tapon_fluxometro, fluxometro_pedal, fluxometro_palanca, orientacion_valvula, quemador_inferior, limpieza_quemador, quitar_quemador_inferior, sensor_llama_inferior, quitar_tapa_sensores, donde_tomar_sensores
- Para reiniciar dispensarios: SIEMPRE usar pastilla individual, NUNCA el paro de emergencia general salvo emergencia real
- Si el problema no se puede resolver: indica levantar ticket, contactar al coordinador o al equipo de mantenimiento
- Sé empático y alentador cuando el usuario resuelve el problema
- Recuerda al final que pueden escribir "Hola" para una nueva consulta"""

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Almacena el historial de conversaciones por usuario
conversaciones = {}

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user_id = update.effective_user.id
    conversaciones[user_id] = []
    await update.message.reply_text(
        "¡Hola! 👋 Soy Mantestito, tu asistente de mantenimiento 🧰\n"
        "Estoy aquí para ayudarte a resolver problemas comunes de manera rápida.\n\n"
        "¿Cómo te llamas?"
    )


async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todos los mensajes del usuario"""
    user_id = update.effective_user.id
    mensaje = update.message.text

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

        # Agregar respuesta al historial
        conversaciones[user_id].append({
            "role": "assistant",
            "content": respuesta_completa
        })

        # Procesar la respuesta para detectar imágenes y videos
        await procesar_y_enviar(update, context, respuesta_completa)

    except Exception as e:
        logger.error(f"Error al llamar a Claude: {e}")
        await update.message.reply_text(
            "Lo siento, tuve un problema técnico. Por favor intenta de nuevo. 🔧"
        )


async def procesar_y_enviar(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str):
    """Procesa el texto y envía imágenes/videos cuando se indique"""
    import re

    # Dividir el texto en partes: texto normal e instrucciones de imagen/video
    partes = re.split(r'(\[IMAGEN:[^\]]+\]|\[VIDEO:[^\]]+\])', texto)

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


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /reset para reiniciar la conversación"""
    user_id = update.effective_user.id
    conversaciones[user_id] = []
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

    logger.info("🤖 Mantestito Bot iniciado!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

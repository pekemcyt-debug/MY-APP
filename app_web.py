import streamlit as st
import json
import random
import time

# 1. Configuración de página e interfaz oscura base
st.set_page_config(page_title="Simulador CNV", page_icon="📈", layout="centered")

# Estilos CSS inyectados
st.markdown("""
    <style>
    /* Agrandar el texto de la pregunta */
    .pregunta-text {
        font-size: 1.3rem !important;
        font-weight: 600 !important;
        line-height: 1.6 !important;
        color: #FFFFFF;
        margin-bottom: 1.8rem;
    }
    /* Encabezado de estadísticas superior */
    .stats-container {
        display: flex;
        justify-content: space-between;
        font-size: 0.95rem;
        color: #A0A0A0;
        margin-bottom: 1.2rem;
        border-bottom: 1px solid #333;
        padding-bottom: 0.6rem;
    }
    .stat-correctas { color: #4CAF50; font-weight: bold; }
    .stat-incorrectas { color: #F44336; font-weight: bold; }
    
    /* PANEL LATERAL FLOTANTE PARA LA EXPLICACIÓN */
    .panel-flotante {
        position: fixed;
        top: 15%; 
        right: 1%; /* Margen derecho relativo para adaptarse a la pantalla */
        width: 320px;
        max-height: 75vh;
        overflow-y: auto;
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-top: 4px solid #4CAF50; 
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: -4px 4px 15px rgba(0,0,0,0.8); 
        z-index: 999999 !important; /* Prioridad máxima absoluta para que Streamlit no lo tape */
        font-size: 0.95rem;
        line-height: 1.5;
        color: #E0E0E0;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def cargar_datos():
    with open("banco_multiple_choice.json", "r", encoding="utf-8") as f:
        datos = json.load(f, strict=False)
    if isinstance(datos, dict) and "preguntas" in datos: return datos["preguntas"]
    if isinstance(datos, dict) and "lista" in datos: return datos["lista"]
    return datos

preguntas_banco = cargar_datos()

# Inicializar estados de la sesión persistentes por ID de pregunta
if "index_pregunta" not in st.session_state:
    st.session_state.index_pregunta = 0
    st.session_state.correctas = 0
    st.session_state.incorrectas = 0
    st.session_state.preguntas_partida = []
    
    st.session_state.historial_opciones = {}   
    st.session_state.historial_respuestas = {} 
    st.session_state.auto_avanzado = set() 

# --- PANTALLA 1: MENÚ DE INICIO ---
if not st.session_state.preguntas_partida:
    st.title("📈 Simulador de Examen CNV")
    
    modulos = sorted(list(set(p["modulo"] for p in preguntas_banco if "modulo" in p)))
    modulo_sel = st.selectbox("1. Seleccioná el módulo para tu examen:", ["Modo Examen (Todos los Módulos)"] + modulos)
    
    es_modo_examen = (modulo_sel == "Modo Examen (Todos los Módulos)")
    
    # Restringir las opciones dependiendo del modo
    if es_modo_examen:
        opciones_cantidad = ["10 preguntas", "35 preguntas", "60 preguntas (10 por cada módulo)", "100 preguntas"]
    else:
        opciones_cantidad = ["10 preguntas", "35 preguntas", "Módulo completo"]
    
    cantidad_sel = st.selectbox("2. Cantidad de preguntas de la sesión:", opciones_cantidad)
    
    if st.button("Comenzar Examen 🚀", use_container_width=True):
        
        if es_modo_examen:
            if "60 preguntas" in cantidad_sel:
                # Lógica estricta de 10 preguntas por cada módulo
                pool = []
                for mod in modulos:
                    preguntas_mod = [p for p in preguntas_banco if p.get("modulo") == mod]
                    random.shuffle(preguntas_mod)
                    pool.extend(preguntas_mod[:10])
                random.shuffle(pool) # Mezclamos el mazo final completo
                limite = len(pool)
            else:
                # Mezclado normal de todo el banco para 10, 35 o 100
                pool = preguntas_banco.copy()
                random.shuffle(pool)
                if "10 preguntas" in cantidad_sel:
                    limite = 10
                elif "35 preguntas" in cantidad_sel:
                    limite = 35
                elif "100 preguntas" in cantidad_sel:
                    limite = 100
                else:
                    limite = len(pool)
        else:
            # Lógica para un módulo específico
            pool = [p for p in preguntas_banco if p.get("modulo") == modulo_sel]
            random.shuffle(pool)
            
            if "10 preguntas" in cantidad_sel:
                limite = 10
            elif "35 preguntas" in cantidad_sel:
                limite = 35
            else:
                limite = len(pool)
            
        st.session_state.preguntas_partida = pool[:limite]
        st.session_state.index_pregunta = 0
        st.session_state.correctas = 0
        st.session_state.incorrectas = 0
        st.session_state.historial_opciones = {}
        st.session_state.historial_respuestas = {}
        st.session_state.auto_avanzado = set()
        st.rerun()

# --- PANTALLA 2: SIMULADOR ACTIVO ---
else:
    idx = st.session_state.index_pregunta
    total_partida = len(st.session_state.preguntas_partida)
    
    if st.button("⬅️ Abandonar y Volver al Inicio", key="btn_volver_inicio"):
        st.session_state.preguntas_partida = []
        st.rerun()
        
    if idx < total_partida:
        p = st.session_state.preguntas_partida[idx]
        
        if idx not in st.session_state.historial_opciones:
            incorrectas = [p[k] for k in p if k.startswith("incorrecta_") and p[k]]
            incorrectas_partida = random.sample(incorrectas, min(3, len(incorrectas)))
            opciones = incorrectas_partida + [p["respuesta_correcta"]]
            random.shuffle(opciones)
            st.session_state.historial_opciones[idx] = opciones

        orden_opciones = st.session_state.historial_opciones[idx]
        respondido = idx in st.session_state.historial_respuestas
        opcion_seleccionada = st.session_state.historial_respuestas.get(idx, None)

        # --- LÓGICA DE FONDO ROJO PARA ERRORES ---
        if respondido and opcion_seleccionada != p["respuesta_correcta"]:
            st.markdown("""
                <style>
                .stApp, [data-testid="stAppViewContainer"] {
                    background-color: #2B0808 !important; /* Rojo profundo */
                    transition: background-color 0.4s ease;
                }
                [data-testid="stHeader"] {
                    background-color: transparent !important;
                }
                </style>
            """, unsafe_allow_html=True)
        # -----------------------------------------

        # 1. Estadísticas
        st.markdown(
            '<div class="stats-container">'
            f'<div>Respuestas: {idx + 1} de {total_partida}</div>'
            '<div>'
            f'<span class="stat-correctas">Correctas: {st.session_state.correctas}</span> &nbsp;|&nbsp; '
            f'<span class="stat-incorrectas">Incorrectas: {st.session_state.incorrectas}</span>'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )
        
        # 2. Enunciado
        st.markdown(f'<p class="pregunta-text">{p["pregunta"]}</p>', unsafe_allow_html=True)
        
        # 3. Botones bloqueados al tamaño exacto
        for opcion in orden_opciones:
            if respondido:
                if opcion == p["respuesta_correcta"]:
                    fondo_color = "#1B5E20" 
                    borde_color = "#4CAF50" 
                else:
                    fondo_color = "#B71C1C" 
                    borde_color = "#F44336" 
                    
                st.markdown(f"""
                    <div style="
                        box-sizing: border-box;
                        width: 100%;
                        background-color: {fondo_color}; 
                        border: 1px solid {borde_color}; 
                        color: #FFFFFF; 
                        border-radius: 0.5rem; 
                        text-align: center; 
                        margin-bottom: 16px; 
                        font-size: 16px; 
                        font-weight: 400; 
                        font-family: 'Source Sans Pro', sans-serif;
                        min-height: 38.4px; 
                        padding: 0.25rem 0.75rem; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center; 
                    ">
                        {opcion}
                    </div>
                """, unsafe_allow_html=True)
            else:
                if st.button(opcion, key=f"btn_{idx}_{opcion}", use_container_width=True):
                    st.session_state.historial_respuestas[idx] = opcion
                    if opcion == p["respuesta_correcta"]:
                        st.session_state.correctas += 1
                    else:
                        st.session_state.incorrectas += 1
                    st.rerun()

        # 4. Panel lateral flotante (Apuntando directo a "explicacion")
        if respondido:
            if "explicacion" in p and p["explicacion"]:
                st.markdown(
                    '<div class="panel-flotante">'
                    '<strong>📚 Justificación Teórica:</strong><br><br>'
                    f'{p["explicacion"]}'
                    '</div>',
                    unsafe_allow_html=True
                )
        
        # --- NAVEGACIÓN MANUAL ---
        col_izq, col_der = st.columns(2)
        with col_izq:
            if idx > 0:
                if st.button("⬅️ Pregunta Anterior", use_container_width=True):
                    st.session_state.index_pregunta -= 1
                    st.rerun()
        with col_der:
            if respondido:
                if st.button("Siguiente Pregunta ➡️", use_container_width=True):
                    st.session_state.index_pregunta += 1
                    st.rerun()
        
        # --- MOTOR DE AVANCE AUTOMÁTICO ---
        if respondido and idx not in st.session_state.auto_avanzado:
            caracteres_totales = len(p["pregunta"]) + len(p["respuesta_correcta"]) + len(p.get("explicacion", ""))
            tiempo_lectura = max(4.0, 4.0 + (caracteres_totales / 75.0))
            
            placeholder_timer = st.empty()
            for restante in range(int(tiempo_lectura), 0, -1):
                placeholder_timer.caption(f"Avanzando automáticamente en {restante} segundos...")
                time.sleep(1)
            
            placeholder_timer.empty()
            st.session_state.auto_avanzado.add(idx)
            st.session_state.index_pregunta += 1
            st.rerun()

    else:
        st.balloons()
        st.title("🏆 Práctica Completada")
        st.metric("Porcentaje de Aciertos", f"{(st.session_state.correctas / total_partida)*100:.1f}%")
        st.write(f"Lograste **{st.session_state.correctas}** respuestas correctas de un pozo de **{total_partida}**.")
        
        # Recopilación y muestra de errores al finalizar el test (Sin mostrar el ID)
        if st.session_state.incorrectas > 0:
            st.markdown("---")
            st.markdown("### 📝 Repaso de Errores")
            st.write("Acá tenés el detalle de las preguntas donde te equivocaste, para que puedas repasarlas:")
            st.markdown("---")
            
            for i, p_error in enumerate(st.session_state.preguntas_partida):
                opcion_elegida = st.session_state.historial_respuestas.get(i)
                if opcion_elegida and opcion_elegida != p_error["respuesta_correcta"]:
                    modulo_pregunta = p_error.get("modulo", "Sin módulo asignado")
                    
                    st.markdown(f"**Módulo:** *{modulo_pregunta}*")
                    st.markdown(f"**Enunciado:** {p_error['pregunta']}")
                    st.markdown(f"❌ **Tu respuesta:** {opcion_elegida}")
                    st.markdown(f"✅ **Respuesta correcta:** {p_error['respuesta_correcta']}")
                    
                    if "explicacion" in p_error and p_error["explicacion"]:
                        st.info(f"📚 **Explicación:** {p_error['explicacion']}")
                    
                    st.markdown("---")

        if st.button("Volver al Menú Principal 🔄", use_container_width=True):
            st.session_state.preguntas_partida = []
            st.rerun()
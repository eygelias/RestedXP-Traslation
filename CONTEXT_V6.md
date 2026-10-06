# RXP Translator V6 - Context & Architecture

Este repositorio contiene la V6 del Traductor de RestedXP.
Principales cambios recientes:
1. **Guas Multi-Expansin:** `zones_all.json` ahora almacena las zonas en un diccionario categorizado por expansin (`all`, `forever`, `classic`). `translate_guides.py` compila los patrones regex dinmicamente segn la expansin.
2. **Interfaz de Addon Inteligente:** `app.py` utiliza una base de datos permanente (`database/addon_ui.json`) con +780 frases en 9 idiomas extraidas de los locales oficiales. Si la frase no est, aplica un sistema de respaldo hbrido con Google Translator y MyMemory.
3. **Estructura Portable:** Para compilar con PyInstaller, `BASE_DIR` siempre resuelve a la ruta del ejecutable real, requiriendo que `/database` y `/cache` estn en la misma carpeta del `.exe`.

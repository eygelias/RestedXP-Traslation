# RestedXP-Traslation V5

Traductor local para guías de **RestedXP / RXPGuides**. Convierte guías `.lua` de inglés a varios idiomas manteniendo la sintaxis interna que RestedXP necesita para funcionar dentro de World of Warcraft Classic.

> Foco principal: traducir guías RestedXP.

## Qué hace

RestedXP-Traslation V5 toma archivos de guía RestedXP y genera versiones traducidas sin romper comandos del addon.

Traduce:

- Texto visible para el jugador: tips, instrucciones, notas, pasos.
- Nombres de NPCs, objetos, items, misiones y spells cuando existe ID o dato fiable.
- Interfaz/localización del addon RXPGuides usando `locale/esES.lua` y strings extraídos.
- 9 locales configurados: `esES`, `esMX`, `ptBR`, `deDE`, `frFR`, `ruRU`, `koKR`, `zhCN`, `zhTW`.

Protege / no traduce:

- Comandos internos: `.goto`, `.zoneskip`, `.subzoneskip`, `.mob`, `.target`, `.unitscan`, etc.
- Condicionales RestedXP: `<<`, clases, facciones, razas.
- IDs: `NPC::123`, `QuestID`, coordenadas, tags.
- Códigos de color WoW: `|c...|r`.
- Zonas dentro de `.goto`, `.zoneskip`, `.subzoneskip`, porque RestedXP las resuelve por nombre inglés o ID.

## Cómo funciona por dentro

Pipeline principal:

```text
Guías originales .lua
        ↓
translate_guides.py
        ↓
LocalDatabase carga databases locales
        ↓
Traducción segura línea por línea
        ↓
validate_output.py revisa sintaxis crítica
        ↓
Guías traducidas listas para copiar al addon
```

### 1. Base de datos local

`build_database.py` construye / actualiza bases locales desde:

- QuestieDB
- RXPGuides locale files
- CMaNGOS / TBC DB
- Overrides manuales

Archivos generados principales:

```text
database/questiedb_es.json      # DB unificada principal
database/merged_esES.json       # DB combinada por locale
database/npcnames_esES.json     # NPCnames de RXPGuides
database/questie_npcs_esES.json # Fallback Questie
database/zones_esES.json        # Zonas
database/spells_es.json         # Spells
database/addon_phrases.json     # Frases interfaz addon
database/manual_overrides.json  # Correcciones manuales
```

### 2. Traducción de guías

`translate_guides.py` lee cada `.lua`, detecta comandos RestedXP y traduce solo la parte segura.

Reglas importantes:

| Comando | Traduce | No traduce |
|---|---|---|
| `.goto Zone,x,y` | Texto después de `>>` | Zona + coordenadas |
| `.zoneskip Zone` | Texto después de `>>` | Zona |
| `.subzoneskip Zone` | Texto después de `>>` | Zona |
| `.mob NPC::ID` | Nombre visible si DB fiable | ID |
| `.target NPC::ID` | Nombre visible si DB fiable | ID |
| `.unitscan NPC::ID` | Nombre visible si DB fiable | ID |
| `#completewith`, `#label`, `#requires` | nada lógico | tokens internos |
| `>> texto` | texto visible | comandos antes de `>>` |

### 3. Validación

`validate_output.py` revisa que la salida no rompa RestedXP:

- Balance de colores `|c` / `|r`.
- Comandos críticos preservados.
- IDs preservados.
- Reporte de entidades no resueltas.

### 4. Interfaz gráfica

`app.py` + `RXP_Guide_Translator_ES.html` crean una GUI local con PyQt5/QWebEngineView:

- Selección de carpeta input/output.
- Selección de idioma.
- Traducción de guías.
- Traducción de interfaz RXPGuides.
- Logs y progreso.

## Estructura del repo

```text
app.py                         # GUI PyQt5
translate_guides.py            # Motor principal de traducción
build_database.py              # Construye DB local
validate_output.py             # Valida salida traducida
translate_addon_interface.py   # Traduce interfaz RXPGuides
locales_config.py              # Idiomas soportados
RXP_Guide_Translator_ES.html   # UI HTML embebida
requirements.txt               # Dependencias Python
build_exe.bat                  # Build Windows con PyInstaller
database/                      # DB local actual
docs/DATABASE_SOURCES.md       # Links oficiales de databases
rxpguides_locale/              # NPCnames/esES extraídos de RXPGuides
input/                         # Coloca aquí guías originales
output/                        # Salida traducida
```

## Tutorial paso a paso

### Paso 1 — Descargar release

Ve a:

```text
https://github.com/eygelias/RestedXP-TraslationV5/releases
```

Descarga el ZIP del release si quieres la app compilada.

Si quieres código fuente:

```bash
git clone https://github.com/eygelias/RestedXP-TraslationV5.git
cd RestedXP-TraslationV5
```

### Paso 2 — Instalar dependencias para modo código

```bash
python -m pip install -r requirements.txt
```

Si solo usas el `.exe` del release, no necesitas esto.

### Paso 3 — Preparar databases

El repo ya trae una copia funcional de `database/`, pero si quieres reconstruirla desde fuentes frescas revisa:

```text
docs/DATABASE_SOURCES.md
```

Descargas principales:

```text
QuestieDB:  https://github.com/Questie/QuestieDB/releases
RXPGuides:  https://github.com/RestedXP/RXPGuides/releases
CMaNGOS:    https://github.com/cmangos/tbc-db
TBC-DB:     https://github.com/TBC-DB/Database
Wowhead:    https://www.wowhead.com/tbc/es/npc=<ID>
```

Luego ejecuta:

```bash
python build_database.py
```

### Paso 4 — Poner guías originales

Coloca tus archivos `.lua` originales de RestedXP en:

```text
input/
```

Ejemplo:

```text
input/The Burning Crusade.lua
```

No se recomienda publicar guías privadas/comerciales dentro del repo.

### Paso 5 — Traducir

Modo GUI:

```bash
python app.py
```

Modo consola:

```bash
python translate_guides.py        # esES por defecto
python translate_guides.py esMX   # español México
python translate_guides.py deDE   # alemán
```

El script usa carpetas fijas junto al proyecto:

```text
input/   -> guías originales
output/  -> guías traducidas
```

### Paso 6 — Validar salida

```bash
python validate_output.py output
```

Revisa reporte en `cache/validation_report.json` si existe.

### Paso 7 — Copiar al addon

Copia los `.lua` traducidos desde:

```text
output/
```

a la carpeta correspondiente de RXPGuides en WoW:

```text
C:\Program Files (x86)\World of Warcraft\_anniversary_\Interface\AddOns\RXPGuides\Guides\
```

Haz backup antes de reemplazar archivos.

## Build EXE Windows

```bash
python -m pip install -r requirements.txt
build_exe.bat
```

Salida esperada:

```text
dist/RXP_Translator_V5/RXP_Translator_V5.exe
```

## Fuentes de datos

Ver documento completo:

```text
docs/DATABASE_SOURCES.md
```

Prioridad recomendada para nombres de NPC:

```text
manual/client verified > Wowhead TBC ES por ID > QuestieDB > RXPGuides NPCnames > CMaNGOS > dejar inglés y reportar
```

## Estado open source

El código base del traductor queda abierto en este repo.

No se incluyen credenciales, tokens ni guías comerciales privadas. Las databases públicas se documentan con links para poder reconstruir el proyecto si se pierde el PC o se cambia de agente.

## Licencia

MIT. Ver `LICENSE`.

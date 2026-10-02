# Database Sources

Fuentes necesarias para reconstruir las bases de datos de RestedXP-Traslation V5.

## Resumen rápido

| Prioridad | Fuente | URL | Uso |
|---:|---|---|---|
| 2 | Wowhead TBC ES | https://www.wowhead.com/tbc/es/npc=<ID> | Verificación externa por ID |
| 3 | QuestieDB | https://github.com/Questie/QuestieDB/releases | DB local principal |
| 4 | RXPGuides | https://github.com/RestedXP/RXPGuides/releases | Locale/NPCnames del addon |
| 5 | CMaNGOS TBC | https://github.com/cmangos/tbc-db | SQL amplio de TBC |
| 6 | TBC-DB | https://github.com/TBC-DB/Database | Alternativa CMaNGOS/TBC |
| 7 | Questie addon | https://github.com/Questie/Questie/releases | Fallback de NPCs |

## 1. QuestieDB

Principal fuente pública para datos Classic.

Links:

```text
Repo:     https://github.com/Questie/QuestieDB
Releases: https://github.com/Questie/QuestieDB/releases
```

Archivo esperado:

```text
QuestieDB-v0.7.0.zip
```

Uso en proyecto:

```text
build_database.py
```

Genera:

```text
database/questiedb_es.json
database/zones_*.json
database/spells_es.json
```

## 2. RXPGuides / RestedXP addon

Fuente para archivos de locale del propio addon.

Links:

```text
GitHub:    https://github.com/RestedXP/RXPGuides/releases
CurseForge: https://www.curseforge.com/wow/addons/restedxp-guide
Descarga:  https://download.restedxp.com/
```

Archivos usados:

```text
locale/NPCnames.lua
locale/esES.lua
locale/subzone_enUS.lua
locale/subzone_esES.lua
locale/localization_strings.lua
```

Destino local:

```text
rxpguides_locale/NPCnames.lua
rxpguides_locale/esES.lua
rxpguides_locale/subzone_enUS.lua
rxpguides_locale/subzone_esES.lua
```

Genera:

```text
database/npcnames_esES.json
database/addon_phrases.json
```

## 3. CMaNGOS TBC DB

Base SQL amplia para TBC 2.4.3. Útil como fallback para criaturas, quests, items y gameobjects.

Links:

```text
TBC DB:       https://github.com/cmangos/tbc-db
Servidor TBC: https://github.com/cmangos/mangos-tbc
```

Archivos SQL relevantes:

```text
creature_template_locale.sql
item_template_locale.sql
quest_template_locale.sql
gameobject_template_locale.sql
```

Genera / alimenta:

```text
database/merged_esES.json
database/merged_esMX.json
database/merged_deDE.json
database/merged_frFR.json
database/merged_ptBR.json
database/merged_koKR.json
database/merged_zhCN.json
database/merged_zhTW.json
```

## 4. TBC-DB alternativa

Otra DB pública para World of Warcraft 2.4.3.

Links:

```text
https://github.com/TBC-DB/Database
```

Uso recomendado:

- Comparar nombres si CMaNGOS no tiene entrada.
- No usar por encima del cliente WoW ni Wowhead para macros `/targetexact`.

## 5. Wowhead TBC Classic en español

Mejor fallback externo por ID cuando un NPC específico falla.

Patrón:

```text
https://www.wowhead.com/tbc/es/npc=<ID>
```

Ejemplos verificados:

```text
https://www.wowhead.com/tbc/es/npc=7856  -> Filibustero de los Mares del Sur
https://www.wowhead.com/tbc/es/npc=113   -> Jabalí colmillopétreo
https://www.wowhead.com/tbc/es/npc=2185  -> Trillador de la Costa Oscura
```

Nota:

- Usar por ID, no por búsqueda de texto libre.
- No hacer fuzzy matching para macros. Si no hay ID fiable, dejar inglés y reportar.

## 6. Cliente WoW en vivo

Fuente más fiable para el nombre que el cliente acepta.

Método usado por RXPNameFixer:

```lua
GameTooltip:SetHyperlink("unit:Creature-0-0-0-0-" .. npcID)
local name = GameTooltipTextLeft1:GetText()
```

Cache:

```text
WTF/Account/<ACCOUNT>/SavedVariables/RXPNameFixer.lua
```

Exportador:

```bash
python addon_companion/RXPNameFixer/export_npc_names.py
```

## Orden recomendado

Para nombres de NPC en guías:

```text
manual_overrides.json
↓
cache verificada del cliente WoW
↓
Wowhead TBC ES por ID
↓
QuestieDB
↓
RXPGuides NPCnames
↓
CMaNGOS / TBC-DB
↓
no traducir, dejar inglés y reportar unresolved
```

## Reconstruir databases

```bash
# 1. Descargar/extraer fuentes públicas indicadas arriba
# 2. Colocar QuestieDB-vX.X.X.zip en raíz del proyecto si se usa zip
# 3. Colocar archivos RXPGuides locale en rxpguides_locale/
# 4. Colocar SQL CMaNGOS/TBC si se va a regenerar merged_*.json
python build_database.py
```

## Seguridad / legal

- No subir tokens, credenciales ni rutas privadas.
- No subir guías comerciales privadas de RestedXP.
- Sí se puede subir código del traductor y documentación de fuentes públicas.

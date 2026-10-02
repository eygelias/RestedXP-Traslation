# RXPGuides `Timers.lua` — fix de autoanclaje

Error corregido:

```text
Action[SetPoint] failed because[Cannot anchor to itself]
RXPGuides/Timers.lua:61
```

## Causa

`LibCandyBar` reutiliza frames ocultos. `BarContainer.bars` podía conservar dos etiquetas apuntando al mismo frame. `SortTimers()` añadía ese frame dos veces y luego ejecutaba conceptualmente:

```lua
bar:SetPoint("TOPLEFT", bar, "BOTTOMLEFT")
```

## Corrección aplicada

1. `SortTimers()` deduplica barras por identidad de frame y elimina etiquetas obsoletas.
2. El anclaje verifica `bar ~= lastBar`, impidiendo directamente `bar:SetPoint(..., bar, ...)`.
3. `StartTimer()` elimina cualquier etiqueta anterior que todavía apunte al frame reutilizado antes de registrar etiqueta nueva.
4. Backup local creado junto al archivo:

```text
Timers.lua.backup-pre-self-anchor-fix
```

## Archivo instalado

```text
C:\Program Files (x86)\World of Warcraft\_anniversary_\Interface\AddOns\RXPGuides\Timers.lua
```

## Verificación

```text
luaparse: OK
```

## Nota

Una actualización de RXPGuides puede reemplazar `Timers.lua`; en ese caso habrá que reaplicar corrección si versión oficial todavía contiene bug.



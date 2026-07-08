#!/bin/bash

# Автоматически определяем папку, где лежит сам скрипт
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GITIGNORE="$SCRIPT_DIR/.gitignore"
SAMPLE_COUNT=5

MARKER_START="# === DATASET SAMPLES START ==="
MARKER_END="# === DATASET SAMPLES END ==="

# Генерируем свежий блок правил
NEW_BLOCK="$MARKER_START"
NEW_BLOCK+=$'\n'

for dir in "$SCRIPT_DIR"/*/; do
    dir="${dir%/}"
    folder_name="${dir##*/}"

    # Пропускаем скрытые папки (начинаются с точки)
    [[ "$folder_name" == .* ]] && continue

    NEW_BLOCK+="${folder_name}/*"
    NEW_BLOCK+=$'\n'
    NEW_BLOCK+="!${folder_name}/"
    NEW_BLOCK+=$'\n'

    counter=0
    for file in "$dir"/*; do
        [ -f "$file" ] || continue
        [ $counter -ge $SAMPLE_COUNT ] && break
        NEW_BLOCK+="!${folder_name}/${file##*/}"
        NEW_BLOCK+=$'\n'
        ((counter++))
    done
done

NEW_BLOCK+="$MARKER_END"

# Обновляем .gitignore
if [ -f "$GITIGNORE" ] && grep -qF "$MARKER_START" "$GITIGNORE"; then
    TEMP_FILE=$(mktemp)
    sed "/$MARKER_START/,/$MARKER_END/d" "$GITIGNORE" > "$TEMP_FILE"
    [ -s "$TEMP_FILE" ] && [ "$(tail -c1 "$TEMP_FILE")" != "" ] && echo "" >> "$TEMP_FILE"
    echo "$NEW_BLOCK" >> "$TEMP_FILE"
    mv "$TEMP_FILE" "$GITIGNORE"
else
    [ -f "$GITIGNORE" ] && [ -s "$GITIGNORE" ] && [ "$(tail -c1 "$GITIGNORE")" != "" ] && echo "" >> "$GITIGNORE"
    echo "$NEW_BLOCK" >> "$GITIGNORE"
fi

echo "✓ $GITIGNORE обновлён (первые $SAMPLE_COUNT файлов из каждой папки разрешены)"
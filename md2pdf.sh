#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <input.md>"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_PDF="${INPUT_FILE%.md}.pdf"
OUTPUT_ODT="${INPUT_FILE%.md}.odt"

# Extract the first heading to use as the document title
TITLE=$(grep -m 1 -E '^#+ ' "$INPUT_FILE" | sed -E 's/^#+ +//')

podman run --rm \
    --volume "$(pwd):/data:Z" \
    --userns=keep-id \
    docker.io/pandoc/extra \
    template.md \
    "$INPUT_FILE" \
    -o "$OUTPUT_PDF" \
    --template eisvogel \
    --syntax-highlighting idiomatic \
    --metadata title="$TITLE" \
    --metadata date="$(date +%F)"

podman run --rm \
    --volume "$(pwd):/data:Z" \
    --userns=keep-id \
    docker.io/pandoc/extra \
    template.md \
    "$INPUT_FILE" \
    -o "$OUTPUT_ODT" \
    --reference-doc=reference.odt \
    --metadata title="$TITLE" \
    --metadata date="$(date +%F)"

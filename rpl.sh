#!/bin/bash
OLD="$1"
NEW="$2"
echo "$OLD -> $NEW"
egrep -lRZ "\b$OLD\b" templates/ out/rec/js/ | xargs -0 -l sed -i -e "s/\b$OLD\b/$NEW/g"
grep -E "\b$OLD\b" -R templates/ out/rec/js/

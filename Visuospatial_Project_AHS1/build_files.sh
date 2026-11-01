#!/bin/bash
echo "Starting Vercel static build..."

# Ensure static directories and mirror folders exist
mkdir -p staticfiles/static
cp -r static/* staticfiles/ 2>/dev/null || true
cp -r static/* staticfiles/static/ 2>/dev/null || true

echo "Static files ready in staticfiles/ and staticfiles/static/!"


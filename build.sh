#!/usr/bin/env bash
# Render runs this script on every deploy (Build Command: bash build.sh).
# "set -o errexit" stops the build at the first failing command, so a broken
# deploy never goes live.
set -o errexit

# 1. Install the Python libraries listed in requirements.txt.
pip install -r requirements.txt

# 2. Copy all CSS/JS into staticfiles/ for WhiteNoise to serve.
python manage.py collectstatic --no-input

# 3. Create or update the database tables in Neon. Safe to run every time:
#    migrations that have already been applied are skipped.
python manage.py migrate --no-input

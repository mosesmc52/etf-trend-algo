#!/bin/bash
set -e

echo "🧱 Creating SQLite DB..."
python -c '
from database import init_db
init_db()
'

echo "📥 Ingesting equities once..."
python ingest.py

echo "📝 Creating cron log..."
touch /var/log/cron.log

echo "🌐 Exporting environment..."
declare -p | grep -Ev 'BASHOPTS|BASH_VERSINFO|EUID|PPID|SHELLOPTS|UID' > /container.env

echo "📆 Writing scheduler..."
cat <<EOF > /app/scheduler.txt
SHELL=/bin/bash
BASH_ENV=/container.env
PATH=/usr/local/bin:/usr/bin:/bin
0 11 * * 3 cd /app && poetry run python ingest.py && poetry run python algo.py >> /var/log/cron.log 2>&1

EOF

echo "📌 Installing crontab:"
cat /app/scheduler.txt
crontab /app/scheduler.txt

echo "📋 Confirming crontab:"
crontab -l

echo "🚀 Starting cron..."
cron -f

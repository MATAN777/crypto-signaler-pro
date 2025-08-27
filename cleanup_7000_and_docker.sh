#!/usr/bin/env bash
# ניקוי חיבורים לפורט 7000 + עצירת כל קונטיינרים רצים (ולפי דגלים: מחיקה/Prune)
# שימוש:
#   ./cleanup_7000_and_docker.sh            # עצירה + ניקוי פורט 7000
#   NUKE=1 ./cleanup_7000_and_docker.sh     # כולל מחיקת כל הקונטיינרים + רשתות לא בשימוש + קאש
#   PORT=7000 ./cleanup_7000_and_docker.sh  # לשינוי הפורט (ברירת מחדל 7000)
set -euo pipefail

PORT="${PORT:-7000}"
NUKE="${NUKE:-0}"  # 0 = עדין (עצירה בלבד); 1 = אגרסיבי (מחיקה/Prune)

banner(){ echo -e "\n\033[1;36m==> $*\033[0m"; }

docker info >/dev/null 2>&1 || { echo "Docker אינו פעיל (daemon)."; exit 1; }

banner "ניקוי חיבורים מקומיים לפורט ${PORT}"
if command -v fuser >/dev/null 2>&1; then
  sudo fuser -k "${PORT}"/tcp || true
elif command -v lsof >/dev/null 2>&1; then
  sudo lsof -ti TCP:"${PORT}" -sTCP:LISTEN | xargs -r sudo kill -9
else
  echo "אזהרה: לא נמצא fuser/lsof; דלג על שלב זה."
fi

banner "עצירת כל הקונטיינרים הרצים (ללא מחיקה)"
docker ps -q | xargs -r docker stop

if [[ "${NUKE}" == "1" ]]; then
  banner "מצב אגרסיבי NUKE=1: מחיקת כל הקונטיינרים (גם אם לא רצים)"
  docker ps -aq | xargs -r docker rm -f

  banner "ניקוי רשתות לא בשימוש"
  docker network prune -f || true

  banner "ניקוי קאש/תמונות/אובייקטים לא בשימוש (עשוי למחוק Volumes לא בשימוש)"
  docker system prune -af --volumes || true
fi

banner "בדיקה: האם פורט ${PORT} פנוי?"
ss -lntp | awk 'NR==1 || $4 ~ /:'"$PORT"'$/ {print}'

banner "מצב Docker לאחר הניקוי"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

echo -e "\nסיום. (NUKE=${NUKE}, PORT=${PORT})"

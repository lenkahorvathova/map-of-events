PROJECT_DIR="/nlp/projekty/event_map"
REPOSITORY_DIR="${PROJECT_DIR}/repository"
PYTHON_ENV_SCRIPTS_DIR="venv/bin"
LOG_DATA_DIR="data/log"
WEBSITE_DATA_DIR="data/tmp/web"
PUBLIC_HTML_DIR="${PROJECT_DIR}/public_html"

(ls "${REPOSITORY_DIR}" >>/dev/null 2>&1) || (
  echo ">>> '${REPOSITORY_DIR}' doesn't exist!"
  exit
)
cd "${REPOSITORY_DIR}" || exit
export PYTHONPATH="${REPOSITORY_DIR}"

(ls "${PYTHON_ENV_SCRIPTS_DIR}/activate" >>/dev/null 2>&1) || (
  echo ">>> '${REPOSITORY_DIR}/${PYTHON_ENV_SCRIPTS_DIR}/activate' doesn't exist!"
  exit
)
# shellcheck source=./activate
source "${PYTHON_ENV_SCRIPTS_DIR}/activate" || exit

current_time=$(date "+%Y-%m-%d_%H-%M-%S")
mkdir -p "${LOG_DATA_DIR}"
{
  echo "====================$current_time====================="

  echo "============================================================"
  echo "DOWNLOAD CALENDARS:"
  echo "============================================================"
  python3 -u bin/download_calendars.py

  echo "============================================================"
  echo "PARSE CALENDARS:"
  echo "============================================================"
  python3 -u bin/parse_calendars.py

  echo "============================================================"
  echo "DOWNLOAD EVENTS:"
  echo "============================================================"
  python3 -u bin/download_events.py

  echo "============================================================"
  echo "PARSE EVENTS:"
  echo "============================================================"
  python3 -u bin/parse_events.py

  echo "============================================================"
  echo "PROCESS EVENTS' DATETIME:"
  echo "============================================================"
  python3 -u bin/process_datetime.py

  echo "============================================================"
  echo "GEOCODE EVENTS' LOCATION:"
  echo "============================================================"
  python3 -u bin/geocode_location.py

  echo "============================================================"
  echo "EXTRACT EVENTS' KEYWORDS:"
  echo "============================================================"
  python3 -u bin/extract_keywords.py

  echo "============================================================"
  echo "UNIFY EVENTS' TYPES:"
  echo "============================================================"
  python3 -u bin/unify_types.py

  echo "============================================================"
  echo "PREPARE CRAWLER'S STATUS:"
  echo "============================================================"
  python3 -u bin/prepare_crawler_status.py

  echo "============================================================"
  echo "GENERATE WEBSITE'S HTML:"
  echo "============================================================"
  python3 -u bin/generate_html.py

} 2>&1 | tee -a "data/log/cron_process_${current_time}.txt"

mkdir -p "${PUBLIC_HTML_DIR}"
(cp -rpf "${WEBSITE_DATA_DIR}/." "${PUBLIC_HTML_DIR}" >>/dev/null 2>&1) || (
  echo ">>> couldn't copy data from '${WEBSITE_DATA_DIR}/.' to '${PUBLIC_HTML_DIR}'!"
  exit
)

PROJECT_DIR="/nlp/projekty/event_map/repository"
PYTHON_ENV="venv/bin/activate"

(ls "$PROJECT_DIR" >>/dev/null 2>&1) || (
  echo ">>> ${PROJECT_DIR} doesn't exist!"
  exit
)
cd "$PROJECT_DIR" || exit
export PYTHONPATH=$PROJECT_DIR

(ls "$PYTHON_ENV" >>/dev/null 2>&1) || (
  echo ">>> ${PROJECT_DIR}/${PYTHON_ENV} doesn't exist!"
  exit
)
source "$PYTHON_ENV" || exit
current_time=$(date "+%Y-%m-%d_%H-%M-%S")
mkdir -p data/log/

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
} 2>&1 | tee -a data/log/cron_process_"$current_time".txt

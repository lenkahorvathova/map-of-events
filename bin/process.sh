PROJECT_DIR="/home/xhorvat8/map-of-events"
PYTHON_ENV="venv/bin/activate"

(ls "$PROJECT_DIR" >>/dev/null 2>&1) || (
  echo ">>> ${PROJECT_DIR} doesn't exist!"
  exit
)
cd "$PROJECT_DIR"
export PYTHONPATH=$PROJECT_DIR

(ls "$PYTHON_ENV" >>/dev/null 2>&1) || (
  echo ">>> ${PROJECT_DIR}/${PYTHON_ENV} doesn't exist!"
  exit
)
source "$PYTHON_ENV"

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
} 2>&1 | tee -a data/log/cron_process_"$current_time".txt


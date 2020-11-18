PROJECT_DIR="/nlp/projekty/event_map"
REPOSITORY_DIR="${PROJECT_DIR}/repository"
PYTHON_ENV_SCRIPTS_DIR="venv/bin"
LOG_DATA_DIR="data/log"

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
log_file_path="data/log/cron_clean_up_files_${current_time}.txt"
mkdir -p "${LOG_DATA_DIR}"
{
  echo "====================$current_time====================="
  echo "============================================================"
  echo "CLEAN UP HTML FILES:"
  echo "============================================================"
  python3 -u bin/delete_html_files.py 366 --log-file "${log_file_path}"
} >>"${log_file_path}"

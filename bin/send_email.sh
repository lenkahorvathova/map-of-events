SUCCESS_EMAIL_FILE=/nlp/projekty/event_map/repository/data/tmp/email.txt
FAILURE_EMAIL_FILE=/nlp/projekty/event_map/repository/resources/email/failure.txt

if [ -f "$SUCCESS_EMAIL_FILE" ]; then
  mail -s "Weekly reminder" -S "from=Map of Events <no-reply>" 445291@mail.muni.cz <${SUCCESS_EMAIL_FILE}
else
  mail -s "Failed weekly reminder" -S "from=Map of Events <no-reply>" 445291@mail.muni.cz <${FAILURE_EMAIL_FILE}
fi

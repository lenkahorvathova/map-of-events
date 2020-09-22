function prefixWithZero(value) {
    return ('0' + value).slice(-2)
}

function getDateString(date) {
    let day = prefixWithZero(date.getDate());
    let month = prefixWithZero(date.getMonth() + 1);
    let year = date.getFullYear();

    return year + '-' + month + '-' + day;
}

function getTimeString(date) {
    let hours = prefixWithZero(date.getHours());
    let minutes = prefixWithZero(date.getMinutes());

    return hours + ':' + minutes;
}

function setValuesOfDatetimePickers(startDate, startTime, endDate, endTime) {
    if (startDate && endDate && endDate < startDate) {
        throw "end_date is before start_date!"
    }
    if (startDate && endDate && startTime && endTime && startDate === endDate && endTime < startTime) {
        throw "end_time is before start_time on the same date!"
    }

    let startDatePicker = document.getElementById('js-search-form__datetime__start__date-picker');
    let startTimePicker = document.getElementById('js-search-form__datetime__start__time-picker');
    let endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    let endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');

    startDatePicker.value = startDate;
    startDatePicker.min = startDate;
    startTimePicker.value = startTime;

    endDatePicker.value = endDate;
    endDatePicker.min = startDate;
    endTimePicker.value = endTime;
    if (startDatePicker.value === endDatePicker.value) {
        endTimePicker.min = startTime;
    }
}

function getAllFutureEvents() {
    let date = new Date();

    let today = getDateString(date);
    let now = getTimeString(date);

    setValuesOfDatetimePickers(today, now, null, null);
}

function setTodayIntoDatetimePickers() {
    enableEnd();

    let date = new Date();
    let today = getDateString(date);
    let now = getTimeString(date);

    setValuesOfDatetimePickers(today, now, today, null);
}

function setTomorrowIntoDatetimePickers() {
    enableEnd();

    let date = new Date();
    date.setDate(date.getDate() + 1);
    let tomorrow = getDateString(date);

    setValuesOfDatetimePickers(tomorrow, null, tomorrow, null);
}

function setNext10DaysIntoDatetimePickers() {
    enableEnd();

    let startDate = document.getElementById('js-search-form__datetime__start__date-picker').value;
    let startTime = document.getElementById('js-search-form__datetime__start__time-picker').value;

    let date = new Date(startDate + ' ' + (startTime !== null ? startTime : '00:00'));
    date.setDate(date.getDate() + 10);
    let dateIn10Days = getDateString(date);

    setValuesOfDatetimePickers(startDate, startTime, dateIn10Days, null);
}

function enableEnd() {
    let allFutureEventsCheckbox = document.getElementById('js-search-form__datetime__end__checkbox');
    let endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    let endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');

    allFutureEventsCheckbox.checked = true;
    endDatePicker.disabled = false;
    endTimePicker.disabled = false;
}

function disableEndAndGetAllEventsFromStart() {
    let startDate = document.getElementById('js-search-form__datetime__start__date-picker').value;
    let startTime = document.getElementById('js-search-form__datetime__start__time-picker').value;

    setValuesOfDatetimePickers(startDate, startTime, null, null);

    let allFutureEventsCheckbox = document.getElementById('js-search-form__datetime__end__checkbox');
    let endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    let endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');

    endDatePicker.disabled = allFutureEventsCheckbox.checked !== true;
    endTimePicker.disabled = allFutureEventsCheckbox.checked !== true;
}

function setEndTimePickerMin(newMin) {
    let endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');
    endTimePicker.min = newMin;
}

function handleOnChangeOfStartDatePicker(startDatePicker) {
    let endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    endDatePicker.min = startDatePicker.value;

    if (startDatePicker.value === endDatePicker.value) {
        let startTimePicker = document.getElementById('js-search-form__datetime__start__time-picker');
        setEndTimePickerMin(startTimePicker.value);
    } else {
        setEndTimePickerMin("");
    }
}

function handleOnChangeOfEndDatePicker(endDatePicker) {
    let startDatePicker = document.getElementById('js-search-form__datetime__start__date-picker');

    if (startDatePicker.value === endDatePicker.value) {
        let startTimePicker = document.getElementById('js-search-form__datetime__start__time-picker');
        setEndTimePickerMin(startTimePicker.value);
    } else {
        setEndTimePickerMin("");
    }
}

function handleOnChangeOfStartTimePicker(startTimePicker) {
    let startDatePicker = document.getElementById('js-search-form__datetime__start__date-picker');
    let endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');

    if (startDatePicker.value === endDatePicker.value) {
        setEndTimePickerMin(startTimePicker.value);
    }
}

function handleRadioButtonsForGPSInput() {
    let gpsRadioButton = document.getElementById('js-search-form__location__options__gps');
    let gpsLongitude = document.getElementById('js-search-form__location__gps-longitude');
    let gpsLatitude = document.getElementById('js-search-form__location__gps-latitude');
    let radiusSpecification = document.getElementById('js-search-form__location__radius');

    gpsLongitude.disabled = gpsRadioButton.checked !== true;
    gpsLatitude.disabled = gpsRadioButton.checked !== true;
    gpsLongitude.required = gpsRadioButton.checked === true;
    gpsLatitude.required = gpsRadioButton.checked === true;
    radiusSpecification.disabled = gpsRadioButton.checked !== true;
}

function handleFormSubmission(event, data) {
    event.preventDefault();
    let eventsData = filterEventsAndLoadMap(data);
    reloadEventsTable(eventsData)
}

function reloadEventsTable(eventsData) {
    let datatable = $('#js-events-table').DataTable();
    datatable.clear();
    datatable.rows.add(eventsData);
    datatable.draw();
}

function handleEventDetailsModal(event, element) {
    let datatable = $('#js-events-table').DataTable();
    let eventData = datatable.row($(element).parents('tr')).data();
    showEventDetailsModal(eventData);
}

function handleEventDetailsCard(eventId) {
    let eventData = data[eventId];
    showEventDetailsModal(eventData);
}

function showEventDetailsModal(eventData) {
    if (eventData !== null) {
        let title = document.getElementById('event-title');
        title.innerText = eventData['title'];

        let defaultLocation = document.getElementById('event-default-location');
        defaultLocation.hidden = true;
        if (eventData['online']) {
            defaultLocation.hidden = false;
            defaultLocation.outerHTML = `<i id="event-online" class="fa fa-check-circle text-primary"> ONLINE</i>`
        } else {
            defaultLocation.hidden = false;
            defaultLocation.innerText = eventData['default_location'];
        }

        let datetime = document.getElementById('event-datetime');
        datetime.innerText = eventData['table_start_datetime'];
        if (eventData['table_end_datetime']) {
            datetime.innerText += ' - ' + eventData['table_end_datetime'];
        }

        let perex = document.getElementById('event-perex');
        perex.innerText = eventData['perex'];

        let location = document.getElementById('event-location');
        if (eventData['location']) {
            location.innerText = eventData['location'];
        } else {
            location.innerHTML = `<i>unknown</i>`;
        }

        let gps = document.getElementById('event-gps');
        let geocoded = document.getElementById('event-geocoded');
        if (eventData['gps'] !== null) {
            gps.innerText = eventData['gps'];
            geocoded.innerText = "";
        } else {
            gps.innerText = eventData['geocoded_gps'];

            if (eventData['has_default']) {
                geocoded.innerText = '(' + eventData['default_location'] + ')';
            } else {
                geocoded.innerText = '(' + eventData['municipality'] + ', ' + eventData['district'] + ')';
            }
        }

        let organizer = document.getElementById('event-organizer');
        if (eventData['organizer']) {
            organizer.innerText = eventData['organizer'];
        } else {
            organizer.innerHTML = `<i>unknown</i>`;
        }

        let source = document.getElementById('event-calendar-url');
        source.href = eventData['calendar_url'];
        source.innerText = eventData['calendar_url'];

        let fetchedAt = document.getElementById('event-downloaded-at');
        fetchedAt.innerText = new Date(eventData['calendar_downloaded_at']).toLocaleString();

        let eventButton = document.getElementById('event-url');
        eventButton.href = eventData['event_url'];
    }
}

function zoomToEventGPS(event, element) {
    let data = $('#js-events-table').DataTable().row($(element).parents('tr')).data();

    let gps = data["gps"];
    if (gps === null) {
        gps = data["geocoded_gps"];
    }
    let dataCoordinates = gps.split(',').map(coordinate => parseFloat(coordinate));
    let coords = SMap.Coords.fromWGS84(dataCoordinates[1], dataCoordinates[0]);

    map.setCenterZoom(coords, 18);
}

function setupEventsTable(eventsData) {
    $('#js-events-table').DataTable({
        "data": eventsData,
        columns: [
            {data: 'title'},
            {data: 'table_location'},
            {data: 'table_start_datetime'},
            {data: 'table_end_datetime'},
            {data: null}
        ],
        "order": [[2, "asc"]],
        "responsive": true,
        "select": true,
        "columnDefs": [{
            "targets": -1,
            "data": null,
            "orderable": false,
            "defaultContent": `
                <div style="text-align: center; white-space: nowrap">
                    <button type="button" id="event-detail-btn" class="btn btn-secondary btn-sm"
                            data-toggle="modal" data-target="#eventDetails" onclick="handleEventDetailsModal(event, this)"
                            title="Show event's details.">
                        <i class="fa fa-info-circle"></i>
                    </button>
                    <button type="button" id="event-target-btn" class="btn btn-secondary btn-sm"
                            onclick="zoomToEventGPS(event, this)" title="Zoom event's location on the map.">
                        <i class="fa fa-bullseye"></i>
                    </button>
                </div>`
        }]
    });

    $('.dataTables_length').addClass('bs-select');
}

function handleFirstLoad(data) {
    getAllFutureEvents();
    let eventsData = filterEventsAndLoadMap(data);
    setupEventsTable(eventsData);
}
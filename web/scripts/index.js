function handleLocationRadioButtonsClick() {
    const gpsRadioButton = document.getElementById('sidebar__form--filter__location__options--gps');
    const gpsLatitude = document.getElementById('sidebar__form--filter__location__gps--latitude');
    const gpsLongitude = document.getElementById('sidebar__form--filter__location__gps--longitude');
    const radius = document.getElementById('sidebar__form--filter__location__radius');

    gpsLongitude.disabled = gpsRadioButton.checked !== true;
    gpsLatitude.disabled = gpsRadioButton.checked !== true;
    gpsLongitude.required = gpsRadioButton.checked === true;
    gpsLatitude.required = gpsRadioButton.checked === true;
    radius.disabled = gpsRadioButton.checked !== true;
}

function handleOngoingCheckboxClick(ongoingCheckbox) {
    const longTermCheckbox = document.getElementById('sidebar__form--filter__datetime__including-checkboxes--long-term');
    longTermCheckbox.disabled = ongoingCheckbox.checked !== true;
}

function copyGPSValueIntoSearchForm(itemId) {
    const itemLatitude = document.getElementById(`modal--gps-table__table__latitude--${itemId}`).innerText;
    const itemLongitude = document.getElementById(`modal--gps-table__table__longitude--${itemId}`).innerText;

    const gpsRadioButton = document.getElementById('sidebar__form--filter__location__options--gps');
    const gpsLatitude = document.getElementById('sidebar__form--filter__location__gps--latitude');
    const gpsLongitude = document.getElementById('sidebar__form--filter__location__gps--longitude');
    const radius = document.getElementById('sidebar__form--filter__location__radius');

    gpsLatitude.disabled = false;
    gpsLatitude.required = true;
    gpsLatitude.value = itemLatitude;
    gpsRadioButton.checked = true;
    gpsLongitude.disabled = false;
    gpsLongitude.required = true;
    gpsLongitude.value = itemLongitude;
    radius.disabled = false;

    document.getElementById('modal--gps-table__close-button').click();
}

function addRowToGPSTable(itemId, item) {
    const tbody = document.querySelector('#modal--gps-table__table > tbody');
    const tr = tbody.insertRow();
    tr.insertCell(0).outerHTML = `<th scope="row">${itemId}</th>`;

    const td1 = tr.insertCell();
    td1.textContent = item['label'];

    const td2 = tr.insertCell();
    td2.textContent = item['coords']['y'];
    td2.id = `modal--gps-table__table__latitude--${itemId}`;

    const td3 = tr.insertCell();
    td3.textContent = item['coords']['x'];
    td3.id = `modal--gps-table__table__longitude--${itemId}`;

    const td4 = tr.insertCell();
    td4.innerHTML = `<button type="button" class="btn btn-primary btn-block btn-sm" 
                             onclick="copyGPSValueIntoSearchForm(${itemId})">Use</button>`;
}

function addMessageRowToGPSTable(message) {
    const tbody = document.querySelector('#modal--gps-table__table > tbody');
    const tr = tbody.insertRow();
    tr.insertCell().outerHTML = `<td colspan="5" class="centered-cell-content">${message}</td>`;
}

function clearTbodyOfGPSTable() {
    const oldTbody = document.querySelector('#modal--gps-table__table > tbody');
    if (oldTbody) oldTbody.remove();

    const table = document.getElementById('modal--gps-table__table');
    const newTbody = document.createElement('tbody');
    table.appendChild(newTbody);
}

function geocodeCallback(geocoder) {
    const locationResults = geocoder.getResults()[0].results;

    clearTbodyOfGPSTable();

    if (!locationResults.length) {
        addMessageRowToGPSTable("The specified location couldn't be geocoded!");
    }

    for (let i = 0; i < locationResults.length; i++) {
        const item = locationResults[i];
        addRowToGPSTable(i + 1, item);
    }
}

function handleGeocodeFormSubmission(event) {
    event.preventDefault();

    const queryValue = document.getElementById('sidebar__form--geocode__location-query').value;
    const tableTitle = document.getElementById('modal--gps-table__table__title');
    tableTitle.innerHTML = `Value used for the search: <strong>"${queryValue}"</strong>`;

    clearTbodyOfGPSTable();
    addMessageRowToGPSTable("Geocoding the specified location...");

    new SMap.Geocoder(queryValue, geocodeCallback);
}

function reloadEventsTable(eventsData) {
    const eventsDatatable = $('#modal--events-table__table').DataTable();
    eventsDatatable.clear();
    eventsDatatable.rows.add(eventsData);
    eventsDatatable.draw();
}

function handleSearchFormSubmission(event) {
    event.preventDefault();

    const filteredEventsData = filterEventsAndLoadMap();
    reloadEventsTable(filteredEventsData);
    handleSidebarToggleButtonClick();
}

function zoomToEventGPS(element) {
    $('#modal--events-table').modal('hide');
    const eventData = $('#modal--events-table__table').DataTable().row($(element).parents('tr')).data();

    if (eventData['online']) {
        alert("You can't zoom to this event as it is being held online.");
    } else {
        let gps = eventData['gps'];
        if (gps === null) {
            gps = eventData['geocoded_gps'];
        }
        const coordinatesArray = gps.split(',').map(coordinate => parseFloat(coordinate));
        const sMapCoordinates = SMap.Coords.fromWGS84(coordinatesArray[1], coordinatesArray[0]);

        GLB_MAP.setCenterZoom(sMapCoordinates, 18);
    }
}

function parseDatetime(datetimeDict) {
    const dateString = datetimeDict['date'];
    const timeString = datetimeDict['time'];

    let datetime = null;
    if (dateString != null) {
        let datetimeString = dateString;
        if (timeString != null) {
            datetimeString += " " + timeString;
            datetime = new Date(datetimeString).toLocaleString();
        } else {
            datetime = new Date(datetimeString).toLocaleDateString();
        }
    }
    return datetime;
}

function prepareEventDetailsModal(eventData) {
    if (eventData === null) throw `'eventData' is undefined!`;

    const title = document.getElementById('modal--event-details__title');
    title.innerText = eventData['title'];

    const defaultLocation = document.getElementById('modal--event-details__location--default');
    defaultLocation.hidden = true;
    if (eventData['online']) {
        defaultLocation.hidden = false;
        defaultLocation.innerHTML = `<i class="fa fa-check-circle text-primary"> ONLINE</i>`;
    } else if (eventData['default_location']) {
        defaultLocation.hidden = false;
        defaultLocation.innerText = eventData['default_location'];
    }

    const datetime = document.getElementById('modal--event-details__datetime');
    datetime.innerText = parseDatetime(eventData['table_start_datetime']);
    const endDatetime = parseDatetime(eventData['table_end_datetime']);
    if (endDatetime) datetime.innerText += ' - ' + endDatetime;

    const perex = document.getElementById('modal--event-details__perex');
    perex.innerText = eventData['perex'];

    const location = document.getElementById('modal--event-details__location');
    if (eventData['location']) {
        location.innerText = eventData['location'];
    } else {
        if (eventData['online']) {
            location.innerHTML = `<i>online</i>`;
        } else {
            location.innerHTML = `<i>unknown</i>`;
        }
    }

    const gps = document.getElementById('modal--event-details__gps');
    const geocodedLocation = document.getElementById('modal--event-details__location--geocoded');
    if (eventData['online']) {
        gps.innerText = `online`;
        gps.style = `font-style: italic;`;
        geocodedLocation.innerText = "";
    } else {
        if (eventData['gps'] !== null) {
            gps.innerText = eventData['gps'];
            gps.style = `font-style: normal;`;
            geocodedLocation.innerText = "";
        } else if (eventData['geocoded_gps'] !== null) {
            gps.innerText = eventData['geocoded_gps'];
            gps.style = `font-style: normal;`;

            if (eventData['has_default']) {
                geocodedLocation.innerText = '(' + eventData['default_location'] + ')';
            } else {
                geocodedLocation.innerText = '(' + eventData['municipality'] + ', ' + eventData['district'] + ')';
            }
        }
    }

    const organizer = document.getElementById('modal--event-details__organizer');
    if (eventData['organizer']) {
        organizer.innerText = eventData['organizer'];
    } else {
        organizer.innerHTML = `<i>unknown</i>`;
    }

    const types = document.getElementById('modal--event-details__types');
    types.innerText = eventData['types'].join(', ');

    const keywords = document.getElementById('modal--event-details__keywords');
    if (eventData['keywords'].length !== 0) {
        keywords.innerText = eventData['keywords'].join(', ');
    } else {
        keywords.innerHTML = `<i>unknown</i>`;
    }

    const source = document.getElementById('modal--event-details__calendar--url');
    source.href = eventData['calendar_url'];
    source.innerText = eventData['calendar_url'];

    const fetchedAt = document.getElementById('modal--event-details__calendar--downloaded-at');
    fetchedAt.innerText = new Date(eventData['calendar_downloaded_at']).toLocaleString();

    const eventButton = document.getElementById('modal--event-details__url');
    eventButton.href = eventData['event_url'];
}

function showEventDetailsFromEventsTable(element) {
    const eventsDatatable = $('#modal--events-table__table').DataTable();
    const eventData = eventsDatatable.row($(element).parents('tr')).data();
    document.getElementById('modal--event-details__close-btn').hidden = true;
    document.getElementById('modal--event-details__back-btn').hidden = false;
    $('#modal--events-table').modal('hide');
    prepareEventDetailsModal(eventData);
}

function prepareDatetimeDisplayForEventsTable(date, time) {
    if (date == null) {
        return null;
    } else {
        if (time == null) {
            return new Date(date).toLocaleDateString();
        } else {
            return new Date(date + ' ' + time).toLocaleString();
        }
    }
}

function prepareDatetimeFilterForEventsTable(date, time) {
    if (date == null) {
        return null;
    } else {
        if (time == null) {
            return new Date(date);
        } else {
            return new Date(date + ' ' + time);
        }
    }
}

function initializeEventsTable(eventsData) {
    $('#modal--events-table__table').DataTable({
        data: eventsData,
        columns: [
            {data: 'table_title'},
            {data: 'table_location'},
            {data: 'table_start_datetime'},
            {data: 'table_end_datetime'},
            {data: null}
        ],
        order: [[2, "asc"]],
        responsive: true,
        select: true,
        columnDefs: [
            {
                targets: 2,
                orderable: true,
                render: function (data, type) {
                    if (type === 'display')
                        return prepareDatetimeDisplayForEventsTable(data['date'], data['time']);
                    else
                        return prepareDatetimeFilterForEventsTable(data['date'], data['time']);
                }
            },
            {
                targets: 3,
                orderable: true,
                render: function (data, type) {
                    if (type === 'display')
                        return prepareDatetimeDisplayForEventsTable(data['date'], data['time']);
                    else
                        return prepareDatetimeFilterForEventsTable(data['date'], data['time']);
                }
            },
            {
                targets: -1,
                data: null,
                orderable: false,
                defaultContent: `
                    <div class="centered-cell-content">
                        <button type="button" class="btn btn-secondary btn-sm"
                                data-target="#modal--event-details" onclick="showEventDetailsFromEventsTable(this)" data-toggle="modal"
                                title="Show event's details.">
                            <i class="fa fa-info-circle"></i>
                        </button>
                        <button type="button" class="btn btn-secondary btn-sm"
                                title="Zoom event's location on the map." onclick="zoomToEventGPS(this)">
                            <i class="fa fa-bullseye"></i>
                        </button>
                    </div>`
            }
        ]
    });

    $('.dataTables_length').addClass('bs-select');
}

function initializeTypePicker() {
    const typePicker = $('#sidebar__form--filter__types__select-picker');
    for (let i = 0; i < GLB_EVENT_TYPES.length; i++) {
        const typeName = GLB_EVENT_TYPES[i].charAt(0).toUpperCase() + GLB_EVENT_TYPES[i].slice(1);
        typePicker.append(`<option>${typeName}</option>`);
    }
    typePicker.selectpicker();
}

function initializeKeywordPicker() {
    const keywordPicker = $('#sidebar__form--filter__keywords__select-picker');
    for (let i = 0; i < GLB_EVENT_KEYWORDS.length; i++) {
        keywordPicker.append(`<option>${GLB_EVENT_KEYWORDS[i]}</option>`);
    }
    keywordPicker.selectpicker();
}

function handleSidebarToggleButtonClick() {
    $('#sidebar, #content').toggleClass('active');
    $('.collapse.in').toggleClass('in');
    $('a[aria-expanded=true]').attr('aria-expanded', 'false');
}

function handleFirstLoad() {
    setFutureIntoDatetimePickers();
    initializeTypePicker();
    initializeKeywordPicker();

    const filteredEventsData = filterEventsAndLoadMap();
    initializeEventsTable(filteredEventsData);
}
function handleSidebarToggleButtonClick() {
    $('#sidebar, #content, #sidebar-collapse-btn').toggleClass('active');
    const sidebarBtn = document.getElementById('sidebar-collapse-btn');
    if (sidebarBtn.classList.contains('active')) {
        sidebarBtn.innerHTML = `<i class="fa fa-angle-double-left"></i> ${getLocalizedString('content_search_form_bookmark')}`;
    } else {
        sidebarBtn.innerHTML = `<i class="fa fa-angle-double-right"></i> ${getLocalizedString('content_search_form_bookmark')}`;
    }

    $('.collapse.in').toggleClass('in');
    $('a[aria-expanded=true]').attr('aria-expanded', 'false');
}

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
                             onclick="copyGPSValueIntoSearchForm(${itemId})">
                        ${getLocalizedString('modal_gps_table_button')}
                    </button>`;
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
        addMessageRowToGPSTable(getLocalizedString('modal_gps_table_message'));
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
    tableTitle.innerHTML = `${getLocalizedString('modal_gps_table_used_value')}: <strong>"${queryValue}"</strong>`;

    clearTbodyOfGPSTable();
    addMessageRowToGPSTable(getLocalizedString('modal_gps_table_geocoding'));

    new SMap.Geocoder(queryValue, geocodeCallback);
}

function reloadEventsTable(eventsData) {
    const eventsDatatable = $('#modal--events-table__table').DataTable();
    eventsDatatable.clear();
    eventsDatatable.rows.add(eventsData);
    eventsDatatable.draw();
}

function toggleOnlineOverlay() {
    const onlineSearched = document.getElementById('sidebar__form--filter__location__options--online').checked;
    document.getElementById("content__online-overlay").hidden = !onlineSearched;
}

function handleSearchFormSubmission(event) {
    event.preventDefault();

    const filteredEventsData = filterEventsAndLoadMap();
    toggleOnlineOverlay();
    reloadEventsTable(filteredEventsData);
    handleSidebarToggleButtonClick();
}

function zoomToEventGPS(element) {
    $('#modal--events-table').modal('hide');
    const eventData = $('#modal--events-table__table').DataTable().row($(element).parents('tr')).data();

    if (eventData['online']) {
        alert(getLocalizedString('modal_events_table_online_alert'));
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

function getDatetime(dateString, timeString) {
    let datetime = null;
    if (dateString != null) {
        let datetimeString = dateString;
        if (timeString != null) {
            datetimeString += " " + timeString;
            datetime = new Date(datetimeString.replace(/ /g, "T")).toLocaleString();
        } else {
            datetime = new Date(datetimeString.replace(/ /g, "T")).toLocaleDateString();
        }
    }
    return datetime;
}

function parseDatetime(datetimeTuple) {
    const startDatetime = getDatetime(datetimeTuple[0], datetimeTuple[1]);
    const endDatetime = getDatetime(datetimeTuple[2], datetimeTuple[3]);

    let resultDatetime = startDatetime;
    if (endDatetime) resultDatetime += ' - ' + endDatetime;

    return resultDatetime;
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

    const datetimeUl = document.getElementById('modal--event-details__datetime');
    datetimeUl.innerHTML = "";
    for (let eventDatetime of eventData['datetimes']) {
        const liElement = document.createElement("li");
        liElement.appendChild(document.createTextNode(parseDatetime(eventDatetime)));
        liElement.style.fontWeight = "bold";
        if (eventData.hasOwnProperty('table_start_datetime') && eventData.hasOwnProperty('table_end_datetime')
                && (eventData['table_start_datetime']['date'] === eventDatetime[0]
                        && eventData['table_start_datetime']['time'] === eventDatetime[1]
                        && eventData['table_end_datetime']['date'] === eventDatetime[2]
                        && eventData['table_end_datetime']['time'] === eventDatetime[3])) {
            liElement.classList.add("text-primary");
        }
        datetimeUl.appendChild(liElement);
    }

    const perex = document.getElementById('modal--event-details__perex');
    perex.innerText = eventData['perex'];

    const location = document.getElementById('modal--event-details__location');
    if (eventData['location']) {
        location.innerText = eventData['location'];
    } else {
        if (eventData['online']) {
            location.innerHTML = `<i>online</i>`;
        } else {
            location.innerHTML = `<i>${getLocalizedString('modal_event_details_value_unknown')}</i>`;
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
        organizer.innerHTML = `<i>${getLocalizedString('modal_event_details_value_unknown')}</i>`;
    }

    const types = document.getElementById('modal--event-details__types');
    types.innerText = eventData['types'].join(', ');

    const keywords = document.getElementById('modal--event-details__keywords');
    if (eventData['keywords'].length !== 0) {
        keywords.innerText = eventData['keywords'].join(', ');
    } else {
        keywords.innerHTML = `<i>${getLocalizedString('modal_event_details_value_unknown')}</i>`;
    }

    const source = document.getElementById('modal--event-details__calendar--url');
    source.href = eventData['calendar_url'];
    source.innerText = eventData['calendar_url'];

    const fetchedAt = document.getElementById('modal--event-details__calendar--downloaded-at');
    fetchedAt.innerText = new Date(eventData['calendar_downloaded_at'].replace(/ /g, "T")).toLocaleString();

    const eventButton = document.getElementById('modal--event-details__url');
    eventButton.onclick = function () {
        window.open(eventData['event_url']);
        return false;
    };
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
            return new Date(date.replace(/ /g, "T")).toLocaleDateString();
        } else {
            return new Date((date + ' ' + time).replace(/ /g, "T")).toLocaleString();
        }
    }
}

function prepareDatetimeFilterForEventsTable(date, time) {
    if (date == null) {
        return null;
    } else {
        if (time == null) {
            return new Date(date.replace(/ /g, "T"));
        } else {
            return new Date((date + ' ' + time).replace(/ /g, "T"));
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
                                title="${getLocalizedString('modal_details_btn_title')}">
                            <i class="fa fa-info-circle"></i>
                        </button>
                        <button type="button" class="btn btn-secondary btn-sm" onclick="zoomToEventGPS(this)"
                                title="${getLocalizedString('modal_events_table_zoom_btn_title')}">
                            <i class="fa fa-bullseye"></i>
                        </button>
                    </div>`
            }
        ]
    });

    $('.dataTables_length').addClass('bs-select');
}

function initializeTypePicker() {
    const typePicker = $('#sidebar__form--filter__select-picker--types');
    for (let i = 0; i < GLB_EVENT_TYPES.length; i++) {
        const typeName = GLB_EVENT_TYPES[i].charAt(0).toUpperCase() + GLB_EVENT_TYPES[i].slice(1);
        typePicker.append(`<option>${typeName}</option>`);
    }
    typePicker.selectpicker();
}

function initializeKeywordPicker() {
    const keywordPicker = $('#sidebar__form--filter__select-picker--keywords');
    for (let i = 0; i < GLB_EVENT_KEYWORDS.length; i++) {
        keywordPicker.append(`<option>${GLB_EVENT_KEYWORDS[i]}</option>`);
    }
    keywordPicker.selectpicker();
}

function initializeSelectPickers() {
    initializeTypePicker();
    initializeKeywordPicker();
}

function handleFirstLoad() {
    setFutureIntoDatetimePickers();
    initializeSelectPickers();
    const filteredEventsData = filterEventsAndLoadMap();
    initializeEventsTable(filteredEventsData);
}
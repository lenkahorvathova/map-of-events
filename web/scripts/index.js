function copyGPSValueIntoSearchForm(itemId) {
    const itemLatitude = document.getElementById(`js-gps-table__${itemId}-latitude`).innerText;
    const itemLongitude = document.getElementById(`js-gps-table__${itemId}-longitude`).innerText;

    const gpsRadioButton = document.getElementById('js-search-form__location__options__gps');
    const gpsLongitude = document.getElementById('js-search-form__location__gps-longitude');
    const gpsLatitude = document.getElementById('js-search-form__location__gps-latitude');
    const radius = document.getElementById('js-search-form__location__radius');

    gpsLatitude.disabled = false;
    gpsLatitude.required = true;
    gpsLatitude.value = itemLatitude;
    gpsRadioButton.checked = true;
    gpsLongitude.disabled = false;
    gpsLongitude.required = true;
    gpsLongitude.value = itemLongitude;
    radius.disabled = false;

    document.getElementById('modal-button-close').click();
}

function addRowToGPSTable(number, item) {
    const tbody = document.querySelector('#js-gps-table > tbody');
    const tr = tbody.insertRow();
    tr.insertCell(0).outerHTML = `<th scope="row">${number}</th>`;

    const td1 = tr.insertCell();
    td1.textContent = item['label'];

    const td2 = tr.insertCell();
    td2.textContent = item['coords']['y'];
    td2.id = `js-gps-table__${number}-latitude`;

    const td3 = tr.insertCell();
    td3.textContent = item['coords']['x'];
    td3.id = `js-gps-table__${number}-longitude`;

    const td4 = tr.insertCell();
    td4.innerHTML = `<button type="button" class="btn btn-primary btn-block" onclick="copyGPSValueIntoSearchForm(${number})">Use</button>`;
}

function addMessageRowToGPSTable(message) {
    const tbody = document.querySelector('#js-gps-table > tbody');
    const tr = tbody.insertRow();
    tr.insertCell().outerHTML = `<td colspan="5" style="text-align: center;">${message}</td>`;
}

function clearTbodyOfGPSTable() {
    const oldTbody = document.querySelector('#js-gps-table > tbody');
    if (oldTbody) oldTbody.remove();

    const table = document.getElementById('js-gps-table');
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

    const queryValue = document.getElementById('js-geocode-form__location__municipality').value;
    const tableTitle = document.getElementById('js-gps-table-title');
    tableTitle.innerHTML = `Value used for the search: <strong>"${queryValue}"</strong>`;

    clearTbodyOfGPSTable();
    addMessageRowToGPSTable("Geocoding the specified location...");

    new SMap.Geocoder(queryValue, geocodeCallback);
}

function showEventDetailsFromEventsTable(element) {
    const eventsDatatable = $('#js-events-table').DataTable();
    const eventData = eventsDatatable.row($(element).parents('tr')).data();
    showEventDetailsModal(eventData);
}

function zoomToEventGPS(element) {
    const eventData = $('#js-events-table').DataTable().row($(element).parents('tr')).data();

    let gps = eventData["gps"];
    if (gps === null) {
        gps = eventData["geocoded_gps"];
    }
    const coordinatesArray = gps.split(',').map(coordinate => parseFloat(coordinate));
    const sMapCoordinates = SMap.Coords.fromWGS84(coordinatesArray[1], coordinatesArray[0]);

    GLB_MAP.setCenterZoom(sMapCoordinates, 18);
}

function initializeEventsTable(eventsData) {
    $('#js-events-table').DataTable({
        "data": eventsData,
        columns: [
            {data: 'table_title'},
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
            "defaultContent":
                    `
                        <div style="text-align: center; white-space: nowrap">
                            <button type="button" id="event-detail-btn" class="btn btn-secondary btn-sm"
                                    data-target="#eventDetails" onclick="showEventDetailsFromEventsTable(this)" data-toggle="modal"
                                    title="Show event's details.">
                                <i class="fa fa-info-circle"></i>
                            </button>
                            <button type="button" id="event-target-btn" class="btn btn-secondary btn-sm"
                                    title="Zoom event's location on the map." onclick="zoomToEventGPS(this)">
                                <i class="fa fa-bullseye"></i>
                            </button>
                        </div>
                    `
        }]
    });

    $('.dataTables_length').addClass('bs-select');
}

function reloadEventsTable(eventsData) {
    const eventsDatatable = $('#js-events-table').DataTable();
    eventsDatatable.clear();
    eventsDatatable.rows.add(eventsData);
    eventsDatatable.draw();
}

function handleSearchFormSubmission(event) {
    event.preventDefault();

    const filteredEventsData = filterEventsAndLoadMap();
    reloadEventsTable(filteredEventsData);
}

function handleLocationRadioButtonsClick() {
    const gpsRadioButton = document.getElementById('js-search-form__location__options__gps');
    const gpsLongitude = document.getElementById('js-search-form__location__gps-longitude');
    const gpsLatitude = document.getElementById('js-search-form__location__gps-latitude');
    const radius = document.getElementById('js-search-form__location__radius');

    gpsLongitude.disabled = gpsRadioButton.checked !== true;
    gpsLatitude.disabled = gpsRadioButton.checked !== true;
    gpsLongitude.required = gpsRadioButton.checked === true;
    gpsLatitude.required = gpsRadioButton.checked === true;
    radius.disabled = gpsRadioButton.checked !== true;
}

function showEventDetailsModal(eventData) {
    if (eventData === null) throw `'eventData' is undefined!`;

    const title = document.getElementById('event-title');
    title.innerText = eventData['title'];

    const defaultLocation = document.getElementById('event-default-location');
    defaultLocation.hidden = true;
    if (eventData['online']) {
        defaultLocation.hidden = false;
        defaultLocation.outerHTML = `<i id="event-online" class="fa fa-check-circle text-primary"> ONLINE</i>`;
    } else {
        defaultLocation.hidden = false;
        defaultLocation.innerText = eventData['default_location'];
    }

    const datetime = document.getElementById('event-datetime');
    datetime.innerText = eventData['table_start_datetime'];
    if (eventData['table_end_datetime']) datetime.innerText += ' - ' + eventData['table_end_datetime'];

    const perex = document.getElementById('event-perex');
    perex.innerText = eventData['perex'];

    const location = document.getElementById('event-location');
    if (eventData['location']) {
        location.innerText = eventData['location'];
    } else {
        location.innerHTML = `<i>unknown</i>`;
    }

    const gps = document.getElementById('event-gps');
    const geocoded = document.getElementById('event-geocoded');
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

    const organizer = document.getElementById('event-organizer');
    if (eventData['organizer']) {
        organizer.innerText = eventData['organizer'];
    } else {
        organizer.innerHTML = `<i>unknown</i>`;
    }

    const source = document.getElementById('event-calendar-url');
    source.href = eventData['calendar_url'];
    source.innerText = eventData['calendar_url'];

    const fetchedAt = document.getElementById('event-downloaded-at');
    fetchedAt.innerText = new Date(eventData['calendar_downloaded_at']).toLocaleString();

    const eventButton = document.getElementById('event-url');
    eventButton.href = eventData['event_url'];
}

function handleFirstLoad() {
    setFutureIntoDatetimePickers();
    const filteredEventsData = filterEventsAndLoadMap();
    initializeEventsTable(filteredEventsData);
}
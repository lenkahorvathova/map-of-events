function degreesToRadians(degrees) {
    return degrees * (Math.PI / 180)
}

function calculateDistanceInKilometers(coordinatesA, coordinatesB) {
    const latitudeA = coordinatesA.y;
    const longitudeA = coordinatesA.x;
    const latitudeB = coordinatesB.y;
    const longitudeB = coordinatesB.x;

    const earthRadius = 6371;

    let latitudeDistance = degreesToRadians(latitudeB - latitudeA);
    let longitudeDistance = degreesToRadians(longitudeB - longitudeA);

    let a =
        Math.pow(Math.sin(latitudeDistance / 2), 2) +
        Math.cos(degreesToRadians(latitudeA)) * Math.cos(degreesToRadians(latitudeB)) *
        Math.pow(Math.sin(longitudeDistance / 2), 2);

    return 2 * earthRadius * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function prepareEventData(event) {
    let location = null;
    if (event['location']) {
        location = event['location']
    } else if (event['has_default']) {
        location = event['default_location']
    } else if (!event['has_default']) {
        location = event['municipality'] + ", " + event['district']
    }
    event["table_location"] = location;

    let startDatetime = null;
    let startDatetimeString = event['start_date'];
    if (event['start_time'] != null) {
        startDatetimeString += " " + event['start_time'];
        startDatetime = new Date(startDatetimeString).toLocaleString();
    } else {
        startDatetime = new Date(startDatetimeString).toLocaleDateString();
    }

    event["table_start_datetime"] = startDatetime;

    let endDatetime = null;
    if (event['end_date'] != null) {
        let endDatetimeString = event['end_date'];
        if (event['end_time'] != null) {
            endDatetimeString += " " + event['end_time'];
            endDatetime = new Date(endDatetimeString).toLocaleString();
        } else {
            endDatetime = new Date(endDatetimeString).toLocaleDateString();
        }
    }
    event["table_end_datetime"] = endDatetime;

    return event
}

function filterEventsAndLoadMap(eventsData) {
    const dropRed = "https://api.mapy.cz/img/api/marker/drop-red.png";
    const dropBlue = "https://api.mapy.cz/img/api/marker/drop-blue.png"

    map = new SMap(document.getElementById('map'));
    map.addControl(new SMap.Control.Sync());
    map.addDefaultLayer(SMap.DEF_BASE).enable();
    let mouse = new SMap.Control.Mouse(SMap.MOUSE_PAN | SMap.MOUSE_WHEEL | SMap.MOUSE_ZOOM);
    map.addControl(mouse);

    let marks = [];
    let coordinates = [];

    let onlineChecked = document.getElementById('js-search-form__location__options__online').checked;
    let gpsChecked = document.getElementById('js-search-form__location__options__gps').checked;

    let radius = null;
    let specifiedCoordinates = null;
    if (gpsChecked) {
        radius = document.getElementById('js-search-form__location__radius').value;
        let gpsLatitude = parseFloat(document.getElementById('js-search-form__location__gps-latitude').value);
        let gpsLongitude = parseFloat(document.getElementById('js-search-form__location__gps-longitude').value);

        specifiedCoordinates = SMap.Coords.fromWGS84(gpsLongitude, gpsLatitude);
        let specifiedCoordinatesOptions = {
            url: dropBlue,
            anchor: {left: 10, bottom: 1}
        };

        let mark = new SMap.Marker(specifiedCoordinates, null, specifiedCoordinatesOptions);
        marks.push(mark);
        coordinates.push(specifiedCoordinates);

        let geometryLayer = new SMap.Layer.Geometry();
        map.addLayer(geometryLayer);
        geometryLayer.enable();

        const equator = 6378 * 2 * Math.PI;
        let yrad = Math.PI * gpsLatitude / 180;
        let line = equator * Math.cos(yrad);
        let angle = 360 * radius / line;

        let point = SMap.Coords.fromWGS84(gpsLongitude + angle, gpsLatitude);
        let circleOptions = {
            color: "blue",
            opacity: 0.1,
            outlineColor: "blue",
            outlineOpacity: 0.5,
            outlineWidth: 3
        };
        let circle = new SMap.Geometry(SMap.GEOMETRY_CIRCLE, null, [specifiedCoordinates, point], circleOptions);
        geometryLayer.addGeometry(circle);
    }

    let startDate = document.getElementById('js-search-form__datetime__start__date-picker').value;
    let startTime = document.getElementById('js-search-form__datetime__start__time-picker').value;
    startTime = startTime !== null ? startTime : "00:00";
    let pickedStartDatetime = new Date(startDate + ' ' + startTime);

    let endDate = document.getElementById('js-search-form__datetime__end__date-picker').value;
    let endTime = document.getElementById('js-search-form__datetime__end__time-picker').value;
    endTime = (endDate !== null && endTime !== null) ? endTime : "23:59";
    let pickedEndDatetime = endDate !== null ? new Date(endDate + ' ' + endTime) : new Date(8640000000000000);

    let eventsDataArray = []
    for (let eventId in eventsData) {
        if (!eventsData.hasOwnProperty(eventId)) {
            continue;
        }

        if (onlineChecked && !eventsData[eventId]['online']) {
            continue;
        }

        let eventsStartDate = eventsData[eventId]['start_date']
        let eventsStartTime = eventsData[eventId]['start_time'] !== null ? eventsData[eventId]['start_time'] : "00:00";
        let eventsStartDatetime = new Date(eventsStartDate + ' ' + eventsStartTime);

        let eventsEndDate = eventsData[eventId]['end_date'] !== null ? eventsData[eventId]['end_date'] : eventsStartDate;
        let eventsEndTime = eventsData[eventId]['end_time'] !== null ? eventsData[eventId]['end_time'] : "23:59";
        let eventsEndDatetime = new Date(eventsEndDate + ' ' + eventsEndTime);

        if ((eventsStartDatetime < pickedStartDatetime || eventsStartDatetime > pickedEndDatetime)
            && (eventsEndDatetime < pickedStartDatetime || eventsEndDatetime > pickedEndDatetime)) {
            continue;
        }

        let eventGPS = eventsData[eventId]["gps"];
        if (eventGPS === null) {
            eventGPS = eventsData[eventId]["geocoded_gps"];
        }
        if (eventGPS != null) {
            let dataCoordinates = eventGPS.split(',').map(coordinate => parseFloat(coordinate));
            let parsedCoordinates = SMap.Coords.fromWGS84(dataCoordinates[1], dataCoordinates[0]);


            if (gpsChecked && specifiedCoordinates !== null) {
                let distance = calculateDistanceInKilometers(parsedCoordinates, specifiedCoordinates);
                if (distance >= radius) {
                    continue;
                }
            }

            let options = {
                url: dropRed,
                title: eventsData[eventId]['title'],
                anchor: {left: 10, bottom: 1}
            };

            let mark = new SMap.Marker(parsedCoordinates, null, options);
            marks.push(mark);
            coordinates.push(parsedCoordinates);
        }

        let eventData = prepareEventData(eventsData[eventId]);
        eventsDataArray.push(eventData)
    }

    let options = {
        anchor: {left: 0.5, top: 0.5}
    }
    if (marks.length !== 0) {
        marks[0].decorate(SMap.Marker.Feature.RelativeAnchor, options);
    }

    let layer = new SMap.Layer.Marker();
    map.addLayer(layer);
    layer.enable();
    for (let i = 0; i < marks.length; i++) {
        layer.addMarker(marks[i]);
    }

    if (coordinates.length === 0) {
        coordinates.push(SMap.Coords.fromWGS84("51°03′20″N 14°18′53″E"));
        coordinates.push(SMap.Coords.fromWGS84("48°33′09″N 14°19′59″E"));
        coordinates.push(SMap.Coords.fromWGS84("50°15′07″N 12°05′29″E"));
        coordinates.push(SMap.Coords.fromWGS84("49°33′01″N 18°51′32″E"));
    }

    let centerZoom = map.computeCenterZoom(coordinates);
    map.setCenterZoom(centerZoom[0], centerZoom[1]);

    return eventsDataArray
}

function copyGPSValueIntoForm(itemId) {
    let itemLatitude = document.getElementById(`js-gps-table__${itemId}-latitude`).innerText;
    let itemLongitude = document.getElementById(`js-gps-table__${itemId}-longitude`).innerText;

    let gpsRadioButton = document.getElementById('js-search-form__location__options__gps');
    let gpsLongitude = document.getElementById('js-search-form__location__gps-longitude');
    let gpsLatitude = document.getElementById('js-search-form__location__gps-latitude');
    let radiusSpecification = document.getElementById('js-search-form__location__radius');

    gpsLatitude.disabled = false;
    gpsLatitude.required = true;
    gpsLatitude.value = itemLatitude;
    gpsRadioButton.checked = true;
    gpsLongitude.disabled = false;
    gpsLongitude.required = true;
    gpsLongitude.value = itemLongitude;
    radiusSpecification.disabled = false;

    document.getElementById('modal-button-close').click();
}

function addRowToGPSTable(tbody, number, item) {
    let tr = tbody.insertRow();
    tr.insertCell(0).outerHTML = `<th scope="row">${number}</th>`;

    let td1 = tr.insertCell();
    td1.textContent = item['label'];

    let td2 = tr.insertCell();
    td2.textContent = item['coords']['y'];
    td2.id = `js-gps-table__${number}-latitude`

    let td3 = tr.insertCell();
    td3.textContent = item['coords']['x'];
    td3.id = `js-gps-table__${number}-longitude`

    let td4 = tr.insertCell();
    td4.innerHTML = `<button type="button" class="btn btn-primary btn-block" onclick="copyGPSValueIntoForm(${number})">Use</button>`;
}

function geocodeCallback(geocoder) {
    let locationResults = geocoder.getResults()[0].results;

    removeOldTbodyFromGPSTable();
    let tbody = createNewTbodyForGPSTable();

    if (!locationResults.length) {
        addRowToTbodyWithMessage(tbody, "The specified location couldn't be geocoded!")
    }

    for (let i = 0; i < locationResults.length; i++) {
        let item = locationResults[i];
        addRowToGPSTable(tbody, i + 1, item);
    }
}

function removeOldTbodyFromGPSTable() {
    let oldTbody = document.querySelector('#js-gps-table > tbody');
    if (oldTbody) oldTbody.remove();
}

function createNewTbodyForGPSTable() {
    let table = document.getElementById('js-gps-table');
    let tbody = document.createElement('tbody');
    table.appendChild(tbody);

    return tbody;
}

function addRowToTbodyWithMessage(tbody, message) {
    let tr = tbody.insertRow();
    tr.insertCell().outerHTML = `<td colspan="5" style="text-align: center;">${message}</td>`;
}

function geocodeLocation() {
    let queryValue = document.getElementById('js-search-form__location__municipality').value;
    let tableTitle = document.getElementById('js-gps-table-title')
    tableTitle.innerHTML = `Value used for the search: <strong>"${queryValue}"</strong>`

    removeOldTbodyFromGPSTable();
    let tbody = createNewTbodyForGPSTable();
    addRowToTbodyWithMessage(tbody, "Geocoding the specified location...")

    new SMap.Geocoder(queryValue, geocodeCallback);
}
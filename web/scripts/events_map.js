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

function addRow(tbody, number, event) {
    let tr = tbody.insertRow();
    tr.insertCell(0).outerHTML = `<th scope="row">${number}</th>`;

    let td1 = tr.insertCell();
    td1.textContent = event['title'];

    let td2 = tr.insertCell();
    td2.textContent = event['location'];

    let td3 = tr.insertCell();
    td3.textContent = event['start_date']
    if (event['start_time'] != null) {
        td3.textContent += " " + event['start_time']
    }

    let td4 = tr.insertCell();
    if (event['end_date'] != null) {
        td4.textContent = event['end_date']
        if (event['end_time'] != null) {
            td4.textContent += " " + event['end_time']
        }
    }
}

function filterEventsAndLoadMap(eventsData, foundCoordinates) {
    const dropRed = "https://api.mapy.cz/img/api/marker/drop-red.png";

    let map = new SMap(document.getElementById('map'));
    map.addControl(new SMap.Control.Sync());
    map.addDefaultLayer(SMap.DEF_BASE).enable();
    let mouse = new SMap.Control.Mouse(SMap.MOUSE_PAN | SMap.MOUSE_WHEEL | SMap.MOUSE_ZOOM);
    map.addControl(mouse);

    let marks = [];
    let coordinates = [];

    let oldTbody = document.querySelector('#js-events-table > tbody');
    if (oldTbody) oldTbody.remove();

    let table = document.getElementById('js-events-table');
    let tbody = document.createElement('tbody');
    table.appendChild(tbody);

    let radius = document.getElementById('js-search-form__location__radius').value;
    let onlineChecked = document.getElementById('js-search-form__checkboxes__online').checked;

    let startDate = document.getElementById('js-search-form__datetime__start__date-picker').value;
    let startTime = document.getElementById('js-search-form__datetime__start__time-picker').value;
    startTime = startTime !== null ? startTime : "00:00";
    let pickedStartDatetime = new Date(startDate + ' ' + startTime);

    let endDate = document.getElementById('js-search-form__datetime__end__date-picker').value;
    let endTime = document.getElementById('js-search-form__datetime__end__time-picker').value;
    endTime = (endDate !== null && endTime !== null) ? endTime : "23:59";
    let pickedEndDatetime = endDate !== null ? new Date(endDate + ' ' + endTime) : new Date(8640000000000000);

    let number = 1;
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

        if (eventsData[eventId]["gps"] != null) {
            let dataCoordinates = eventsData[eventId]['gps'].split(',').map(coordinate => parseFloat(coordinate));
            let parsedCoordinates = SMap.Coords.fromWGS84(dataCoordinates[1], dataCoordinates[0]);


            if (foundCoordinates && foundCoordinates.length > 0) {
                let distance = calculateDistanceInKilometers(parsedCoordinates, foundCoordinates[0]);
                // TODO: For now, it considers only the first location found - implement choosing from all found locations.
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

        addRow(tbody, number, eventsData[eventId]);
        number += 1;
    }

    if (number === 1) {
        let tr = tbody.insertRow();
        tr.insertCell().outerHTML = `<td colspan="5" style="text-align: center;">No events were found!</td>`;
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
}

function geocode_callback(geocoder, eventsData) {
    if (!geocoder.getResults()[0].results.length) {
        alert("We don't know to geocode your location, please, try to rewrite it!");
        return;
    }
    let locationResults = geocoder.getResults()[0].results;
    let foundCoordinates = [];
    while (locationResults.length) {
        let item = locationResults.shift()
        foundCoordinates.push(item.coords);
    }

    filterEventsAndLoadMap(eventsData, foundCoordinates);
}

function searchLocationAndFilterEventsAndLoadMap(eventsData, queryValue) {
    new SMap.Geocoder(queryValue, function () {
        geocode_callback(this, eventsData);
    });
}
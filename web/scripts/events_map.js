function filterEventsAndLoadMap(data) {
    const dropRed = "https://api.mapy.cz/img/api/marker/drop-red.png";

    let map = new SMap(JAK.gel("map"));
    map.addControl(new SMap.Control.Sync());
    map.addDefaultLayer(SMap.DEF_BASE).enable();
    let mouse = new SMap.Control.Mouse(SMap.MOUSE_PAN | SMap.MOUSE_WHEEL | SMap.MOUSE_ZOOM);
    map.addControl(mouse);

    let marks = [];
    let coordinates = [];

    $('#js-events-table tbody').remove();

    let table = document.getElementById('js-events-table');
    let tbody = document.createElement('tbody');
    table.appendChild(tbody);

    let onlineChecked = document.getElementById('js-search-form__checkboxes__online').checked;

    let startDate = document.getElementById('js-search-form__datetime__start__date-picker').value;
    let startTime = document.getElementById('js-search-form__datetime__start__time-picker').value;
    let pickedStartDatetime = new Date(startDate + ' ' + startTime);

    let endDate = document.getElementById('js-search-form__datetime__end__date-picker').value;
    let endTime = document.getElementById('js-search-form__datetime__end__time-picker').value;
    let pickedEndDatetime = new Date(endDate + ' ' + endTime);

    let number = 1;
    for (let eventId in data) {
        if (!data.hasOwnProperty(eventId)) {
            continue;
        }

        if (onlineChecked && !data[eventId]['online']) {
            continue;
        }

        let eventsStartDate = data[eventId]['start_date']
        let eventsStartTime = data[eventId]['start_time'] !== null ? data[eventId]['start_time'] : "00:00";
        let eventsStartDatetime = new Date(eventsStartDate + ' ' + eventsStartTime);

        let eventsEndDate = data[eventId]['end_date'] !== null ? data[eventId]['end_date'] : eventsStartDate;
        let eventsEndTime = data[eventId]['end_time'] !== null ? data[eventId]['end_time'] : "23:59";
        let eventsEndDatetime = new Date(eventsEndDate + ' ' + eventsEndTime);

        if ((eventsStartDatetime < pickedStartDatetime || eventsStartDatetime > pickedEndDatetime)
            && (eventsEndDatetime < pickedStartDatetime || eventsEndDatetime > pickedEndDatetime)) {
            continue;
        }

        if (data[eventId]["gps"] != null) {
            let dataCoordinates = data[eventId]['gps'].split(',').map(coordinate => parseFloat(coordinate));
            let parsedCoordinates = SMap.Coords.fromWGS84(dataCoordinates[1], dataCoordinates[0]);

            let options = {
                url: dropRed,
                title: data[eventId]['title'],
                anchor: {left: 10, bottom: 1}
            };

            let mark = new SMap.Marker(parsedCoordinates, null, options);
            marks.push(mark);
            coordinates.push(parsedCoordinates);
        }

        addRow(tbody, number, data[eventId]);
        number += 1;
    }

    if (number === 1) {
        let tr = tbody.insertRow();
        tr.insertCell().outerHTML = "<td colspan=\"5\" style=\"text-align: center;\">No events were found!</td>";
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

function addRow(tbody, number, event) {
    let tr = tbody.insertRow();
    tr.insertCell(0).outerHTML = "<th scope=\"row\">" + number + "</th>";

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
function degreesToRadians(degrees) {
    return degrees * (Math.PI / 180);
}

function calculateDistanceInKilometers(coordinatesA, coordinatesB) {
    const latitudeA = coordinatesA.y;
    const longitudeA = coordinatesA.x;
    const latitudeB = coordinatesB.y;
    const longitudeB = coordinatesB.x;

    const EARTH_RADIUS = 6371;
    const a = Math.pow(Math.sin(degreesToRadians(latitudeB - latitudeA) / 2), 2) +
            Math.cos(degreesToRadians(latitudeA)) * Math.cos(degreesToRadians(latitudeB)) *
            Math.pow(Math.sin(degreesToRadians(longitudeB - longitudeA) / 2), 2);

    return 2 * EARTH_RADIUS * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function showEventDetailsFromCard(eventId) {
    const eventData = GLB_EVENTS_DATASET[eventId];
    showEventDetailsModal(eventData);
}

function createCustomCluster() {
    const CustomCluster = JAK.ClassMaker.makeClass({
        NAME: "MyCluster",
        VERSION: "1.0",
        EXTEND: SMap.Marker.Cluster
    });

    CustomCluster.prototype.click = function (event, element) {
        const max_zoom = 18;

        if (GLB_MAP.getZoom() >= max_zoom) {
            const card = new SMap.Card();

            let cardTable = "";
            for (let i = 0; i < this._markers.length; i++) {
                cardTable += `
                    <tr>
                        <td>${this._markers[i]._options.title}</td>
                        <td>
                            <div style="text-align: center; white-space: nowrap">
                                <button type="button" class="btn btn-secondary btn-sm"
                                        data-toggle="modal" data-target="#eventDetails"
                                        onclick="showEventDetailsFromCard(${this._markers[i]._options.eventId})"
                                        title="Show event's details.">
                                    <i class="fa fa-info-circle"></i>
                                </button>
                            </div>
                        </td>
                    </tr>`;
            }

            card.getHeader().innerHTML = "<strong>Included Events</strong>";
            card.getBody().innerHTML = `
                <div class="table-responsive rounded">
                    <table class="table table-bordered table-hover table-sm">
                        <thead style="display: none">
                            <tr>
                                <th scope="col" class="th-sm">Title</th>
                                <th scope="col" class="th-sm"></th>
                            </tr>
                        </thead>
                        <tbody>
                            ${cardTable}
                        </tbody>
                    </table>
                </div>`;

            GLB_MAP.addCard(card, this.getCoords());

        } else {
            this.$super(event, element);
        }
    };

    return CustomCluster;
}

function prepareEventDataForEventsTable(event) {
    event['table_title'] = event['title'];

    let location = null;
    if (event['location']) {
        location = event['location'];
    } else if (event['has_default']) {
        location = event['default_location'];
    } else if (!event['has_default']) {
        location = event['municipality'] + ", " + event['district'];
    }
    event["table_location"] = location;

    let startDatetime;
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

    return event;
}

function addLayerForRadiusCircle(specifiedRadius, specifiedCoordinates, circlePoint) {
    const specifiedRadiusLayer = new SMap.Layer.Geometry();
    GLB_MAP.addLayer(specifiedRadiusLayer);
    specifiedRadiusLayer.enable();

    const specifiedRadiusOptions = {
        color: "blue",
        opacity: 0.1,
        outlineColor: "blue",
        outlineOpacity: 0.5,
        outlineWidth: 3
    };

    const specifiedRadiusCircle = new SMap.Geometry(SMap.GEOMETRY_CIRCLE, null, [specifiedCoordinates, circlePoint], specifiedRadiusOptions);
    specifiedRadiusLayer.addGeometry(specifiedRadiusCircle);
}

function computeCirclePoint(specifiedRadius, gpsLatitude, gpsLongitude) {
    const EQUATOR = 6378 * 2 * Math.PI;
    const yrad = Math.PI * gpsLatitude / 180;
    const line = EQUATOR * Math.cos(yrad);
    const angle = 360 * specifiedRadius / line;

    return SMap.Coords.fromWGS84(gpsLongitude + angle, gpsLatitude);
}

function addLayerForGPSMark(specifiedCoordinates) {
    const dropBlue = "https://api.mapy.cz/img/api/marker/drop-blue.png";
    const specifiedCoordinatesOptions = {
        url: dropBlue,
        anchor: {left: 10, bottom: 1}
    };
    const specifiedGPSLayer = new SMap.Layer.Marker();
    const specifiedGPSMark = new SMap.Marker(specifiedCoordinates, null, specifiedCoordinatesOptions);
    const specifiedGPSMarkOptions = {
        anchor: {left: 0.5, top: 0.5}
    };
    specifiedGPSMark.decorate(SMap.Marker.Feature.RelativeAnchor, specifiedGPSMarkOptions);
    specifiedGPSLayer.addMarker(specifiedGPSMark);
    GLB_MAP.addLayer(specifiedGPSLayer);
    specifiedGPSLayer.enable();
}

function initializeMap() {
    GLB_MAP = new SMap(document.getElementById('map'));
    GLB_MAP.addControl(new SMap.Control.Sync());
    GLB_MAP.addDefaultLayer(SMap.DEF_BASE).enable();
    GLB_MAP.addDefaultControls();

    const mouse = new SMap.Control.Mouse(SMap.MOUSE_PAN | SMap.MOUSE_WHEEL | SMap.MOUSE_ZOOM);
    GLB_MAP.addControl(mouse);
}

function filterEventsAndLoadMap() {
    initializeMap();

    const onlineChecked = document.getElementById('js-search-form__location__options__online').checked;
    const gpsChecked = document.getElementById('js-search-form__location__options__gps').checked;

    let specifiedRadius = null;
    let specifiedCoordinates = null;
    if (gpsChecked) {
        specifiedRadius = document.getElementById('js-search-form__location__radius').value;

        const gpsLatitude = parseFloat(document.getElementById('js-search-form__location__gps-latitude').value);
        const gpsLongitude = parseFloat(document.getElementById('js-search-form__location__gps-longitude').value);
        specifiedCoordinates = SMap.Coords.fromWGS84(gpsLongitude, gpsLatitude);

        addLayerForGPSMark(specifiedCoordinates);

        const circlePoint = computeCirclePoint(specifiedRadius, gpsLatitude, gpsLongitude);
        addLayerForRadiusCircle(specifiedRadius, specifiedCoordinates, circlePoint);
    }

    const startDate = document.getElementById('js-search-form__datetime__start__date-picker').value;
    let startTime = document.getElementById('js-search-form__datetime__start__time-picker').value;
    if (startTime === null) startTime = "00:00";
    const specifiedStartDatetime = new Date(startDate + ' ' + startTime);

    const endDate = document.getElementById('js-search-form__datetime__end__date-picker').value;
    let endTime = document.getElementById('js-search-form__datetime__end__time-picker').value;
    if (endTime === null) endTime = "23:59";
    let specifiedEndDatetime;
    if (endDate !== null) {
        specifiedEndDatetime = new Date(endDate + ' ' + endTime);
    } else {
        specifiedEndDatetime = new Date(8640000000000000);
    }

    const marks = [];
    const coordinates = [];
    const filteredEventsData = [];

    const dropRed = "https://api.mapy.cz/img/api/marker/drop-red.png";
    for (let eventId in GLB_EVENTS_DATASET) {
        if (!GLB_EVENTS_DATASET.hasOwnProperty(eventId)) {
            continue;
        }

        if (onlineChecked && !GLB_EVENTS_DATASET[eventId]['online']) {
            continue;
        }

        const eventsStartDate = GLB_EVENTS_DATASET[eventId]['start_date'];
        let eventsStartTime = GLB_EVENTS_DATASET[eventId]['start_time'];
        if (eventsStartTime === null) eventsStartTime = "00:00";
        const eventsStartDatetime = new Date(eventsStartDate + ' ' + eventsStartTime);

        let eventsEndDate = GLB_EVENTS_DATASET[eventId]['end_date'];
        if (eventsEndDate === null) eventsEndDate = eventsStartDate;
        let eventsEndTime = GLB_EVENTS_DATASET[eventId]['end_time'];
        if (eventsEndTime === null) eventsEndTime = "23:59";
        const eventsEndDatetime = new Date(eventsEndDate + ' ' + eventsEndTime);

        if ((eventsStartDatetime < specifiedStartDatetime && eventsEndDatetime < specifiedStartDatetime)
                || (eventsStartDatetime > specifiedEndDatetime && eventsEndDatetime > specifiedEndDatetime)) {
            continue;
        }

        let eventGPS = GLB_EVENTS_DATASET[eventId]["gps"];
        if (eventGPS === null) eventGPS = GLB_EVENTS_DATASET[eventId]["geocoded_gps"];
        if (eventGPS === null) {
            throw `'eventGPS' for the event(${eventId}) is null!`;
        }

        const coordinatesArray = eventGPS.split(',').map(coordinate => parseFloat(coordinate));
        const sMapCoordinates = SMap.Coords.fromWGS84(coordinatesArray[1], coordinatesArray[0]);

        if (gpsChecked && specifiedCoordinates !== null) {
            const distance = calculateDistanceInKilometers(sMapCoordinates, specifiedCoordinates);
            if (distance >= specifiedRadius) {
                continue;
            }
        }

        const eventCard = new SMap.Card();
        eventCard.getHeader().innerHTML = `<strong>${GLB_EVENTS_DATASET[eventId]['title']}</strong>`;
        eventCard.getBody().innerHTML = `
            <div style="text-align: center; white-space: nowrap">
                <button type="button" class="btn btn-secondary"
                        data-toggle="modal" data-target="#eventDetails"
                        onclick="showEventDetailsFromCard(${eventId})"
                        title="Show event's details.">
                    <i class="fa fa-info-circle"></i>
                </button>
            </div>`;

        const eventMarkOptions = {
            url: dropRed,
            title: GLB_EVENTS_DATASET[eventId]['title'],
            anchor: {left: 10, bottom: 1},
            eventId: eventId
        };
        const eventMark = new SMap.Marker(sMapCoordinates, null, eventMarkOptions);
        eventMark.decorate(SMap.Marker.Feature.Card, eventCard);
        marks.push(eventMark);
        coordinates.push(sMapCoordinates);

        const eventData = prepareEventDataForEventsTable(GLB_EVENTS_DATASET[eventId]);
        filteredEventsData.push(eventData);
    }

    if (marks.length > 0) {
        marks[0].decorate(SMap.Marker.Feature.RelativeAnchor, {anchor: {left: 0.5, top: 0.5}});
    }

    const CustomCluster = createCustomCluster();
    const eventsMarksLayer = new SMap.Layer.Marker();
    let clusterer = new SMap.Marker.Clusterer(GLB_MAP, 50, CustomCluster);
    eventsMarksLayer.setClusterer(clusterer);

    for (let i = 0; i < marks.length; i++) {
        eventsMarksLayer.addMarker(marks[i]);
    }
    GLB_MAP.addLayer(eventsMarksLayer);
    eventsMarksLayer.enable();

    if (coordinates.length === 0) {
        coordinates.push(SMap.Coords.fromWGS84("51°03′20″N 14°18′53″E"));
        coordinates.push(SMap.Coords.fromWGS84("48°33′09″N 14°19′59″E"));
        coordinates.push(SMap.Coords.fromWGS84("50°15′07″N 12°05′29″E"));
        coordinates.push(SMap.Coords.fromWGS84("49°33′01″N 18°51′32″E"));
    }

    if (gpsChecked) {
        coordinates.push(specifiedCoordinates);
    }

    let centerZoom = GLB_MAP.computeCenterZoom(coordinates);
    GLB_MAP.setCenterZoom(centerZoom[0], centerZoom[1]);

    return filteredEventsData;
}
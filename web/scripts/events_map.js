function showEventDetailsFromMap(eventId) {
    const eventData = GLB_EVENTS_DATASET[eventId];
    document.getElementById('modal--event-details__close-btn').hidden = false;
    document.getElementById('modal--event-details__back-btn').hidden = true;
    prepareEventDetailsModal(eventData);
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
                            <div class="centered-cell-content">
                                <button type="button" class="btn btn-secondary btn-sm"
                                        data-toggle="modal" data-target="#modal--event-details"
                                        onclick="showEventDetailsFromMap(${this._markers[i]._options.eventId})"
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

    event["table_start_datetime"] = {
        'date': event['start_date'],
        'time': event['start_time']
    };

    event["table_end_datetime"] = {
        'date': event['end_date'],
        'time': event['end_time']
    };

    return event;
}

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

function calculateDurationInWeeks(dateA, dateB) {
    let furtherDate;
    let closerDate;
    if (dateA > dateB) {
        furtherDate = dateA;
        closerDate = dateB;
    } else if (dateA < dateB) {
        furtherDate = dateB;
        closerDate = dateA;
    } else {
        return 0;
    }

    let diff = (furtherDate.getTime() - closerDate.getTime()) / 1000;
    diff /= (60 * 60 * 24 * 7);
    return Math.abs(Math.round(diff));
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

function addShowTableButton() {
    const customLayer = new SMap.Layer.HUD();
    GLB_MAP.addLayer(customLayer);
    customLayer.enable();

    const showTable = JAK.mel("div");
    const button = JAK.mel("button", {
        type: "button",
        textContent: "Show Events Table"
    }, {
        fontSize: "17px",
        lineHeight: "27px",
        fontWeight: "400",
        background: "#fff",
        color: "#6b7580",
        border: "none",
        outline: "0",
        borderRadius: "2px",
        padding: "0 8px 0 8px",
        fontStyle: "normal",
        fontSmooth: "antialiased",
        "-webkit-font-smoothing": "antialiased"

    });
    button.onclick = function () {
        $("#modal--events-table").modal('show');
    };
    showTable.appendChild(button);
    customLayer.addItem(showTable, {
        position: "absolute",
        right: "97px",
        top: "17px",
        borderRadius: "2px",
        boxShadow: "0 0 2px 0 rgba(0,0,0,.3)"
    });
}

function initializeMap() {
    GLB_MAP = new SMap(document.getElementById('content__map'));
    GLB_MAP.addControl(new SMap.Control.Sync());
    GLB_MAP.addDefaultLayer(SMap.DEF_BASE).enable();
    GLB_MAP.addDefaultControls();

    addShowTableButton();

    const mouse = new SMap.Control.Mouse(SMap.MOUSE_PAN | SMap.MOUSE_WHEEL | SMap.MOUSE_ZOOM);
    GLB_MAP.addControl(mouse);

    GLB_MAP.getSignals().addListener(this, "marker-click", function (event) {
        const target = event.target;
        if (target.getActive().className === "marker") {
            const eventId = target._options.eventId;
            showEventDetailsFromMap(eventId);
            $("#modal--event-details").modal();
        }
    });
}

function filterEventsAndLoadMap() {
    initializeMap();

    const typesPickedOptions = document.getElementById('sidebar__form--filter__types__select-picker').selectedOptions;
    typesPicked = [];
    if (typesPickedOptions !== undefined) {
        for (let i = 0; i < typesPickedOptions.length; i++) {
            typesPicked.push(typesPickedOptions[i].label.toLowerCase());
        }
    }

    const keywordsPickedOptions = document.getElementById('sidebar__form--filter__keywords__select-picker').selectedOptions;
    keywordsPicked = [];
    if (keywordsPickedOptions !== undefined) {
        for (let i = 0; i < keywordsPickedOptions.length; i++) {
            keywordsPicked.push(keywordsPickedOptions[i].label);
        }
    }

    const gpsChecked = document.getElementById('sidebar__form--filter__location__options--gps').checked;
    let specifiedRadius = null;
    let specifiedCoordinates = null;
    if (gpsChecked) {
        specifiedRadius = document.getElementById('sidebar__form--filter__location__radius').value;

        const gpsLatitude = parseFloat(document.getElementById('sidebar__form--filter__location__gps--latitude').value);
        const gpsLongitude = parseFloat(document.getElementById('sidebar__form--filter__location__gps--longitude').value);
        specifiedCoordinates = SMap.Coords.fromWGS84(gpsLongitude, gpsLatitude);

        const circlePoint = computeCirclePoint(specifiedRadius, gpsLatitude, gpsLongitude);
        addLayerForRadiusCircle(specifiedRadius, specifiedCoordinates, circlePoint);
    }

    const startDate = document.getElementById('sidebar__form--filter__datetime__start--date-picker').value;
    let specifiedStartTime = document.getElementById('sidebar__form--filter__datetime__start--time-picker').value;
    if (specifiedStartTime === "") specifiedStartTime = "00:00";
    const specifiedStartDatetime = new Date(startDate + ' ' + specifiedStartTime);

    const endDate = document.getElementById('sidebar__form--filter__datetime__end--date-picker').value;
    let specifiedEndTime = document.getElementById('sidebar__form--filter__datetime__end--time-picker').value;
    if (specifiedEndTime === "") specifiedEndTime = "23:59";
    let specifiedEndDatetime;
    if (endDate === "") {
        specifiedEndDatetime = new Date(8640000000000000);
    } else {
        specifiedEndDatetime = new Date(endDate + ' ' + specifiedEndTime);
    }

    const marks = [];
    const coordinates = [];
    const filteredEventsData = [];

    const dropRed = "https://api.mapy.cz/img/api/marker/drop-red.png";
    for (let eventId in GLB_EVENTS_DATASET) {
        if (!GLB_EVENTS_DATASET.hasOwnProperty(eventId)) {
            continue;
        }

        const onlineChecked = document.getElementById('sidebar__form--filter__location__options--online').checked;
        if ((onlineChecked && !GLB_EVENTS_DATASET[eventId]['online'])
                || (!onlineChecked && GLB_EVENTS_DATASET[eventId]['online'])) {
            continue;
        }

        if (typesPicked.length !== 0) {
            const typesIntersection = typesPicked.filter(value => GLB_EVENTS_DATASET[eventId]['types'].includes(value));
            if (typesIntersection.length === 0) {
                continue;
            }
        }

        if (keywordsPicked.length !== 0) {
            const keywordsIntersection = keywordsPicked.filter(value => GLB_EVENTS_DATASET[eventId]['keywords'].includes(value));
            if (keywordsIntersection.length === 0) {
                continue;
            }
        }

        const ongoingChecked = document.getElementById('sidebar__form--filter__datetime__including-checkboxes--ongoing').checked;

        const eventsStartDate = GLB_EVENTS_DATASET[eventId]['start_date'];
        let eventsStartTime = GLB_EVENTS_DATASET[eventId]['start_time'];
        if (eventsStartTime === null) eventsStartTime = ongoingChecked ? "00:00" : specifiedStartTime;
        const eventsStartDatetime = new Date(eventsStartDate + ' ' + eventsStartTime);

        let eventsEndDate = GLB_EVENTS_DATASET[eventId]['end_date'];
        if (eventsEndDate === null) eventsEndDate = eventsStartDate;
        let eventsEndTime = GLB_EVENTS_DATASET[eventId]['end_time'];
        if (eventsEndTime === null) eventsEndTime = ongoingChecked ? "23:59" : specifiedEndTime;
        const eventsEndDatetime = new Date(eventsEndDate + ' ' + eventsEndTime);

        const longTermChecked = document.getElementById('sidebar__form--filter__datetime__including-checkboxes--long-term').checked;
        if (!longTermChecked) {
            const longTermMinDuration = 3;
            const eventDuration = calculateDurationInWeeks(eventsStartDatetime, eventsEndDatetime);
            if (eventDuration >= longTermMinDuration) {
                continue;
            }
        }

        if (ongoingChecked) {
            if ((eventsStartDatetime < specifiedStartDatetime && eventsEndDatetime < specifiedStartDatetime)
                    || (eventsStartDatetime > specifiedEndDatetime && eventsEndDatetime > specifiedEndDatetime)) {
                continue;
            }
        } else {
            if (eventsStartDatetime < specifiedStartDatetime || eventsStartDatetime > specifiedEndDatetime
                    || eventsEndDatetime < specifiedStartDatetime || eventsEndDatetime > specifiedEndDatetime) {
                continue;
            }
        }

        if (!onlineChecked) {
            let eventGPS = GLB_EVENTS_DATASET[eventId]["gps"];
            if (eventGPS === null) eventGPS = GLB_EVENTS_DATASET[eventId]["geocoded_gps"];
            if (!onlineChecked && eventGPS === null) {
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

            const eventMarkOptions = {
                url: dropRed,
                title: GLB_EVENTS_DATASET[eventId]['title'],
                anchor: {left: 10, bottom: 1},
                eventId: eventId
            };
            const eventMark = new SMap.Marker(sMapCoordinates, null, eventMarkOptions);
            eventMark.getContainer()[SMap.LAYER_MARKER].style.cursor = "pointer";
            eventMark.getContainer()[SMap.LAYER_MARKER].classList.add("marker");
            marks.push(eventMark);
            coordinates.push(sMapCoordinates);
        }

        const eventData = prepareEventDataForEventsTable(GLB_EVENTS_DATASET[eventId]);
        filteredEventsData.push(eventData);
    }

    if (marks.length > 0) {
        marks[0].decorate(SMap.Marker.Feature.RelativeAnchor, {anchor: {left: 0.5, top: 0.5}});
    }

    const CustomCluster = createCustomCluster();
    const eventsMarksLayer = new SMap.Layer.Marker();
    const clusterer = new SMap.Marker.Clusterer(GLB_MAP, 50, CustomCluster);
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
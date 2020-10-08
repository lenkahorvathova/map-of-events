function initializeFailedEventsTable() {
    const failedEventsTable = $('#failures__events--failed__table').DataTable({
        data: GLB_FAILED_EVENTS,
        columns: [
            {data: null},
            {data: 'event_url'},
            {data: 'error'},
            {data: 'event_url_id'}
        ],
        dom: 'ltipr',
        order: [[1, "asc"]],
        responsive: true,
        columnDefs: [
            {
                targets: 0,
                orderable: false,
                width: 20
            },
            {
                targets: 1,
                orderable: true,
                render: function (data) {
                    return `<a href="${data}" target="_blank">${data}</a>`;
                }
            },
            {
                targets: 3,
                visible: false
            }
        ]
    });

    failedEventsTable.on('order.dt search.dt', function () {
        failedEventsTable.column(0, {search: 'applied', order: 'applied'}).nodes().each(function (cell, i) {
            cell.innerHTML = i + 1;
        });
    }).draw();
}

function initializeCalendarsWithFailedEventsTable() {
    const calendarsWithFailedEventsTable = $('#failures__calendars--failed-events__table').DataTable({
        data: GLB_CALENDARS_WITH_FAILED_EVENTS,
        columns: [
            {data: null},
            {data: 'calendar_url'},
            {data: 'events_failure'}
        ],
        dom: 'ltipr',
        order: [[1, "asc"]],
        responsive: true,
        columnDefs: [
            {
                targets: 0,
                orderable: false,
                width: 20
            },
            {
                targets: 1,
                orderable: true,
                render: function (data) {
                    return `<a href="${data}" target="_blank">${data}</a>`;
                }
            },
            {
                targets: 2,
                orderable: true,
                render: function (data) {
                    return `${data['failure_percentage'].toFixed(0)}% <span class="text-muted small">(${data['failed_events_count']}/${data['all_events_count']})</span>`;
                }
            }
        ]
    });

    calendarsWithFailedEventsTable.on('order.dt search.dt', function () {
        calendarsWithFailedEventsTable.column(0, {
            search: 'applied',
            order: 'applied'
        }).nodes().each(function (cell, i) {
            cell.innerHTML = i + 1;
        });
    }).draw();
}

function initializeEmptyCalendarsTable() {
    const emptyCalendarsTable = $('#failures__calendars--empty__table').DataTable({
        data: GLB_EMPTY_CALENDARS,
        columns: [
            {data: null},
            {data: 'calendar_url'},
            {data: 'parser'},
            {data: 'always'}
        ],
        dom: 'ltipr',
        order: [[1, "asc"]],
        responsive: true,
        columnDefs: [
            {
                targets: 0,
                orderable: false,
                width: 20
            },
            {
                targets: 1,
                orderable: true,
                render: function (data) {
                    return `<a href="${data}" target="_blank">${data}</a>`;
                }
            },
            {
                targets: 2,
                visible: false
            },
            {
                targets: 3,
                visible: false
            }
        ]
    });

    emptyCalendarsTable.on('order.dt search.dt', function () {
        emptyCalendarsTable.column(0, {search: 'applied', order: 'applied'}).nodes().each(function (cell, i) {
            cell.innerHTML = i + 1;
        });
    }).draw();

    $('#failures__calendars--empty__checkbox input:checkbox').on('change', function () {
        if ($('#failures__calendars--empty__checkbox--vismo').is(':checked')) {
            emptyCalendarsTable.columns(2).search('^((?!vismo).*)$', true, false, false).draw(false);
        } else {
            emptyCalendarsTable.columns(2).search('', true, false, false).draw(false);
        }

        if ($('#failures__calendars--empty__checkbox--always-empty').is(':checked')) {
            emptyCalendarsTable.columns(3).search('^((?!true)false)$', true, false, false).draw(false);
        } else {
            emptyCalendarsTable.columns(3).search('', true, false, false).draw(false);
        }
    });
}

function initializeFailingCalendarsTable() {
    const failingCalendarsTable = $('#failures__calendars--failing__table').DataTable({
        data: GLB_FAILING_CALENDARS,
        columns: [
            {data: null},
            {data: 'calendar_url'}
        ],
        dom: 'ltipr',
        order: [[1, "asc"]],
        responsive: true,
        columnDefs: [
            {
                targets: 0,
                orderable: false,
                width: 20
            },
            {
                targets: 1,
                orderable: true,
                render: function (data) {
                    return `<a href="${data}" target="_blank">${data}</a>`;
                }
            }
        ]
    });

    failingCalendarsTable.on('order.dt search.dt', function () {
        failingCalendarsTable.column(0, {search: 'applied', order: 'applied'}).nodes().each(function (cell, i) {
            cell.innerHTML = i + 1;
        });
    }).draw();
}

function initializeCrawlerStatusTables() {
    initializeFailingCalendarsTable();
    initializeEmptyCalendarsTable();
    initializeCalendarsWithFailedEventsTable();
    initializeFailedEventsTable();
}

function initializeCrawlerStatusGraphs() {
    loadEventsPerWeekGraph();
    loadEventsPerCalendarAndParserGraph(GLB_EVENTS_PER_CALENDAR);
}

function handleFirstLoad() {
    initializeCrawlerStatusGraphs();
    initializeCrawlerStatusTables();
}
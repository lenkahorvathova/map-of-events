function formatCalendarDetails(data) {
    const calendar_url = data['calendar_url'];
    const calendar_details = GLB_CALENDARS_DATA[calendar_url];
    return `<div style="white-space: pre-wrap;">${JSON.stringify(calendar_details, null, '\t')}</div>`;
}

function formatEventDetails(data) {
    const event_url = data['event_url'];
    const event_details = GLB_EVENTS_DATA[event_url];
    return `<div style="white-space: pre-wrap;">${JSON.stringify(event_details, null, '\t')}</div>`;
}

function toggleDetails(element, table) {
    const tr = $(element).closest('tr');
    const row = table.row(tr);

    if (row.child.isShown()) {
        row.child.hide();
        tr.removeClass('shown');
        tr.find("i.fa").first().removeClass('fa-minus-circle');
        tr.find("i.fa").first().addClass('fa-plus-circle');
    } else {
        if ('calendar_url' in row.data()) {
            row.child(formatCalendarDetails(row.data()), 'shown-details').show();
        } else if ('event_url' in row.data()) {
            row.child(formatEventDetails(row.data()), 'shown-details').show();
        } else {
            throw `URL for calendar or event is missing!`;
        }
        tr.addClass('shown');
        tr.find("i.fa").first().removeClass('fa-plus-circle');
        tr.find("i.fa").first().addClass('fa-minus-circle');
    }
}

function initializeFailedEventsTable() {
    const failedEventsTable = $('#failures__events--failed__table').DataTable({
        data: GLB_FAILED_EVENTS,
        columns: [
            {data: null},
            {data: null},
            {data: 'event_url'},
            {data: 'error'},
            {data: 'downloaded_at'},
            {data: 'event_url_id'}
        ],
        dom: 'ltipr',
        order: [[4, "desc"]],
        responsive: true,
        autoWidth: false,
        columnDefs: [
            {
                targets: 0,
                className: 'details-control',
                orderable: false,
                width: 20,
                defaultContent: '',
                render: function () {
                    return '<i class="fa fa-plus-circle" aria-hidden="true"></i>';
                }
            },
            {
                targets: 1,
                orderable: false,
                width: 20
            },
            {
                targets: 2,
                className: "shorten-cell",
                orderable: true,
                visible: true,
                render: function (data) {
                    return `<a href="${data}" target="_blank">${data}</a>`;
                }
            },
            {
                targets: 3,
                orderable: true,
                width: 180
            },
            {
                targets: 4,
                orderable: true,
                width: 80,
                render: function (data, type) {
                    if (type === 'display')
                        return new Date(data.replace(/ /g,"T")).toLocaleDateString();
                    else
                        return new Date(data.replace(/ /g,"T"));
                }
            },
            {
                targets: 5,
                visible: false
            }
        ]
    });

    failedEventsTable.on('order.dt search.dt', function () {
        failedEventsTable.column(1, {
            search: 'applied',
            order: 'applied'
        }).nodes().each(function (cell, i) {
            cell.innerHTML = i + 1;
        });
    }).draw();

    $('#failures__events--failed__table tbody').on('click', 'td.details-control', function () {
        return toggleDetails(this, failedEventsTable);
    });
}

function initializeCalendarsWithFailedEventsTable() {
    const calendarsWithFailedEventsTable = $('#failures__calendars--failed-events__table').DataTable({
        data: GLB_CALENDARS_WITH_FAILED_EVENTS,
        columns: [
            {data: null},
            {data: null},
            {data: 'calendar_url'},
            {data: 'events_failure'}
        ],
        dom: 'ltipr',
        order: [[2, "asc"]],
        responsive: true,
        columnDefs: [
            {
                targets: 0,
                className: 'details-control',
                orderable: false,
                width: 20,
                defaultContent: '',
                render: function () {
                    return '<i class="fa fa-plus-circle" aria-hidden="true"></i>';
                }
            },
            {
                targets: 1,
                orderable: false,
                width: 20
            },
            {
                targets: 2,
                orderable: true,
                render: function (data) {
                    return `<a href="${data}" target="_blank">${data}</a>`;
                }
            },
            {
                targets: 3,
                orderable: true,
                render: function (data, type) {
                    if (type === 'display') {
                        return `${data['failure_percentage'].toFixed(0)}% <span class="text-muted small">(${data['failed_events_count']}/${data['all_events_count']})</span>`;
                    } else {
                        return data['failure_percentage'].toFixed(0)
                    }
                }
            }
        ]
    });

    calendarsWithFailedEventsTable.on('order.dt search.dt', function () {
        calendarsWithFailedEventsTable.column(1, {
            search: 'applied',
            order: 'applied'
        }).nodes().each(function (cell, i) {
            cell.innerHTML = i + 1;
        });
    }).draw();

    $('#failures__calendars--failed-events__table tbody').on('click', 'td.details-control', function () {
        return toggleDetails(this, calendarsWithFailedEventsTable);
    });
}

function initializeEmptyCalendarsTable() {
    const emptyCalendarsTable = $('#failures__calendars--empty__table').DataTable({
        data: GLB_EMPTY_CALENDARS,
        columns: [
            {data: null},
            {data: null},
            {data: 'calendar_url'},
            {data: 'parser'},
            {data: 'always'}
        ],
        dom: 'ltipr',
        order: [[2, "asc"]],
        responsive: true,
        columnDefs: [
            {
                targets: 0,
                className: 'details-control',
                orderable: false,
                width: 20,
                defaultContent: '',
                render: function () {
                    return '<i class="fa fa-plus-circle" aria-hidden="true"></i>';
                }
            },
            {
                targets: 1,
                orderable: false,
                width: 20
            },
            {
                targets: 2,
                orderable: true,
                render: function (data) {
                    return `<a href="${data}" target="_blank">${data}</a>`;
                }
            },
            {
                targets: 3,
                visible: false
            },
            {
                targets: 4,
                visible: false
            }
        ]
    });

    emptyCalendarsTable.on('order.dt search.dt', function () {
        emptyCalendarsTable.column(1, {
            search: 'applied',
            order: 'applied'
        }).nodes().each(function (cell, i) {
            cell.innerHTML = i + 1;
        });
    }).draw();

    $('#failures__calendars--empty__checkbox input:checkbox').on('change', function () {
        if ($('#failures__calendars--empty__checkbox--vismo').is(':checked')) {
            emptyCalendarsTable.columns(3).search('^((?!vismo).*)$', true, false, false).draw(false);
        } else {
            emptyCalendarsTable.columns(3).search('', true, false, false).draw(false);
        }

        if ($('#failures__calendars--empty__checkbox--always-empty').is(':checked')) {
            emptyCalendarsTable.columns(4).search('^((?!true)false)$', true, false, false).draw(false);
        } else {
            emptyCalendarsTable.columns(4).search('', true, false, false).draw(false);
        }
    });

    $('#failures__calendars--empty__table tbody').on('click', 'td.details-control', function () {
        return toggleDetails(this, emptyCalendarsTable);
    });
}

function initializeFailingCalendarsTable() {
    const failingCalendarsTable = $('#failures__calendars--failing__table').DataTable({
        data: GLB_FAILING_CALENDARS,
        columns: [
            {data: null},
            {data: null},
            {data: 'calendar_url'}
        ],
        dom: 'ltipr',
        order: [[2, "asc"]],
        responsive: true,
        columnDefs: [
            {
                targets: 0,
                className: 'details-control',
                orderable: false,
                width: 20,
                defaultContent: '',
                render: function () {
                    return '<i class="fa fa-plus-circle" aria-hidden="true"></i>';
                }
            },
            {
                targets: 1,
                orderable: false,
                width: 20
            },
            {
                targets: 2,
                orderable: true,
                render: function (data) {
                    return `<a href="${data}" target="_blank">${data}</a>`;
                }
            }
        ]
    });

    failingCalendarsTable.on('order.dt search.dt', function () {
        failingCalendarsTable.column(1, {
            search: 'applied',
            order: 'applied'
        }).nodes().each(function (cell, i) {
            cell.innerHTML = i + 1;
        });
    }).draw();

    $('#failures__calendars--failing__table tbody').on('click', 'td.details-control', function () {
        return toggleDetails(this, failingCalendarsTable);
    });
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
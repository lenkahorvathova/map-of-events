function prefixWithZero(value) {
    return ('0' + value).slice(-2)
}

function getDateString(date) {
    let day = prefixWithZero(date.getDate());
    let month = prefixWithZero(date.getMonth() + 1);
    let year = date.getFullYear();

    return year + '-' + month + '-' + day;
}

function getTimeString(date) {
    let hours = prefixWithZero(date.getHours());
    let minutes = prefixWithZero(date.getMinutes());

    return hours + ':' + minutes;
}

function setValuesOfDatetimePickers(startDate, startTime, endDate, endTime) {
    if (startDate && endDate && endDate < startDate) {
        throw "end_date is before start_date!"
    }
    if (startDate && endDate && startTime && endTime && startDate === endDate && endTime < startTime) {
        throw "end_time is before start_time on the same date!"
    }

    let startDatePicker = document.getElementById('js-search-form__datetime__start__date-picker');
    let startTimePicker = document.getElementById('js-search-form__datetime__start__time-picker');
    let endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    let endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');

    startDatePicker.value = startDate;
    startDatePicker.min = startDate;
    startTimePicker.value = startTime;

    endDatePicker.value = endDate;
    endDatePicker.min = startDate;
    endTimePicker.value = endTime;
    if (startDatePicker.value === endDatePicker.value) {
        endTimePicker.min = startTime;
    }
}

function getAllFutureEvents() {
    let date = new Date();

    let today = getDateString(date);
    let now = getTimeString(date);

    setValuesOfDatetimePickers(today, now, null, null);
}

function setTodayIntoDatetimePickers() {
    enableEnd();

    let date = new Date();
    let today = getDateString(date);
    let now = getTimeString(date);

    setValuesOfDatetimePickers(today, now, today, null);
}

function setTomorrowIntoDatetimePickers() {
    enableEnd();

    let date = new Date();
    date.setDate(date.getDate() + 1);
    let tomorrow = getDateString(date);

    setValuesOfDatetimePickers(tomorrow, null, tomorrow, null);
}

function setNext10DaysIntoDatetimePickers() {
    enableEnd();

    let startDate = document.getElementById('js-search-form__datetime__start__date-picker').value;
    let startTime = document.getElementById('js-search-form__datetime__start__time-picker').value;

    let date = new Date(startDate + ' ' + (startTime !== null ? startTime : '00:00'));
    date.setDate(date.getDate() + 10);
    let dateIn10Days = getDateString(date);

    setValuesOfDatetimePickers(startDate, startTime, dateIn10Days, null);
}

function enableEnd() {
    let allFutureEventsCheckbox = document.getElementById('js-search-form__datetime__end__checkbox');
    let endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    let endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');

    allFutureEventsCheckbox.checked = true;
    endDatePicker.disabled = false;
    endTimePicker.disabled = false;
}

function disableEndAndGetAllEventsFromStart() {
    let startDate = document.getElementById('js-search-form__datetime__start__date-picker').value;
    let startTime = document.getElementById('js-search-form__datetime__start__time-picker').value;

    setValuesOfDatetimePickers(startDate, startTime, null, null);

    let allFutureEventsCheckbox = document.getElementById('js-search-form__datetime__end__checkbox');
    let endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    let endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');

    endDatePicker.disabled = allFutureEventsCheckbox.checked !== true;
    endTimePicker.disabled = allFutureEventsCheckbox.checked !== true;
}

function setEndTimePickerMin(newMin) {
    let endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');
    endTimePicker.min = newMin;
}

function handleOnChangeOfStartDatePicker(startDatePicker) {
    let endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    endDatePicker.min = startDatePicker.value;

    if (startDatePicker.value === endDatePicker.value) {
        let startTimePicker = document.getElementById('js-search-form__datetime__start__time-picker');
        setEndTimePickerMin(startTimePicker.value);
    } else {
        setEndTimePickerMin("");
    }
}

function handleOnChangeOfEndDatePicker(endDatePicker) {
    let startDatePicker = document.getElementById('js-search-form__datetime__start__date-picker');

    if (startDatePicker.value === endDatePicker.value) {
        let startTimePicker = document.getElementById('js-search-form__datetime__start__time-picker');
        setEndTimePickerMin(startTimePicker.value);
    } else {
        setEndTimePickerMin("");
    }
}

function handleOnChangeOfStartTimePicker(startTimePicker) {
    let startDatePicker = document.getElementById('js-search-form__datetime__start__date-picker');
    let endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');

    if (startDatePicker.value === endDatePicker.value) {
        setEndTimePickerMin(startTimePicker.value);
    }
}

function handleRadioButtonsForGPSInput() {
    let gpsRadioButton = document.getElementById('js-search-form__location__options__gps');
    let gpsLongitude = document.getElementById('js-search-form__location__gps-longitude');
    let gpsLatitude = document.getElementById('js-search-form__location__gps-latitude');
    let radiusSpecification = document.getElementById('js-search-form__location__radius');

    gpsLongitude.disabled = gpsRadioButton.checked !== true;
    gpsLatitude.disabled = gpsRadioButton.checked !== true;
    gpsLongitude.required = gpsRadioButton.checked === true;
    gpsLatitude.required = gpsRadioButton.checked === true;
    radiusSpecification.disabled = gpsRadioButton.checked !== true;
}

function handleFormSubmission(event, data) {
    event.preventDefault();
    let queryValue = document.getElementById("js-search-form__location__municipality").value;
    if (queryValue === "") {
        filterEventsAndLoadMap(data);
    } else {
        searchLocationAndFilterEventsAndLoadMap(data, queryValue);
    }
}

function handleFirstLoad(data) {
    getAllFutureEvents();
    filterEventsAndLoadMap(data);
}
function prefixWithZero(value) {
    return ('0' + value).slice(-2);
}

function getDateString(date) {
    const day = prefixWithZero(date.getDate());
    const month = prefixWithZero(date.getMonth() + 1);
    const year = date.getFullYear();

    return year + '-' + month + '-' + day;
}

function getTimeString(date) {
    const hours = prefixWithZero(date.getHours());
    const minutes = prefixWithZero(date.getMinutes());

    return hours + ':' + minutes;
}

function setValuesOfDatetimePickers(startDate, startTime, endDate, endTime) {
    if (startDate && endDate && endDate < startDate) {
        throw `'endDate'(${endDate}) is before 'startDate'(${startDate})!`;
    }
    if (startDate && endDate && startTime && endTime && startDate === endDate && endTime < startTime) {
        throw `'endTime'(${endTime}) is before 'startTime'(${startTime}) on the same date(${startDate})!`;
    }

    const startDatePicker = document.getElementById('js-search-form__datetime__start__date-picker');
    const startTimePicker = document.getElementById('js-search-form__datetime__start__time-picker');
    const endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    const endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');

    startDatePicker.value = startDate;
    startDatePicker.min = startDate;
    startTimePicker.value = startTime;

    endDatePicker.value = endDate;
    endDatePicker.min = startDate;
    endTimePicker.value = endTime;
    if (startDatePicker.value === endDatePicker.value) endTimePicker.min = startTime;
}

function setFutureIntoDatetimePickers() {
    const date = new Date();
    const today = getDateString(date);
    const now = getTimeString(date);

    setValuesOfDatetimePickers(today, now, null, null);
}

function enableEnd() {
    const endDatetimeCheckbox = document.getElementById('js-search-form__datetime__end__checkbox');
    const endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    const endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');

    endDatetimeCheckbox.checked = true;
    endDatePicker.disabled = false;
    endTimePicker.disabled = false;
}

function setTodayIntoDatetimePickers() {
    enableEnd();

    const date = new Date();
    const today = getDateString(date);
    const now = getTimeString(date);

    setValuesOfDatetimePickers(today, now, today, null);
}

function setTomorrowIntoDatetimePickers() {
    enableEnd();

    const date = new Date();
    date.setDate(date.getDate() + 1);
    const tomorrow = getDateString(date);

    setValuesOfDatetimePickers(tomorrow, null, tomorrow, null);
}

function setNext10DaysIntoDatetimePickers() {
    enableEnd();

    const startDate = document.getElementById('js-search-form__datetime__start__date-picker').value;
    const startTime = document.getElementById('js-search-form__datetime__start__time-picker').value;

    const date = new Date(startDate + ' ' + (startTime !== null ? startTime : '00:00'));
    date.setDate(date.getDate() + 10);
    const dateIn10Days = getDateString(date);

    setValuesOfDatetimePickers(startDate, startTime, dateIn10Days, null);
}

function handleEndDatetimeCheckboxClick(endDatetimeCheckbox) {
    const startDate = document.getElementById('js-search-form__datetime__start__date-picker').value;
    const startTime = document.getElementById('js-search-form__datetime__start__time-picker').value;

    setValuesOfDatetimePickers(startDate, startTime, null, null);

    const endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    const endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');

    endDatePicker.disabled = endDatetimeCheckbox.checked !== true;
    endTimePicker.disabled = endDatetimeCheckbox.checked !== true;
}

function setEndTimePickerMin(newMin) {
    const endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');
    endTimePicker.min = newMin;
}

function handleStartDatePickerOnChange(startDatePicker) {
    const endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    endDatePicker.min = startDatePicker.value;

    if (startDatePicker.value === endDatePicker.value) {
        const startTimePicker = document.getElementById('js-search-form__datetime__start__time-picker');
        setEndTimePickerMin(startTimePicker.value);
    } else {
        setEndTimePickerMin("");
    }
}

function handleStartTimePickerOnChange(startTimePicker) {
    const startDatePicker = document.getElementById('js-search-form__datetime__start__date-picker');
    const endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');

    if (startDatePicker.value === endDatePicker.value) {
        setEndTimePickerMin(startTimePicker.value);
    }
}

function handleEndDatePickerOnChange(endDatePicker) {
    const startDatePicker = document.getElementById('js-search-form__datetime__start__date-picker');

    if (startDatePicker.value === endDatePicker.value) {
        const startTimePicker = document.getElementById('js-search-form__datetime__start__time-picker');
        setEndTimePickerMin(startTimePicker.value);
    } else {
        setEndTimePickerMin("");
    }
}
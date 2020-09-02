function setCurrentDatetimeIntoPickers() {
    let date = new Date();

    let day = ('0' + date.getDate()).slice(-2);
    let month = ('0' + (date.getMonth() + 1)).slice(-2);
    let year = date.getFullYear();
    let hours = ('0' + date.getHours()).slice(-2);
    let minutes = ('0' + date.getMinutes()).slice(-2);

    let today = year + '-' + month + '-' + day;
    let now = hours + ':' + minutes

    let startDatePicker = document.getElementById('js-search-form__datetime__start__date-picker');
    let startTimePicker = document.getElementById('js-search-form__datetime__start__time-picker');
    let endDatePicker = document.getElementById('js-search-form__datetime__end__date-picker');
    let endTimePicker = document.getElementById('js-search-form__datetime__end__time-picker');

    startDatePicker.value = today;
    startDatePicker.min = today;
    startTimePicker.value = now;

    endDatePicker.value = today;
    endDatePicker.min = today;
    endTimePicker.value = '23:59';
    endTimePicker.min = now;
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

function disableLocationInputWhenOnlineChecked() {
    let onlineCheckBox = document.getElementById('js-search-form__checkboxes__online');
    let municipalitySearch = document.getElementById('js-search-form__location__municipality');
    let radiusSpecification = document.getElementById('js-search-form__location__radius');

    municipalitySearch.disabled = onlineCheckBox.checked === true;
    radiusSpecification.disabled = onlineCheckBox.checked === true;
}

function handleFormSubmission(event) {
    event.preventDefault();
    filterEventsAndLoadMap(data);
}
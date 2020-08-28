function setCurrentDatetimeIntoPickers() {
    let date = new Date();

    let day = ('0' + date.getDate()).slice(-2);
    let month = ('0' + (date.getMonth() + 1)).slice(-2);
    let year = date.getFullYear();
    let hours = ('0' + date.getHours()).slice(-2);
    let minutes = ('0' + date.getMinutes()).slice(-2);

    let today = year + '-' + month + '-' + day;
    let now = hours + ':' + minutes

    let datePicker = $('#js-search-form__datetime__date-picker');
    let timePicker = $('#js-search-form__datetime__time-picker');

    datePicker.val(today);
    datePicker.attr('min', today);
    timePicker.val(now);
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
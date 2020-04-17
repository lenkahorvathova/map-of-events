def parse_date(date: str) -> (str, str):
    start, _, end = date.partition('-')

    start = start.strip()
    end = end.strip()

    if not is_datetime(start):
        if is_datetime(start, "date"):
            start += "\xa000:00"
        else:
            return None

    start_date, _, _ = start.partition('\xa0')
    if not is_datetime(end):
        if is_datetime(end, "date"):
            end += "\xa023:59"
        elif is_datetime(end, "time"):
            end = start_date + '\xa0' + end
        else:
            end = start_date + '\xa023:59'

    return start, end


def is_datetime(date_string: str, partial: str = None) -> bool:
    date_split = date_string.strip().split('\xa0')

    if partial and len(date_split) == 1:
        date_strip = date_split[0].strip()

        if partial == "date" and len(date_strip.split('.')) == 3:
            return True

        if partial == "time" and len(date_strip.split(':')) == 2:
            return True

    if not partial and len(date_split) == 2:
        if is_datetime(date_split[0], "date") and is_datetime(date_split[1], "time"):
            return True

    return False

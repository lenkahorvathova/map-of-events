# Map of Events

This is a tool for parsing of events from provided web calendars. Found events are presented in a form of an interactive map.

## Setup
1. At your desired path create and go to a directory for this project:
    ```console
    user@server:your_path$ mkdir repository
    user@server:your_path$ cd repository
    ```

2. Clone the repository: 
    ```console
    user@server:your_path/repository$ git clone https://github.com/lenkahorvathova/map-of-events.git
    ```

3. [optional] Create and activate a Python environment:  
    > Python environment is for a project isolation, so all packages can be installed locally only for a particular project.
    ```console
    user@server:your_path/repository$ python3 -m venv venv
    user@server:your_path/repository$ source venv/bin/activate
    ```

4. Install requirements for the project:
    ```console
    (venv) user@server:your_path/repository$ pip install -r requirements.txt
    ```

5. Create and set up the project's database:
    ```console
    (venv) user@server:your_path/repository$ export PYTHONPATH=`pwd`
    (venv) user@server:your_path/repository$ python3 bin/setup_db.py
    ```

6. Allow execution of the shell scripts:
    ```console
    (venv) user@server:your_path/repository$ chmod +x bin/process.sh
    (venv) user@server:your_path/repository$ chmod +x bin/send_email.sh
    (venv) user@server:your_path/repository$ chmod +x bin/clean_up_files.sh
    ```
   
## Launch

1. Manually change paths in all 3 shell scripts to the paths related to your project.
    * e.g. path variables in *bin/process.sh*:
        ```shell
        PROJECT_DIR="/your_path"
        REPOSITORY_DIR="${PROJECT_DIR}/repository"
        ```

2. Launch the tool.
    - ### one-time launch
        This will launch the tool only once. This shell script ensures that the Python scripts are executed in the correct order.
        ```console
        user@server:~$ ./your_path/repository/bin/process.sh
        ```
    - ### regular launch
        This will set up regular execution of the tool using **cron** service.  
        > The process for parsing of events and generating of websites runs every day at 8 a.m.  
        An email with a weekly reminder to check crawler's status is being sent every Monday at 9 a.m.  
        Clean-up of old HTML files is performed monthly at 8:30 a.m.

        ```console
        user@server:~$ crontab -e

        0 8 * * * /your_path/repository/bin/process.sh
        0 9 * * MON /your_path/repository/bin/send_email.sh
        0 7 1 * * /your_path/repository/bin/clean_up_files.sh
        ```
    - ### running scripts separately  
        Each of the Python scripts can be run separately and provides its description with several CLI arguments.
        - e.g. check *bin/geocode_location.py* script's arguments and run the script in a testing mode
            ```console
            (venv) user@server:your_path/repository$ python3 bin/geocode_location.py --help
            (venv) user@server:your_path/repository$ python3 bin/geocode_location.py --dry-run
            ```
   
## Add a new calendar

1. Add a calendar's definition into main input file *your_path/repository/resources/input_website_base.json*.
    - there are several keys available:
        1. **domain** [required] – a unique string denoting the calendar's domain with underscores instead of special characters (e.g. *sezemice_cz*)
        2. **url** [this or ***old_urls*** required] – an active URL address of the calendar (e.g. *https://sezemice.cz/akce/*)
        3. **old_urls** [this or ***url*** required] – an array of all old URL addresses that had been used for the calendar before ***url*** changed (e.g. *["http://www.sezemice.cz/ap"]*)
        4. **parser** [required] – a name of a template file to use for the parser (e.g. *vismo*)
        5. **default_gps** [optional] – default GPS coordinates in a decimal form in a latitude-longitude order separated with a comma, if the calendar represents a specific village or town (e.g. *50.0665, 15.8526*)
        6. **default_location** [optional] – a default location string that means a name of the village or town the calendar is representing (e.g. *Město Sezemice*)
        7. **encoding** [optional] – an encoding to use for the HTML content of the calendar, if it is specified incorrectly (e.g. *utf-8*)
        8. **verify** [optional] – an indication whether to perform a verification of the calendar's certificate (default is *true*)
        9. **note** [optional] – a note for the information purpose only
    - a minimal structure:
        ```json
            {
                "domain": "<UNIQUE_CALENDAR_DOMAIN_STRING>",
                "url": "<CALENDAR_URL>",
                "parser": "<PARSER_TEMPLATE_FOR_CALENDAR>"
            }
        ```

2. Prepare a template for the parser to use when processing the calendar.
    1. create a file for the template: *your_path/repository/resources/parsers/<PARSER_TEMPLATE_FOR_CALENDAR>.json*
    2. fill in the template's structure:
        - main structure:
            ```json
            {
                "calendar": {
                    "root": {},
                    "event_url": {}
                },
                "event": {
                    "root": {},
                    "title": {},
                    "perex": {},
                    "datetime": {},
                    "location": {},
                    "gps": {},
                    "organizer": {},
                    "types": {}
                }
            }
            ```
        - for each of the keys you can specify this information:  
            ```json
                    "<KEY>": {
                        "xpath": {
                            "selectors": [],
                            "join_separator": "",
                            "split_separator": "",
                            "match": ""
                        },
                        "regex": {
                            "expressions": [],
                            "group": {},
                            "match": ""
                        }
                    },
            ```
        - **calendar**'s *root* and *event_url* keys and **event**'s *root*, *title* and *datetime* keys are MANDATORY
        - if event's date and time are defined together use *datetime* key, or else you can use separate keys *date* and *time*
        - parameter ***xpath*** is MANDATORY
            - [required] *selectors* array contains XPATHs to the key on the webpage
            - an element on the xpath is stripped from HTML tags and only inner text is used, if you need only the first level text of the element use */text()* as the last part of the xpath
            - *join_separator* and *split_separator* are mutually exclusive
            - *join_separator* joins returned values into a string using provided separator
            - *split_separator* splits returned values into an array using provided separator
        - parameter ***regex*** is OPTIONAL and applies to the result from ***xpath***
            - [required] *expressions* array contains regular expressions which you want to use
            - in *group* you can define a name for the value matched under a specific capturing group (<group_number>: <name_for_the_value>) and dictionary is created with those values, otherwise an array of matched values is created
            - if the expresion has specified capturing groups but without *group* key, an array of matches from all groups is created
        - if you want only the first value from all values found, use 'FIRST' in *match* (default value is 'ALL', which uses all found values)
        - keys *datetime* and *types* are expected to be an array of values, the rest of the keys are expected to have only one final value 

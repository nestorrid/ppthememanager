from flask import Flask
from flask import request
import csv
import json
from pathlib import Path
import os

app = Flask(__name__)
default_path = 'themes/'


@app.route('/')
def index():
    return json.dumps({
        'GET /': 'api list',
        'GET /themes/': 'get all theme names',
        'POST /themes/action/': 'create, update, load specific theme',
    })


@app.route('/themes/', methods=['GET'])
def get_theme_name_list():
    path = request.args.get('p', None)
    result = get_csv_filenames_in_path(path)
    if len(result) == 0:
        return build_error_response("No themes were found.")

    return build_succ_response(result, **{"count": len(result)})


@app.route('/themes/action/', methods=['POST'])
def update_theme():
    data = request.get_json()
    validation = basic_validate(
        data,
        is_valid_method,
        is_data_contains_theme
    )
    if not validation[0]:
        return build_error_response(validation[1])

    method = data.get('method')
    path = data.get('path', None)
    theme = data.get('theme')

    if method == "create":
        use_template = data.get('template', None)
        result = create_new_theme(theme, path, use_template)
        if not result[0]:
            return build_error_response(result[1])
        result = get_csv_filenames_in_path(path)
        info = {
            "action": "create",
            "count": len(result)
        }
        return build_succ_response(result, **info)
    elif method == "update":
        validation = basic_validate(
            data,
            is_data_contains_name,
            is_data_contains_value
        )
        if not validation[0]:
            return build_error_response(validation[1])
        result = update_color_in_theme(data)
        info = {
            "theme": theme,
            "keys": list(result.keys()),
            "count": len(result.keys())
        }
        return build_succ_response(result, **info)
    elif method == "load":
        if not is_theme_exists(theme, path):
            return build_error_response(f'Theme {theme} does not exist.')
        result = read_theme_data(theme, path)
        info = {
            "theme": theme,
            "keys": list(result.keys()),
            "count": len(result.keys())
        }
        return build_succ_response(result, **info)


@app.route('/themes/apply/', methods=['POST'])
def apply_theme():
    data = request.get_json()
    validation = basic_validate(
        data,
        is_data_contains_theme,
        is_reading_exists_theme
    )
    if not validation[0]:
        return build_error_response(validation[1])

    path = data.get('path')
    theme = data.get('theme')
    return json.dumps(read_theme_data(theme, path))


def basic_validate(data: dict, *validators):
    results = list(filter(lambda r: not r[0], [
        v(data) for v in validators
    ]))

    if len(results) > 0:
        return results[0]

    return (True,)


def is_reading_exists_theme(data):
    if not is_theme_exists(data.get('theme'), data.get('path')):
        return False, f"Theme {data.get('theme')} does not exist."
    return (True,)


def is_data_contains_theme(data):
    if not data.get("theme") or not isinstance(data["theme"], str):
        return False, "Please provide a theme name with key: 'theme'."
    return (True,)


def is_data_contains_name(data):
    if not data.get('name') or not isinstance(data["name"], str):
        return False, "No color name is provided. Use key 'name'. e.g. {'name':'primary-hover'}"
    return (True,)


def is_data_contains_value(data):
    if not data.get('value') or not isinstance(data["value"], str):
        return False, "Please provide a valid color string with key 'value'."
    return (True,)


def is_valid_method(data):
    method = data.get('method', "fail")
    if not method in ['create', 'update', 'load']:
        return False, "Invalid method, use 'create', 'update', 'load'."
    return (True,)


def is_theme_exists(theme, path=None):
    full_path = get_csv_full_name(theme, path)
    return os.path.exists(full_path) and os.path.isfile(full_path)


def get_csv_filenames_in_path(path=None):
    p = Path(path or default_path)
    if not os.path.exists(p):
        return build_error_response(f"Path '{path}' does not exist.")

    themes = [
        f.name.replace('.csv', '')
        for f in p.iterdir()
        if f.name.endswith('.csv')]

    themes.sort(key=lambda x: os.path.getctime(
        os.path.join(p, x+'.csv')), reverse=True)

    return themes


def build_error_response(msg):
    result = {"result": "error", "msg": msg}
    return json.dumps(result)


def build_succ_response(jsonData, **additionalData):
    data = {"result": "succ", "data": jsonData}
    data = dict(data, **additionalData)
    resp = json.dumps(data)
    return resp


def update_color_in_theme(data: dict, path=None):
    titles, rows = read_theme_rowdata(data['theme'], path)
    keys = data['name'].split("-")

    if len(keys) == 1:
        keys.append('main')

    if not keys[1] in titles:
        titles.append(keys[1])
        for row in rows:
            row.append("")

    tag_idx = titles.index(keys[1])
    names = [row[0] for row in rows]

    if keys[0] in names:
        name_idx = names.index(keys[0])
        rows[name_idx][tag_idx] = data['value']
    else:
        row = ["" for _ in range(len(titles))]
        row[0] = keys[0]
        row[tag_idx] = data['value']
        rows.append(row)

    rows.insert(0, titles)
    new_data = write_data_to_file(rows, data['theme'])
    return new_data


def write_data_to_file(rows: list, theme: str, path=None):
    full_name = get_csv_full_name(theme, path)
    with open(full_name, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerows(rows)

    data = read_theme_data(theme, path)
    return data


def create_new_theme(name, path=None, use_template=None):
    """
    Just create a new csv file for the theme and add titles at first line
    """
    fullpath = get_csv_full_name(name, path)
    if is_theme_exists(name, path):
        return False, f"Theme '{name}' already exists."

    rows = []
    rows.append(get_standard_theme_titles())

    if use_template == '1':
        for name in get_standard_color_names():
            row = [name, "#000000"]
            row.extend(
                ["" for _ in range(2, len(get_standard_theme_titles()))])
            rows.append(row)

    with open(fullpath, 'w') as f:
        csv.writer(f).writerows(rows)

    return (os.path.exists(fullpath), "Error occurred while creating new theme.")


def get_standard_theme_titles() -> list[str]:
    return [
        'name',
        'main',
        '0',
        '1',
        '2',
        '3',
        '4',
        '5',
        '6',
        '7',
        '8',
        '9',
        'hover',
        'click',
        'disabled'
    ]


def get_standard_color_names() -> list[str]:
    return [
        "primary",
        "secondary",
        "accent",
        "background",
        "text",
        "subtext",
        "link",
        "border",
        "shadow",
        "divider",
        "success",
        "info",
        "warning",
        "fail",
    ]


def read_theme_rowdata(filename, path=None):
    full_name = get_csv_full_name(filename, path)
    with open(full_name) as theme:
        reader = csv.reader(theme)
        titles = next(reader)
        rows = [row for row in reader]
        return titles, rows


def get_csv_full_name(name, path=None):
    path = path or default_path
    if not name.endswith(".csv"):
        name = name + ".csv"
    return os.path.join(path, name)


def read_theme_data(filename, path=None):
    full_name = get_csv_full_name(filename, path)

    with open(full_name) as theme:
        titles = next(csv.reader(theme))
        data = {
            f'{row[0]}-{titles[i]}'.replace(f'-{titles[1]}', ''): f'{row[i]}'
            for idx, row in enumerate(csv.reader(theme))
            for i in range(1, len(row)) if len(row[i]) > 0
        }

    return data

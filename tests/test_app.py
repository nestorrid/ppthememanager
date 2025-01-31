import pytest
import os
from pathlib import Path
from app import *
from flask import Flask
import json
from pprint import pprint

"""
create a new theme
{
    "theme": str
    "title": [str]
    "method": "create"
    "c1": {str: color_str}
    "c2": {"vlaue": "#FF00FF", "hover": "#FF00FF", "click":"#FF00FF", "disabled":"#FF00FF"},
    "c3": {"value": "#FF00FF", "0": "#FF00FF", "1":"#FF00FF", "2":"#FF00FF"}
}
update a theme color
{
    "theme": str
    "color": str name.tag
    "value": str
    "method": "update"
}

delete a theme color
{
    "theme": str
    "color": str name.tag
    "method": "delete"
}
"""


@pytest.fixture
def filename():
    return os.path.join('themes', 'pytest_theme.csv')


@pytest.fixture
def client() -> Flask:
    return app.test_client()


def test_index(client):
    resp = client.get("/")
    data = json.loads(resp.data.decode("utf-8"))
    assert data.get('GET /') == 'api list'
    assert "api list" in resp.text


def test_get_theme_list_succ(client):
    resp = client.get('/themes/')
    count = get_csv_file_count_in_path('themes/')
    data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert 'succ' in resp.text
    assert count == len(data['data'])


def test_get_theme_list_in_empty_path_should_fail(client):
    resp = client.get('/themes/?p=themes_test/empty')
    assert resp.status_code == 200
    assert 'error' in resp.text
    assert 'No themes' in resp.text


def test_get_theme_list_in_wrong_path_should_fail(client):
    resp = client.get('/themes/?p=somewhere')
    assert resp.status_code == 200
    assert 'error' in resp.text
    assert 'does not exist' in resp.text


@pytest.mark.parametrize('path', ['themes/', 'themes_test/'])
def test_get_csv_files_in_path_succ(path):
    count = get_csv_file_count_in_path(path)
    names = get_csv_filenames_in_path(path)
    assert len(names) == count


def get_csv_file_count_in_path(path):
    return len([f for f in os.listdir(path) if f.endswith('.csv')])


def test_read_csv():
    data = read_theme_data('default')
    print(data)


def test_write_csv(filename):
    titles = get_standard_theme_titles()
    colors = ['color1', 'color2', 'color3']
    rows = [
        [f'{c}'] + ['#000000' for _ in range(1, len(titles))]
        for c in colors
    ]
    with open(filename, 'w') as file:
        writer = csv.writer(file)
        writer.writerow(titles)
        writer.writerows(rows)


def test_update_color_for_tag(filename):
    target = "color2-3"
    value = '#FFAC33'
    name, tag = target.split('-')
    tag = tag or 'main'
    idx = get_standard_theme_titles().index(tag)
    print(idx)
    with open(filename) as file:
        reader = csv.reader(file)
        for row in reader:
            if row[0] == name and idx >= 0:
                row[idx] = value
            elif row[0] == name and idx == -1:
                row.append(value)
            elif idx == -1:
                row.append('')
            print(row)


def test_api_update_theme_to_create_new_theme_should_success(client):
    target = os.path.join(default_path, 'pytest_theme.csv')
    if os.path.exists(target):
        os.remove(target)

    data = {
        "method": "create",
        "theme": "pytest_theme"
    }

    resp = client.post(
        '/themes/action/',
        data=json.dumps(data),
        content_type="application/json"
    )
    assert resp.status_code == 200
    assert 'succ' in resp.text
    assert 'pytest_theme' in resp.text


def test_api_update_theme_to_create_existing_theme_should_fail(client):
    data = {
        "method": "create",
        "theme": "pytest_theme"
    }
    resp = client.post(
        '/themes/action/',
        data=json.dumps(data),
        content_type="application/json"
    )
    print(resp.text)
    assert resp.status_code == 200
    assert 'error' in resp.text
    assert 'already exists' in resp.text


def test_valid_color_data_should_return_True():
    result = is_valid_color_data({
        "theme": "theme_name",
        "name": "test-3",
        "value": "#FF1133"
    })
    assert result[0] == True


@pytest.mark.parametrize("data", [
    {
        "name": "test-3",
        "value": "#FF1133"
    },
    {
        "theme": "theme_name",
        "value": "#FF1133"
    },
    {
        "theme": "theme_name",
        "name": "test-3",
    },
    {
        "theme": "theme_name",
        "name": "test-3",
        "value": "#FF1133123123"
    }
])
def test_invalid_color_data_should_return_False(data):
    result = is_valid_color_data(data)
    assert result[0] == False
    assert len(result[1]) > 0


def test_api_update_theme_with_update_color(client):
    resp = client.post(
        "/themes/action/",
        data={
            "theme": "theme_name",
            "name": "test-3",
            "value": "#FF1133"
        },
        content_type="application/json"
    )


def test_read_theme_rowdata():
    titles, rows = read_theme_rowdata("default")
    names = [row[0] for row in rows]
    print(names)
    print(titles)


def test_update_color_in_theme():
    data = {
        "theme": "pytest_theme",
        "name": "aaa-new1",
        "value": "#AE32E1"
    }
    result = update_color_in_theme(data)
    assert result[data['name']] == data['value']


def test_apply_theme_with_exists_theme_should_success(client):
    resp = client.get("/themes/default/apply")
    assert resp.status_code == 200
    assert "#" in resp.text


def test_basic_validate_with_empty_dict_should_fail():
    result = basic_validate({}, is_valid_method, is_data_contains_theme)
    print(result)
    assert len(result) == 2
    assert result[0] == False
    assert len(result[1]) > 0


def test_basic_validate_with_right_values_should_succ():
    result = basic_validate({
        'theme': 'test',
        'method': 'load'
    }, is_valid_method, is_data_contains_theme)
    print(result)
    assert result[0]


def test_reading_exist_theme_should_succ():
    result = is_reading_exists_theme({
        "theme": "default"
    })
    assert result[0]


def test_reading_noexists_theme_should_fail():
    result = is_reading_exists_theme({
        "theme": "this theme does not exist"
    })
    assert not result[0]


def test_api_action_create(client):
    data = {
        "theme": "new_theme",
        "method": "create"
    }


def test_api_action_load(client):
    data = {
        "theme": "default",
        "method": "load"
    }


def test_api_action_update(client):
    data = {
        "theme": "pytest_theme",
        "method": "update",
        "name": "test-3",
        "value": "#AA0032"
    }


def test_api_apply(client):
    data = {
        "theme": "default",
        "method": "apply"
    }

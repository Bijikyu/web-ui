import sys  # add project root to path
sys.path.append('.')  # enable src imports
from unittest.mock import mock_open, patch  # import mocking tools
from src.utils.file_utils import load_json_safe  # function to test


def test_load_json_safe_success():  # parse existing JSON file into dict
    data = '{"a": 1}'  # sample json text
    with patch('os.path.exists', return_value=True):  # pretend file exists
        with patch('builtins.open', mock_open(read_data=data)):  # mock file open
            result = load_json_safe('file.json')  # call util
    assert result == {"a": 1}  # expect parsed dict


def test_load_json_safe_invalid_json():  # invalid JSON logs error and returns None
    bad = '{invalid'  # malformed json text
    with patch('os.path.exists', return_value=True):  # pretend file exists
        with patch('builtins.open', mock_open(read_data=bad)):  # mock file open
            with patch('src.utils.file_utils.logger') as log:  # capture logs
                result = load_json_safe('bad.json')  # call util
                log.error.assert_called()  # ensure logged
    assert result is None  # expect None result


def test_load_json_safe_missing_file():  # nonexistent file yields None
    with patch('os.path.exists', return_value=False):  # path does not exist
        result = load_json_safe('missing.json')  # call util
    assert result is None  # expect None result

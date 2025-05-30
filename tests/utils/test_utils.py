import types  # module utilities
import sys  # allow src imports
sys.modules.setdefault("requests", types.ModuleType("requests"))
sys.modules.setdefault("gradio", types.ModuleType("gradio"))
sys.path.append('.')  # include project root
import base64  # for expected encoding
from types import SimpleNamespace  # create fake stat
from unittest.mock import MagicMock, mock_open, patch  # mocking tools
from src.utils.utils import encode_image, get_latest_files  # functions under test


def test_encode_image_success():
    """Binary image data should be encoded to base64 string."""  #(added docstring summarizing test intent)
    # encode bytes and return base64 string
    data = b'abc'  # sample bytes
    m = mock_open(read_data=data)  # mock binary file
    m.return_value.read.return_value = data  # ensure bytes returned
    expected = base64.b64encode(data).decode('utf-8')  # expected string
    with patch('builtins.open', m):  # patch open
        result = encode_image('img.png')  # call util
    assert result == expected  # compare result


def test_encode_image_none():
    """None path input should return None from encode_image."""  #(added docstring summarizing test intent)
    # None path should yield None
    assert encode_image(None) is None  # expect None returned


def fake_path(path, mtime):  # helper to build fake Path
    stat = SimpleNamespace(st_mtime=mtime)  # fake stat object
    p = MagicMock()  # create mock path
    p.stat.return_value = stat  # stub stat
    p.__str__.return_value = path  # str output
    return p  # return mock


def test_get_latest_files():
    """Return the latest file per extension from a directory."""  #(added docstring summarizing test intent)
    # select most recent file for each extension
    webm1 = fake_path('/dir/a.webm', 50)  # older webm
    webm2 = fake_path('/dir/b.webm', 100)  # newer webm
    zip1 = fake_path('/dir/a.zip', 60)  # zip file
    with patch('os.path.exists', return_value=True):  # pretend dir exists
        with patch('src.utils.utils.Path.rglob') as rg:  # patch file search
            with patch('time.time', return_value=150):  # fixed time
                def side(pattern):  # side effect per extension
                    if pattern == '*.webm':  # match webm
                        return [webm1, webm2]  # return list
                    if pattern == '*.zip':  # match zip
                        return [zip1]  # return list
                    return []  # default empty
                rg.side_effect = side  # assign side effect
                result = get_latest_files('/dir')  # call util
    assert result['.webm'] == '/dir/b.webm'  # newest webm path
    assert result['.zip'] == '/dir/a.zip'  # latest zip path


def test_get_latest_files_missing_dir():
    """Create directory when missing and return placeholders."""  #(added docstring summarizing test intent)
    # handle missing directory by creating it
    with patch('os.path.exists', return_value=False):  # simulate missing dir
        with patch('src.utils.utils.ensure_dir') as mk:  # patch dir helper
            result = get_latest_files('/missing')  # call util
            mk.assert_called_once_with('/missing')  # ensure called
    assert result == {'.webm': None, '.zip': None}  # expect empty dict

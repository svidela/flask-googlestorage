import pytest


@pytest.mark.parametrize("file, content", [("foo.txt", "Foo content"), ("bar.txt", "Bar content")])
def test_get_file(file, content, app_tmp):
    with app_tmp.test_client() as client:
        rv = client.get(f"/_uploads/files/{file}")
        assert rv.status_code == 200
        assert rv.get_data(as_text=True) == content


@pytest.mark.parametrize("url", ("/_uploads/files/biz.txt", "/_uploads/photos/foo.jpg"))
def test_get_file_not_found(url, app_tmp):
    with app_tmp.test_client() as client:
        rv = client.get(url)
        assert rv.status_code == 404

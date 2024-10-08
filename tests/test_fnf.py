

def test_process_fnf():
    from agent0 import process_stderr

    stderr = """Traceback (most recent call last):
      File "/opt/pycharm-community-2023.3.3/plugins/python-ce/helpers/pydev/pydevd.py", line 1534, in _exec
        pydev_imports.execfile(file, globals, locals)  # execute the script
      File "/opt/pycharm-community-2023.3.3/plugins/python-ce/helpers/pydev/_pydev_imps/_pydev_execfile.py", line 18, in execfile
        exec(compile(contents+"\n", file, 'exec'), glob, loc)
      File "scripts/python/zqvmnlef.py", line 33, in <module>
        response = classify_image_with_openai_api(image_file, api_key)
      File "scripts/python/zqvmnlef.py", line 19, in classify_image_with_openai_api
        with open(image_path, 'rb') as image:
    FileNotFoundError: [Errno 2] No such file or directory: '/home/jon/h2ogpt/papers/technical-report/images/h2oGPT-light.png'"""
    stderr_new = process_stderr(stderr)

    print(stderr_new)
    assert "Did you mean instead: '/home/jon/h2ogpt/papers/technical-report/images/h2oGPT-light.pdf'?" in stderr_new


def test_process_mnf():
    from agent0 import process_stderr

    stderr = """Traceback (most recent call last):
      File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
      File "<frozen importlib._bootstrap>", line 1004, in _find_and_load_unlocked
    ModuleNotFoundError: No module named '..python_tools.system_info'
    """

    stderr_new = process_stderr(stderr)

    print(stderr_new)
    assert "Did you mean instead: '..python_tools.get_system_info'?" in stderr_new

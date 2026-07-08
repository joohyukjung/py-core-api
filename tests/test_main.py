from py_core_api.main import main


def test_main_runs_without_error(capsys):
    main()
    captured = capsys.readouterr()
    assert captured.out == "Hello from py-core-api!\n"

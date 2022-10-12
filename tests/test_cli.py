import pytest

from simod import cli

# NOTE: these are mostly general overall long-running tests to check if everything finishes without exceptions

optimize_config_files = [
    'optimize_config.yml',
]


@pytest.mark.integration
@pytest.mark.parametrize('path', optimize_config_files)
def test_optimize(entry_point, runner, path):
    config_path = entry_point / path
    result = runner.invoke(cli.main, ['optimize', '--config_path', config_path.absolute()])
    assert not result.exception
    assert result.exit_code == 0

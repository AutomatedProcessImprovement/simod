import tempfile
import traceback
from pathlib import Path

from simod.configuration import Configuration
from simod.event_log.event_log import EventLog
from simod.event_log.preprocessor import Preprocessor
from simod.event_log.utilities import read
from simod.optimization.optimizer import Optimizer
from simod.utilities import get_project_dir, folder_id
from simod_http.app import Settings, Request
from simod_http.app import settings
from simod_http.archiver import Archiver
from simod_http.notifier import Notifier

logger = settings.logger


class Executor:
    """
    Job executor that runs Simod with the user's configuration.
    """

    def __init__(self, app_settings: Settings, request: Request):
        self.settings = app_settings
        self.request = request

    def run(self):
        with tempfile.TemporaryDirectory() as output_dir:
            logger.debug(
                f'Simod has been started from the request: {self.request}, '
                f'with the temporary directory: {output_dir}')

            try:
                result_dir = optimize_with_simod(self.request.configuration, Path(output_dir))
                archive_url = Archiver(self.settings, self.request, result_dir).as_tar_gz()
                # TODO: use internal host and port

                logger.debug(f'Archive URL: {archive_url}')

                if self.request.callback_endpoint is not None:
                    Notifier(archive_url).callback(self.request.callback_endpoint)

            except Exception as e:
                logger.exception(e)
                traceback.print_exc()

                Notifier().callback(self.request.callback_endpoint, error=e)


def optimize_with_simod(settings: Configuration, output_dir: Path) -> Path:
    # NOTE: EventLog requires start_time column to be present for split_log() to work.
    #   So, we do pre-processing before creating the EventLog object.

    log, csv_path = read(settings.common.log_path, settings.common.log_ids)

    preprocessor = Preprocessor(log, settings.common.log_ids)
    processed_log = preprocessor.run(
        multitasking=settings.preprocessing.multitasking,
    )

    test_log = None
    if settings.common.test_log_path is not None:
        test_log, _ = read(settings.common.test_log_path, settings.common.log_ids)

    event_log = EventLog.from_df(
        log=processed_log,  # would be split into training and validation if test is provided, otherwise into test too
        log_ids=settings.common.log_ids,
        process_name=settings.common.log_path.stem,
        test_log=test_log,
        log_path=settings.common.log_path,
        csv_log_path=csv_path,
    )

    if output_dir is None:
        output_dir = get_project_dir() / 'outputs' / folder_id()

    Optimizer(settings, event_log=event_log, output_dir=output_dir).run()

    return output_dir

import os
import platform as pl
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import yaml

from simod.cli_formatter import print_warning, print_step
from simod.configuration import PROJECT_DIR, StructureMiningAlgorithm, GatewayProbabilitiesDiscoveryMethod


@dataclass
class Settings:
    """Settings for the structure miner."""
    gateway_probabilities_method: GatewayProbabilitiesDiscoveryMethod
    mining_algorithm: StructureMiningAlgorithm = StructureMiningAlgorithm.SPLIT_MINER_3

    # Split Miner 1 and 3
    epsilon: Optional[float] = None
    eta: Optional[float] = None

    # Split Miner 2
    concurrency: Optional[float] = 0.0

    # Split Miner 3
    and_prior: Optional[bool] = False
    or_rep: Optional[bool] = False

    # Private
    _sm1_path: Path = PROJECT_DIR / 'external_tools/splitminer/splitminer.jar'
    _sm2_path: Path = PROJECT_DIR / 'external_tools/splitminer2/sm2.jar'
    _sm3_path: Path = PROJECT_DIR / 'external_tools/splitminer3/bpmtk.jar'

    @staticmethod
    def from_stream(stream: Union[str, bytes]) -> Optional['Settings']:
        settings = yaml.load(stream, Loader=yaml.FullLoader)

        if 'structure_optimizer' in settings:
            settings = settings['structure_optimizer']

        gateway_probabilities_method = settings.get('gateway_probabilities_method', None)
        if gateway_probabilities_method is not None:
            gateway_probabilities_method = GatewayProbabilitiesDiscoveryMethod.from_str(gateway_probabilities_method)

        mining_algorithm = settings.get('mining_algorithm', None)
        if mining_algorithm is None:
            mining_algorithm = settings.get('mining_alg', None)  # legacy key support
        if mining_algorithm is not None:
            mining_algorithm = StructureMiningAlgorithm.from_str(mining_algorithm)
        if mining_algorithm is None:
            print_warning('No mining algorithm specified.')
            return None

        epsilon = settings.get('epsilon', None)
        assert type(epsilon) is not list, 'epsilon must be a single value'

        eta = settings.get('eta', None)
        assert type(eta) is not list, 'eta must be a single value'

        concurrency = settings.get('concurrency', 0.0)
        assert type(concurrency) is not list, 'concurrency must be a single value'

        and_prior = settings.get('and_prior', None)
        if and_prior is not None:
            if isinstance(and_prior, str):
                and_prior = [and_prior.lower() == 'true']
            elif isinstance(and_prior, list):
                and_prior = and_prior
            else:
                raise ValueError('and_prior must be a list or a string.')

        or_rep = settings.get('or_rep', None)
        if or_rep is not None:
            if isinstance(or_rep, str):
                or_rep = [or_rep.lower() == 'true']
            elif isinstance(or_rep, list):
                or_rep = or_rep
            else:
                raise ValueError('or_rep must be a list or a string.')

        return Settings(
            gateway_probabilities_method=gateway_probabilities_method,
            mining_algorithm=mining_algorithm,
            epsilon=epsilon,
            eta=eta,
            concurrency=concurrency,
            and_prior=and_prior,
            or_rep=or_rep
        )

    def to_dict(self) -> dict:
        return {
            'mining_algorithm': self.mining_algorithm.value if self.mining_algorithm else None,
            'gateway_probabilities_method': self.gateway_probabilities_method.value if self.gateway_probabilities_method else None,
            'epsilon': self.epsilon,
            'eta': self.eta,
            'concurrency': self.concurrency,
            'and_prior': self.and_prior,
            'or_rep': self.or_rep
        }


class StructureMiner:
    """Discovers the process structure from a log file."""
    _settings: Settings
    _xes_path: Path
    _output_model_path: Path

    def __init__(self, settings: Settings, xes_path: Path, output_model_path: Path):
        self._settings = settings
        self._xes_path = xes_path
        self._output_model_path = output_model_path
        self._run()

    def _run(self):
        self._mining_structure(self._xes_path)

        assert self._output_model_path.exists(), \
            f"Model file {self._output_model_path} hasn't been mined"

    def _mining_structure(self, xes_path: Path):
        miner = self._get_miner(self._settings.mining_algorithm)
        miner(xes_path, self._settings)

    def _get_miner(self, miner: StructureMiningAlgorithm):
        if miner is StructureMiningAlgorithm.SPLIT_MINER_1:
            raise NotImplementedError('Split Miner 1 is not supported anymore.')
        elif miner is StructureMiningAlgorithm.SPLIT_MINER_2:
            return self._sm2_miner
        elif miner is StructureMiningAlgorithm.SPLIT_MINER_3:
            return self._sm3_miner
        else:
            raise ValueError(f'Unknown mining algorithm: {miner}')

    def _model_path_without_suffix(self) -> Path:
        if self._output_model_path is not None:
            return self._output_model_path.with_suffix('')
        else:
            raise ValueError('No output model path specified.')

    def _sm1_miner(self, xes_path: Path, settings: Settings):
        output_path = str(self._model_path_without_suffix())
        args = ['java', '-jar', settings._sm1_path,
                str(settings.epsilon), str(settings.eta),
                str(xes_path),
                output_path]

        print_step(f'SplitMiner1 is running with the following arguments: {args}')
        subprocess.call(args)

    def _sm2_miner(self, xes_path: Path, settings: Settings):
        output_path = str(self._model_path_without_suffix())
        sep = ';' if pl.system().lower() == 'windows' else ':'
        args = ['java']
        if not pl.system().lower() == 'windows':
            args.append('-Xmx2G')
        args.extend(
            ['-cp',
             (settings._sm2_path.__str__() + sep + os.path.join(os.path.dirname(settings._sm2_path), 'lib',
                                                                '*')),
             'au.edu.unimelb.services.ServiceProvider',
             'SM2',
             str(xes_path),
             output_path,
             str(settings.concurrency)]
        )

        print_step(f'SplitMiner2 is running with the following arguments: {args}')
        subprocess.call(args)

    def _sm3_miner(self, xes_path: Path, settings: Settings):
        output_path = str(self._model_path_without_suffix())
        sep = ';' if pl.system().lower() == 'windows' else ':'

        args = ['java']

        if not pl.system().lower() == 'windows':
            args.extend(['-Xmx2G', '-Xms1024M'])

        and_prior_setting = str(settings.and_prior).lower()

        or_rep_setting = str(settings.or_rep).lower()

        args.extend([
            '-cp',
            (settings._sm3_path.__str__() + sep + os.path.join(os.path.dirname(settings._sm3_path), 'lib', '*')),
            'au.edu.unimelb.services.ServiceProvider',
            'SMD',
            str(settings.epsilon),
            str(settings.eta),
            and_prior_setting, or_rep_setting, 'false',
            str(xes_path),
            output_path
        ])

        print_step(f'SplitMiner3 is running with the following arguments: {args}')
        subprocess.call(args)

from setuptools import setup, find_packages

setup(
    name='simod',
    version='3.1.0',
    packages=find_packages(where='src'),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        'click',
        'pandas',
        'numpy',
        'networkx',
        'matplotlib',
        'lxml',
        'xmltodict',
        'jellyfish',
        'scipy',
        'statistics',
        'tqdm',
        'PyYAML',
        'hyperopt',
        'pytz',
        'pytest',
        'pytest-cov',
        'pre-commit',
        'invoke',
        'setuptools',
        'pendulum',
        'pydantic',
        'fastapi',
        'uvicorn',
        'python-dotenv',
    ],
    entry_points={
        'console_scripts': [
            'simod = simod.cli:main',
        ]
    }
)

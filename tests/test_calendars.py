import uuid

import pandas as pd
import pytest

from bpdfr_simulation_engine.resource_calendar import CalendarFactory
from pm4py_wrapper.wrapper import convert_xes_to_csv
from simod.calendar_discovery import case_arrival
from simod.calendar_discovery import resource as resource_calendar
from simod.event_log import read
from simod.extraction.role_discovery import ResourcePoolAnalyser


def test_calendar_module(entry_point):
    log_path = entry_point / 'PurchasingExample.xes'
    log_path_csv = log_path.with_stem(str(uuid.uuid4())).with_suffix('.csv')
    convert_xes_to_csv(log_path, log_path_csv)

    df = pd.read_csv(log_path_csv)
    log_path_csv.unlink()
    df['start_timestamp'] = pd.to_datetime(df['start_timestamp'])
    df['time:timestamp'] = pd.to_datetime(df['time:timestamp'])
    calendar_factory = CalendarFactory(15)

    for (_, row) in df.iterrows():
        resource = row['org:resource']
        activity = row['concept:name']
        start_timestamp = row['start_timestamp'].to_pydatetime()
        end_timestamp = row['time:timestamp'].to_pydatetime()
        calendar_factory.check_date_time(resource, activity, start_timestamp)
        calendar_factory.check_date_time(resource, activity, end_timestamp)

    calendar_candidates = calendar_factory.build_weekly_calendars(0.1, 0.7, 0.4)

    calendar = {}
    for resource_id in calendar_candidates:
        if calendar_candidates[resource_id] is not None:
            calendar[resource_id] = calendar_candidates[resource_id].to_json()

    assert len(calendar) > 0
    assert 'Kim Passa' in calendar


@pytest.mark.parametrize('log_name', ['DifferentiatedCalendars.xes'])
def test_calendar_discover_undifferentiated(entry_point, log_name):
    log_path = entry_point / log_name
    log, log_path_csv = read(log_path)
    result = resource_calendar.discover_undifferentiated(log)
    assert result
    log_path_csv.unlink()


@pytest.mark.parametrize('log_name', ['DifferentiatedCalendars.xes'])
def test_calendar_discover_per_resource_pool(entry_point, log_name):
    log_path = entry_point / log_name
    log, log_path_csv = read(log_path)
    result = resource_calendar.discover_per_resource_pool(log)
    assert result
    log_path_csv.unlink()


@pytest.mark.parametrize('log_name', ['DifferentiatedCalendars.xes'])
def test_calendar_discover_per_resource(entry_point, log_name):
    log_path = entry_point / log_name
    log, log_path_csv = read(log_path)
    result = resource_calendar.discover_per_resource(log)
    assert result
    log_path_csv.unlink()


def test_resource_pool_analyzer(entry_point):
    log_path = entry_point / 'PurchasingExample.xes'
    log, log_path_csv = read(log_path)
    result = ResourcePoolAnalyser(log, activity_key='concept:name', resource_key='org:resource')
    assert result.resource_table
    assert len(result.resource_table) > 0
    log_path_csv.unlink()


@pytest.mark.parametrize('log_name', ['DifferentiatedCalendars.xes'])
def test_calendar_case_arrival_discover(entry_point, log_name):
    log_path = entry_point / log_name
    log, log_path_csv = read(log_path)
    result = case_arrival.discover(log)
    assert result
    log_path_csv.unlink()

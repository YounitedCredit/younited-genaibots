import logging
from unittest.mock import MagicMock, patch

import pytest

from utils.logging.logger_loader import setup_logger_and_tracer


@pytest.fixture
def mock_config_manager():
    with patch('utils.logging.logger_loader.ConfigManager') as mock:
        yield mock

@pytest.fixture
def mock_rotating_file_handler():
    with patch('utils.logging.logger_loader.RotatingFileHandler') as mock:
        yield mock

@pytest.fixture
def mock_azure_monitor_log_exporter():
    with patch('utils.logging.logger_loader.AzureMonitorLogExporter') as mock:
        yield mock

@pytest.fixture
def mock_azure_monitor_trace_exporter():
    with patch('utils.logging.logger_loader.AzureMonitorTraceExporter') as mock:
        yield mock

@pytest.fixture
def mock_azure_monitor_metric_exporter():
    with patch('utils.logging.logger_loader.AzureMonitorMetricExporter') as mock:
        yield mock

@pytest.fixture
def mock_coloredlogs():
    with patch('utils.logging.logger_loader.coloredlogs') as mock:
        yield mock

def test_setup_logger_basic_config(mock_config_manager, mock_coloredlogs):
    mock_config_manager().get_config.side_effect = [
        'INFO',
        None,  # for log_plugin_file
        None,  # for log_plugin_azure
    ]

    logger, tracer = setup_logger_and_tracer(MagicMock())

    assert isinstance(logger, logging.Logger)
    assert tracer is None
    mock_coloredlogs.install.assert_called_once()

def test_setup_logger_file_config(mock_config_manager, mock_rotating_file_handler):
    mock_config_manager().get_config.side_effect = [
        'INFO',
        MagicMock(PLUGIN_NAME='file_system'),
        None,  # for log_plugin_azure
        '/path/to/log/file.log'
    ]

    logger, tracer = setup_logger_and_tracer(MagicMock())

    mock_rotating_file_handler.assert_called_once_with(
        '/path/to/log/file.log',
        maxBytes=10000000,
        backupCount=3
    )
    assert mock_rotating_file_handler().setFormatter.called
    assert any(isinstance(handler, MagicMock) for handler in logger.handlers)
    assert tracer is None

def test_setup_logger_azure_config(mock_config_manager, mock_azure_monitor_log_exporter,
                                   mock_azure_monitor_trace_exporter, mock_azure_monitor_metric_exporter):
    mock_config_manager().get_config.side_effect = [
        'INFO',
        None,  # for log_plugin_file
        MagicMock(PLUGIN_NAME='azure'),
        MagicMock(APPLICATIONINSIGHTS_CONNECTION_STRING='connection_string'),
    ]

    with patch('utils.logging.logger_loader.LoggerProvider') as mock_logger_provider, \
         patch('utils.logging.logger_loader.set_logger_provider') as mock_set_logger_provider, \
         patch('utils.logging.logger_loader.BatchLogRecordProcessor') as mock_batch_log_processor, \
         patch('utils.logging.logger_loader.LoggingHandler') as mock_logging_handler, \
         patch('utils.logging.logger_loader.TracerProvider') as mock_tracer_provider, \
         patch('utils.logging.logger_loader.trace.set_tracer_provider') as mock_set_tracer_provider, \
         patch('utils.logging.logger_loader.BatchSpanProcessor') as mock_batch_span_processor, \
         patch('utils.logging.logger_loader.PeriodicExportingMetricReader') as mock_metric_reader, \
         patch('utils.logging.logger_loader.MeterProvider') as mock_meter_provider, \
         patch('utils.logging.logger_loader.metrics.set_meter_provider') as mock_set_meter_provider, \
         patch('utils.logging.logger_loader.trace.get_tracer') as mock_get_tracer:

        logger, tracer = setup_logger_and_tracer(MagicMock())

        mock_azure_monitor_log_exporter.assert_called_once_with(connection_string='connection_string')
        mock_azure_monitor_trace_exporter.assert_called_once_with(connection_string='connection_string')
        mock_azure_monitor_metric_exporter.assert_called_once_with(connection_string='connection_string')

        assert mock_set_logger_provider.called
        assert mock_set_tracer_provider.called
        assert mock_set_meter_provider.called

        assert any(isinstance(handler, MagicMock) for handler in logger.handlers)
        assert tracer is not None

import logging
from unittest.mock import MagicMock, patch
import tempfile
import pytest
import os
from utils.logging.logger_loader import setup_logger_and_tracer
import time

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

def test_setup_logger_file_config(mock_config_manager, caplog):
    # Simulate the logger configuration actions
    mock_config_manager().get_config.side_effect = [
        'INFO',
        MagicMock(PLUGIN_NAME='file_system'),
        None,  # for log_plugin_azure
        '/path/to/log/file.log'
    ]

    # Use a temporary file with delete=False to avoid permission issues on Windows
    with tempfile.NamedTemporaryFile(delete=False) as temp_log_file:
        try:
            # Replace the list directly to use the temporary file path
            mock_config_manager().get_config.side_effect = [
                'INFO',
                MagicMock(PLUGIN_NAME='file_system'),
                None,  # for log_plugin_azure
                temp_log_file.name  # Temporary path for the log file
            ]

            # Mock the RotatingFileHandler
            with patch('logging.handlers.RotatingFileHandler') as mock_handler:
                handler_instance = logging.handlers.RotatingFileHandler(
                    temp_log_file.name, maxBytes=1000000, backupCount=5
                )
                mock_handler.return_value = handler_instance

                # Capture the logs with caplog
                with caplog.at_level(logging.INFO):
                    # Ensure the logger level is set to INFO
                    logger, tracer = setup_logger_and_tracer(MagicMock())
                    logger.setLevel(logging.INFO)

                    # Manually log to test if logging works
                    logger.info("File logging is set up")

                # Print to verify what is captured in caplog
                print(f"Captured logs: {caplog.text}")

                # Verify that the log message is in the captured logs
                assert "File logging is set up" in caplog.text

                # Verify that the handler was correctly called with the expected arguments
                mock_handler.assert_called_once_with(temp_log_file.name, maxBytes=1000000, backupCount=5)

                # Close the handler before deleting the temp file
                handler_instance.close()

                # Explicitly remove the file handler from the logger
                for handler in logger.handlers:
                    logger.removeHandler(handler)
                    handler.close()

                # Shutdown logging system to fully release the file
                logging.shutdown()

                # Wait a bit to ensure Windows releases the file
                time.sleep(1)  # Increase sleep time to 1 second for safety

        finally:
            # Ensure the temporary file is deleted after the test
            try:
                os.remove(temp_log_file.name)
            except PermissionError as e:
                print(f"Failed to delete temp file due to: {e}")

def test_setup_logger_azure_config(mock_config_manager, mock_azure_monitor_log_exporter,
                                   mock_azure_monitor_trace_exporter, mock_azure_monitor_metric_exporter):
    # Set up mock return values
    mock_azure_config = MagicMock()
    mock_azure_config.AZURE_LOGGING_APPLICATIONINSIGHTS_CONNECTION_STRING = 'connection_string'

    mock_config_manager().get_config.side_effect = [
        'INFO',
        None,  # for log_plugin_file
        MagicMock(PLUGIN_NAME='azure'),
        mock_azure_config  # Return a mock object with the required attribute
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

        # Call the setup_logger_and_tracer function
        logger, tracer = setup_logger_and_tracer(MagicMock())

        # Validate the calls to the mock Azure exporters
        mock_azure_monitor_log_exporter.assert_called_once_with(connection_string='connection_string')
        mock_azure_monitor_trace_exporter.assert_called_once_with(connection_string='connection_string')
        mock_azure_monitor_metric_exporter.assert_called_once_with(connection_string='connection_string')

        # Ensure other necessary mocks are used
        assert mock_set_logger_provider.called
        assert mock_set_tracer_provider.called
        assert mock_set_meter_provider.called

        # Verify that the logger was configured with handlers
        assert any(isinstance(handler, MagicMock) for handler in logger.handlers)
        assert tracer is not None
import logging
from logging.handlers import RotatingFileHandler

import coloredlogs
from azure.monitor.opentelemetry.exporter import (
    AzureMonitorLogExporter,
    AzureMonitorMetricExporter,
    AzureMonitorTraceExporter,
)

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from utils.config_manager.config_manager import ConfigManager


def setup_logger_and_tracer(global_manager):
    logger = logging.getLogger()
    tracer = None  # Initialiser tracer à None
    config_handler = ConfigManager(global_manager)
    debug_level = config_handler.get_config(['BOT_CONFIG', 'LOG_DEBUG_LEVEL']).upper()  # Convertir en majuscule

    # Define log levels
    log_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    # Vérifier si le niveau de log est valide
    if debug_level not in log_levels:
        logger.warning(f"Log level '{debug_level}' not recognized, using 'INFO' level.")
        log_level = logging.INFO
    else:
        log_level = log_levels[debug_level]

    # Define styles for different logging levels
    level_styles = {
        'debug': {'color': 'blue'},
        'info': {'color': 'white'},
        'warning': {'color': 'yellow'},
        'error': {'color': 'red'},
        'critical': {'color': 'red', 'bold': True},
    }

    logging.getLogger("http.client").setLevel(logging.WARNING)
    
    # Install coloredlogs
    coloredlogs.install(
        level=log_level,
        fmt='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        level_styles=level_styles
    )

    # Setup file or Azure handler
    file_log_format = '%(asctime)s [%(levelname)s] %(message)s'
    file_formatter = logging.Formatter(file_log_format, datefmt='%H:%M:%S')

    log_plugin_file = config_handler.get_config(['UTILS', 'LOGGING', 'LOCAL_LOGGING'])
    log_plugin_azure = config_handler.get_config(['UTILS', 'LOGGING', 'AZURE_LOGGING'])

    if log_plugin_file is None and log_plugin_azure is None:
        logger.warning("No Logging confured in UTILS/LOGGING, no logs will be recorded")

    if log_plugin_file and log_plugin_file.PLUGIN_NAME == 'local_logging':
        # File handler setup
        file_handler = RotatingFileHandler(
            config_handler.get_config(['UTILS', 'LOGGING', 'LOCAL_LOGGING', 'LOCAL_LOGGING_FILE_PATH']),
            maxBytes=10000000,
            backupCount=3
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.debug("File logging is set up")

    elif log_plugin_azure and log_plugin_azure.PLUGIN_NAME == 'azure':
        logging.getLogger('azure').setLevel(logging.WARNING)
        # Azure handler setup for logging
        azure_config = config_handler.get_config(['UTILS', 'LOGGING', 'AZURE_LOGGING'])
        connection_string = azure_config.AZURE_LOGGING_APPLICATIONINSIGHTS_CONNECTION_STRING

        # Set up Azure Monitor Log Exporter
        logger_provider = LoggerProvider()
        set_logger_provider(logger_provider)
        azure_log_exporter = AzureMonitorLogExporter(connection_string=connection_string)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(azure_log_exporter))
        handler = LoggingHandler()
        logger.addHandler(handler)

        # OpenTelemetry Tracer setup
        tracer_provider = TracerProvider()
        trace.set_tracer_provider(tracer_provider)
        tracer_exporter = AzureMonitorTraceExporter(connection_string=connection_string)
        span_processor = BatchSpanProcessor(tracer_exporter)
        tracer_provider.add_span_processor(span_processor)
        tracer = trace.get_tracer(__name__)

        # Set up MeterProvider with MetricReader
        metric_exporter = AzureMonitorMetricExporter(connection_string=connection_string)
        metric_reader = PeriodicExportingMetricReader(exporter=metric_exporter, export_interval_millis=60000)
        meter_provider = MeterProvider(metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

        # Get a meter
        meter = metrics.get_meter(__name__, version="0.1")

        logging.getLogger("opentelemetry").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger, tracer

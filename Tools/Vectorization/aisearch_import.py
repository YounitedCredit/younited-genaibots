import json
import argparse
import logging
import colorama
from colorama import Fore, Style
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex
from azure.search.documents.models import IndexAction
from azure.search.documents._index_documents_batch import IndexDocumentsBatch

"""
Vector Import Script

This script imports an index definition and data into Azure AI Search.
It includes enhanced logging with color output and improved error handling.

Usage:
python aisearch_import.py --service-endpoint <endpoint> --admin-key <key> 
                        --index-definition <path> --data <path>

Arguments:
--service-endpoint : Azure AI Search service endpoint (required)
--admin-key        : Azure AI Search admin key (required)
--index-definition : Path to index definition JSON file (required)
--data             : Path to data JSON file (required)

Example:
python aisearch_import.py --service-endpoint https://your-service.search.windows.net 
                        --admin-key your-admin-key 
                        --index-definition /path/to/index_definition.json 
                        --data /path/to/data.json

Note: 
Ensure you have set up the necessary Azure AI Search resources before running this script.
"""

colorama.init(autoreset=True)

# Configure logging with custom formatter for colored output
class ColoredFormatter(logging.Formatter):
    format_str = '%(asctime)s - %(levelname)s - %(message)s'

    FORMATS = {
        logging.DEBUG: Style.DIM + format_str + Style.RESET_ALL,
        logging.INFO: format_str,
        logging.WARNING: Fore.YELLOW + format_str + Style.RESET_ALL,
        logging.ERROR: Fore.RED + format_str + Style.RESET_ALL,
        logging.CRITICAL: Fore.RED + Style.BRIGHT + format_str + Style.RESET_ALL
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# File handler (no color)
file_handler = logging.FileHandler('vector_import.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Stream handler (with color)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(ColoredFormatter())
logger.addHandler(stream_handler)

def validate_document(document, non_nullable_fields):
    """Ensure that the document does not contain null values for non-nullable fields."""
    for field in non_nullable_fields:
        if field in document and document[field] is None:
            logger.error(f"Document has null value for non-nullable field: {field}")
            return False
    return True

def load_index_definition(file_path):
    logger.info(f"Loading index definition from {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Error loading index definition: {str(e)}")
        raise

def create_index_if_not_exists(index_client, index_definition):
    index_name = index_definition['name']
    logger.info(f"Checking if index {index_name} exists")
    try:
        if index_name not in index_client.list_index_names():
            logger.info(f"Creating index: {index_name}")
            index = SearchIndex.from_dict(index_definition)
            index_client.create_index(index)
            logger.info(f"Index {index_name} created successfully")
        else:
            logger.info(f"Index {index_name} already exists")
        return index_name
    except Exception as e:
        logger.error(f"Error creating index: {str(e)}")
        raise

def import_data(search_client, json_data_path, non_nullable_fields):
    logger.info(f"Importing data from {json_data_path}")
    try:
        with open(json_data_path, 'r', encoding='utf-8') as json_file:
            documents = json.load(json_file)

        total_documents = len(documents['value'])
        valid_documents = []

        for i, document in enumerate(documents['value'], 1):
            if validate_document(document, non_nullable_fields):
                valid_documents.append(document)
            else:
                logger.error(f"Skipping document {i}/{total_documents} due to null values")

            if len(valid_documents) % 100 == 0 or i == total_documents:
                logger.info(f"Uploading batch of {len(valid_documents)} documents...")
                result = search_client.upload_documents(documents=valid_documents)
                logger.info(f"Batch upload succeeded: {result}")
                valid_documents = []  # Reset the list after each upload

        logger.info(f"Processed {i}/{total_documents} documents successfully")

    except Exception as e:
        logger.error(f"Error importing data: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Import index and data to Azure AI Search")
    parser.add_argument("--service-endpoint", required=True, help="Azure AI Search service endpoint")
    parser.add_argument("--admin-key", required=True, help="Azure AI Search admin key")
    parser.add_argument("--index-definition", required=True, help="Path to index definition JSON file")
    parser.add_argument("--data", required=True, help="Path to data JSON file")
    
    args = parser.parse_args()

    logger.info(f"{Fore.CYAN}Starting import process{Style.RESET_ALL}")
    try:
        # Create clients
        credential = AzureKeyCredential(args.admin_key)
        index_client = SearchIndexClient(endpoint=args.service_endpoint, credential=credential)
        logger.info("Successfully created SearchIndexClient")

        # Load and create index
        index_definition = load_index_definition(args.index_definition)
        index_name = create_index_if_not_exists(index_client, index_definition)

        # Define non-nullable fields from your index definition
        non_nullable_fields = ['id', 'content', 'filepath', 'title', 'chunk', 'vector']

        # Create search client and import data
        search_client = SearchClient(endpoint=args.service_endpoint, index_name=index_name, credential=credential)
        logger.info("Successfully created SearchClient")
        import_data(search_client, args.data, non_nullable_fields)

        logger.info(f"{Fore.GREEN}Import process completed successfully{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{Fore.RED}An error occurred during the import process: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
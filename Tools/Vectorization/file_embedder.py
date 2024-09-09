import os
import re
import pandas as pd
import logging
from openai import AzureOpenAI
import tiktoken
import urllib.parse
import json
import argparse
import colorama
from colorama import Fore, Style
import urllib.parse

help_description = """
File Embedder Script with Dynamic Chunking

This script processes documents (files or directories) to create embeddings using Azure OpenAI.
It handles segmentation of documents dynamically by either a fixed token count or based on document structure (paragraphs/headings).
It also provides the option to overlap chunks for better contextual continuity.

Usage:
  python file_embedder.py --input <input_path> --output <output_path> --output_format <csv|json>
                          --openai_key <api_key> --openai_endpoint <endpoint_url>
                          [--max_tokens <number>] [--index_name <name>]
                          [--openai_api_version <version>] [--dynamic_chunking] [--overlap_tokens <number>]
                          [--source_type <filesystem|azure_devops_wiki>] [--wiki_url <url>]

Arguments:
  --input              : Path to input file or directory (required).
                         This can be a single document or a directory containing multiple documents.
  --output             : Path to the output file without extension (required).
                         The script will generate either a CSV or JSON file based on the format you choose.
  --output_format      : Output format, either 'csv' or 'json' (default: csv).
                         Specifies the format for the embedding results. If not provided, the default is CSV.
  --openai_key         : Azure OpenAI API key (required).
                         Your API key to authenticate with Azure OpenAI services.
  --openai_endpoint    : Azure OpenAI endpoint URL (required).
                         The endpoint URL provided by Azure for your OpenAI instance.
  --max_tokens         : Maximum number of tokens per segment (optional).
                         If not provided, the entire document is processed in a single pass. Use this to limit the number of tokens in each chunk.
  --index_name         : Name for the Azure Cognitive Search index (optional).
                         If provided, an index definition will be generated based on the document embeddings.
  --openai_api_version : Azure OpenAI API version (optional, default: 2023-06-01-preview).
                         The API version to be used for the OpenAI services.
  --dynamic_chunking   : Enable chunking based on document structure such as paragraphs or headings (optional, default: False).
                         Allows dynamic chunking based on the structure of the document instead of a fixed token limit.
  --overlap_tokens     : Number of tokens to overlap between chunks (optional, default: 50).
                         This helps maintain continuity between chunks by repeating a certain number of tokens from the previous chunk.
  --model_name         : OpenAI model name to be used for generating embeddings (optional, default: 'text-embedding-3-large').
                         Specifies the OpenAI model to use for generating embeddings. You can provide a custom model if needed.
  --source_type        : Specify the source type for the file path (optional, default: 'filesystem').
                         'filesystem' (default): The file path is stored as the full local path.
                         'azure_devops_wiki': Converts the file path to an Azure DevOps Wiki URL.
  --wiki_url           : The base URL of your Azure DevOps Wiki.
                         This is required if you select 'azure_devops_wiki' as the source type.
                         Example: https://your-domain.visualstudio.com/your-project/_wiki/wikis/your-project.wiki

Examples:
1. Basic usage - Process a single file and output as CSV:
   python file_embedder.py --input /path/to/document.txt --output /path/to/output --openai_key YOUR_API_KEY --openai_endpoint YOUR_ENDPOINT

2. Process a directory and output as JSON:
   python file_embedder.py --input /path/to/docs --output /path/to/output --output_format json --openai_key YOUR_API_KEY --openai_endpoint YOUR_ENDPOINT

3. Process a file with a custom token limit and specific API version:
   python file_embedder.py --input /path/to/document.txt --output /path/to/output --max_tokens 500 --openai_key YOUR_API_KEY --openai_endpoint YOUR_ENDPOINT --openai_api_version 2023-05-15

4. Use dynamic chunking based on document structure with overlap tokens:
   python file_embedder.py --input /path/to/docs --output /path/to/output --output_format json --dynamic_chunking --overlap_tokens 100 --openai_key YOUR_API_KEY --openai_endpoint YOUR_ENDPOINT

5. Process a directory and generate an Azure Cognitive Search index definition:
   python file_embedder.py --input /path/to/docs --output /path/to/output --index_name my_search_index --openai_key YOUR_API_KEY --openai_endpoint YOUR_ENDPOINT

6. Use a custom model for embedding generation:
   python file_embedder.py --input /path/to/document.txt --output /path/to/output --model_name "your-custom-model" --openai_key YOUR_API_KEY --openai_endpoint YOUR_ENDPOINT

7. Process a directory from an Azure DevOps Wiki:
   python file_embedder.py --input /path/to/docs --output /path/to/output --source_type azure_devops_wiki --wiki_url https://your-domain.visualstudio.com/your-project/_wiki/wikis/your-project.wiki --openai_key YOUR_API_KEY --openai_endpoint YOUR_ENDPOINT

8. Process with a mix of all options - token limit, dynamic chunking, overlap, and custom model:
   python file_embedder.py --input /path/to/docs --output /path/to/output --max_tokens 800 --dynamic_chunking --overlap_tokens 75 --model_name "your-custom-model" --openai_key YOUR_API_KEY --openai_endpoint YOUR_ENDPOINT --index_name my_search_index

9. Process a directory, limit tokens, use custom model and specific API version, output to JSON:
   python file_embedder.py --input /path/to/docs --output /path/to/output --output_format json --max_tokens 300 --model_name "text-embedding-2" --openai_api_version 2023-01-15 --openai_key YOUR_API_KEY --openai_endpoint YOUR_ENDPOINT
"""

colorama.init(autoreset=True)
tokenizer = tiktoken.get_encoding('cl100k_base')

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
file_handler = logging.FileHandler('embedding_process.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Stream handler (with color)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(ColoredFormatter())
logger.addHandler(stream_handler)

def get_file_path(local_path, source_type, wiki_url, input_dir):
    if source_type == 'filesystem':
        # Replace backslashes with forward slashes for filesystem paths
        file_path = local_path.replace('\\', '/')
        return file_path
    elif source_type == 'azure_devops_wiki':
        # For Azure DevOps, generate the Wiki URL
        return create_wiki_url(wiki_url, local_path, input_dir)
    else:
        raise ValueError(f"Invalid source_type: {source_type}")
    
def create_wiki_url(wiki_base_url, local_file_path, input_dir, subfolder=''):
    """Creates the correct URL for an Azure DevOps Wiki page from a local file path.

    Args:
        wiki_base_url (str): The base URL of your Azure DevOps Wiki.
        local_file_path (str): The full path to the local Markdown file.
        input_dir (str): The root directory where the Markdown files are located.
        subfolder (str, optional): The relative path of the subfolder inside the wiki repository. 
                                   Defaults to ''. 

    Returns:
        str: The Azure DevOps Wiki URL for the given file.
    """

    logging.info(f"Local file path received: {local_file_path}")

    # Get the relative path from the input directory
    relative_path = os.path.relpath(local_file_path, input_dir)
    logging.info(f"Relative path before processing: {relative_path}")

    # Replace backslashes with forward slashes for Windows paths
    relative_path = relative_path.replace('\\', '/')
    logging.info(f"Relative path after backslash replacement: {relative_path}")

    # Remove the .md extension if present
    if relative_path.lower().endswith('.md'):
        relative_path = os.path.splitext(relative_path)[0]
    logging.info(f"Relative path after removing .md: {relative_path}")

    # 1. Replace hyphens used as spaces with %20
    relative_path = relative_path.replace('-', '%20')
    logging.info(f"Path after handling hyphens for spaces: {relative_path}")

    # 2.  Replace %2D with %252D (this was the missing piece!)
    relative_path = relative_path.replace('%2D', '%252D')
    logging.info(f"Path after handling encoded hyphens: {relative_path}")

    # 3. Encode the path, preserving already encoded characters and spaces
    final_path = urllib.parse.quote(relative_path, safe='%20/')
    logging.info(f"Final encoded path: {final_path}")

    # Add the subfolder to the final path
    if subfolder:
        final_path = f"{subfolder}/{final_path}"
    logging.info(f"Final path with subfolder: {final_path}")

    # Construct the final URL
    final_url = f"{wiki_base_url}?wikiVersion=GBwikiMaster&pagePath=/{final_path}"
    logging.info(f"Final generated URL: {final_url}")

    return final_url

def clean_text(text):
    """Clean markdown and HTML from the text."""
    try:
        # Remove title markers, keep title text
        text = re.sub(r'^\s*#+\s', '', text, flags=re.MULTILINE)
        
        # Remove images
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        
        # Keep only URLs from links
        text = re.sub(r'\[.*?\]\((.*?)\)', r'\1', text)
        
        # Remove bold and italic markers
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        
        # Remove list markers
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        
        # Remove block code entirely
        text = re.sub(r'`{3}.*?`{3}', '', text, flags=re.DOTALL)
        
        # Remove inline code markers, keep code text
        text = re.sub(r'`(.*?)`', r'\1', text)

        # Remove extra newlines and clean lines
        content_lines = [line.strip() for line in text.splitlines() if line.strip()]
        
        # Join the cleaned lines with visible line breaks for better readability
        return '\n'.join(content_lines)
    except Exception as e:
        logging.error(f"Error cleaning text: {e}")
        return ""

def clean_title(title):
    # Decode the title first to handle any URL encoded characters
    title = urllib.parse.unquote(title)
    
    # Replace hyphens and underscores with spaces
    title = title.replace('-', ' ').replace('_', ' ')
    
    # Remove any remaining URL-unsafe characters
    title = re.sub(r'[^\w\s-]', '', title)
    
    # Remove extra whitespace
    title = ' '.join(title.split())
    
    return title

def split_document_by_structure(text, max_tokens, overlap_tokens=50):
    """Split a document into passages by structure with optional overlap."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_chunk_tokens = 0

    for paragraph in paragraphs:
        paragraph_tokens = len(tokenizer.encode(paragraph))
        
        if current_chunk_tokens + paragraph_tokens > max_tokens:
            chunks.append(" ".join(current_chunk))
            overlap = current_chunk[-overlap_tokens:]
            current_chunk = overlap + [paragraph]
            current_chunk_tokens = sum(len(tokenizer.encode(p)) for p in current_chunk)
        else:
            current_chunk.append(paragraph)
            current_chunk_tokens += paragraph_tokens
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

def split_document_into_passages(document, max_tokens=None):
    """Split a document into passages based on token length."""
    try:
        tokens = tokenizer.encode(document)
        if max_tokens is None or len(tokens) <= max_tokens:
            return [document]  # Return the entire document as a single passage
        
        passages = []
        for i in range(0, len(tokens), max_tokens):
            passage_tokens = tokens[i:i + max_tokens]
            passage = tokenizer.decode(passage_tokens)
            passages.append(passage)
            logging.info(f"Processing passage {len(passages)} of {len(tokens) // max_tokens + 1}")
        return passages
    except Exception as e:
        logging.error(f"Error splitting document into passages: {e}")
        return []

def get_text_embedding(text, openai_client, model=None):
    """Get the embedding for a given text using the specified model."""
    if text.strip() == '':
        logging.warning("Empty text encountered, returning empty embedding.")
        return []
    
    model_name = model if model else "text-embedding-3-large"  # Default model
    try:
        response = openai_client.embeddings.create(input=[text], model=model_name)
        embedding = response.data[0].embedding
        return embedding
    except Exception as e:
        logging.error(f"Error getting text embedding: {e}")
        return []

def convert_to_azure_search_json(df, key_name='id'):
    """Convert DataFrame to Azure Cognitive Search JSON format."""
    documents = []
    for _, row in df.iterrows():
        # Sanitize the document_id and passage_id before using them
        sanitized_id = sanitize_document_id(f"{row['document_id']}_{row['passage_id']}")
        doc = {
            key_name: sanitized_id,  # Unique ID for the passage
            "content": row['text'],  # Full content of the passage
            "file_path": row['file_path'],  # Original file path
            "title": row['title'],  # Title of the document
            "chunk": int(row['passage_index']),  # The passage chunk index
            "passage_id": int(row['passage_id']),  # Adding passage_id explicitly
            "vector": row['embedding'],  # The vector embedding
            "title_vector": row['title_embedding']  # The title vector embedding
        }
        documents.append(doc)

    return {"value": documents}


def sanitize_document_id(doc_id):
    """Sanitize the document ID by removing invalid characters and avoiding leading underscores."""
    # Replace any invalid characters with an underscore
    sanitized_id = re.sub(r'[^a-zA-Z0-9_\-=]', '_', doc_id)
    
    # Remove any leading underscores
    return sanitized_id.lstrip('_')

def generate_index_definition(index_name, vector_dimension):
    """Generate the index definition for Azure Cognitive Search."""
    return {
        "name": index_name,
        "fields": [
            {
                "name": "id",
                "type": "Edm.String",
                "searchable": False,
                "filterable": True,
                "retrievable": True,  # ID should be retrievable as a key
                "sortable": False,
                "facetable": False,
                "key": True
            },
            {
                "name": "document_id",  # New field to store the original document ID
                "type": "Edm.String",
                "searchable": False,
                "filterable": True,
                "retrievable": True,  # Make the document ID retrievable
                "sortable": False,
                "facetable": False
            },
            {
                "name": "passage_id",  # New field to store the passage ID
                "type": "Edm.Int32",
                "searchable": False,
                "filterable": True,
                "retrievable": True,  # Make passage ID retrievable
                "sortable": False,
                "facetable": False
            },
            {
                "name": "content",
                "type": "Edm.String",
                "searchable": True,  # Allow search in content
                "filterable": False,
                "retrievable": True,  # Make the content field retrievable
                "sortable": False,
                "facetable": False,
                "analyzer": "standard.lucene"
            },
            {
                "name": "file_path",
                "type": "Edm.String",
                "searchable": False,
                "filterable": True,
                "retrievable": True,  # Make the file_path field retrievable
                "sortable": False,
                "facetable": False
            },
            {
                "name": "title",
                "type": "Edm.String",
                "searchable": True,  # Allow search by title
                "filterable": True,  # Filter by title if needed
                "retrievable": True,  # Make title retrievable
                "sortable": False,
                "facetable": False,
                "analyzer": "standard.lucene"
            },
            {
                "name": "chunk",
                "type": "Edm.Int32",
                "searchable": False,
                "filterable": True,  # Filter by chunk if needed
                "retrievable": True,  # Make chunk field retrievable
                "sortable": False,
                "facetable": False
            },
            {
                "name": "vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,  # Vector search requires this field to be searchable
                "filterable": False,
                "retrievable": False,  # Do not make the vector retrievable
                "sortable": False,
                "facetable": False,
                "dimensions": vector_dimension,
                "vectorSearchProfile": "vector-profile-1725439458160"
            },
            {
                "name": "title_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,  # Allow vector search with title embeddings
                "filterable": False,
                "retrievable": False,  # Do not make title_vector retrievable
                "sortable": False,
                "facetable": False,
                "dimensions": vector_dimension,
                "vectorSearchProfile": "vector-profile-1725439458160"
            }
        ],
        "vectorSearch": {
            "algorithms": [
                {
                    "name": "vector-config-1725439474337",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "metric": "cosine",
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500
                    }
                }
            ],
            "profiles": [
                {
                    "name": "vector-profile-1725439458160",
                    "algorithm": "vector-config-1725439474337"
                }
            ]
        },
        "similarity": {
            "@odata.type": "#Microsoft.Azure.Search.BM25Similarity"
        }
    }

def get_file_path_and_url(local_path, source_type, wiki_url, input_dir, subfolder=''):
    """Return both the local file path and the corresponding Azure DevOps Wiki URL if applicable."""
    file_path = local_path.replace('\\', '/')
    if source_type == 'azure_devops_wiki':
        wiki_url = create_wiki_url(wiki_url, local_path, input_dir, subfolder)
        return file_path, wiki_url
    return file_path, file_path

def convert_to_wiki_url(local_path, wiki_url, input_dir):
    """Convert a local file path to an Azure DevOps Wiki URL."""
    relative_path = os.path.relpath(local_path, input_dir).replace('\\', '/')
    if relative_path.lower().endswith('.md'):
        relative_path = os.path.splitext(relative_path)[0]
    final_path = urllib.parse.quote(relative_path, safe='%20()/')
    return f"{wiki_url}?wikiVersion=GBwikiMaster&pagePath=/{final_path}"

# Main execution
def main(args):
    file_paths = []
    file_urls = []

    # Create an OpenAI object specifying the endpoint
    try:
        openai_client = AzureOpenAI(
            api_key=args.openai_key,
            azure_endpoint=args.openai_endpoint,
            api_version=args.openai_api_version
        )
    except Exception as e:
        logging.error(f"Failed to create OpenAI client: {e}")
        raise

    # Load encoding locally
    try:
        tokenizer = tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        logging.error(f"Failed to load tokenizer: {e}")
        raise

    # Main processing logic to determine file paths and process files
    if os.path.isdir(args.input):
        for root, dirs, files in os.walk(args.input):
            for file in files:
                local_file_path = os.path.join(root, file)
                file_path, file_url = get_file_path_and_url(local_file_path, args.source_type, args.wiki_url, args.input, args.wiki_subfolder)
                file_paths.append(file_path)
                file_urls.append(file_url)
    else:
        local_file_path = args.input
        file_path, file_url = get_file_path_and_url(local_file_path, args.source_type, args.wiki_url, args.input, args.wiki_subfolder)
        file_paths.append(file_path)
        file_urls.append(file_url)

    # Initialize lists to store data
    document_ids, passage_ids, embeddings, texts, titles, title_embeddings, passage_indices = [], [], [], [], [], [], []

    # Process files
    for file_count, (local_file_path, file_url) in enumerate(zip(file_paths, file_urls), 1):
        logging.info(f"Processing file {file_count}/{len(file_paths)}: {file_url}")
        
        try:
            with open(local_file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            logging.error(f"Failed to read file {local_file_path}: {e}")
            continue
        
        cleaned_text = clean_text(text)
        if not cleaned_text:
            logging.warning(f"Cleaned text from file {local_file_path} is empty, ignored.")
            continue
        
        try:
            num_tokens = len(tokenizer.encode(cleaned_text))
            logging.info(f"File {local_file_path} contains {num_tokens} tokens after cleaning")
        except Exception as e:
            logging.error(f"Failed to calculate tokens for file {local_file_path}: {e}")
            continue
        
        if args.dynamic_chunking:
            document_passages = split_document_by_structure(cleaned_text, args.max_tokens, args.overlap_tokens)
        else:
            document_passages = split_document_into_passages(cleaned_text, args.max_tokens)

        if not document_passages:
            logging.warning(f"No valid passages found for file {local_file_path}, ignored.")
            continue
        
        title = os.path.splitext(os.path.basename(local_file_path))[0]
        title = clean_title(title)
        if not title.strip():
            title = os.path.splitext(os.path.basename(local_file_path))[0]

        logging.info(f"Cleaned title: {title}")
        title_embedding = get_text_embedding(title, openai_client, model=args.model_name)
        if not title_embedding:
            logging.warning(f"Failed to get embedding for title: {title}")
        
        logging.info(f"Title: {title}")
        
        # Process passages and store embeddings
        for passage_index, passage in enumerate(document_passages, 1):
            embedding = get_text_embedding(passage, openai_client, model=args.model_name)
            if embedding:
                document_ids.append(title)
                passage_ids.append(passage_index)
                embeddings.append(embedding)
                texts.append(passage)
                titles.append(title)
                title_embeddings.append(title_embedding)
                passage_indices.append(passage_index)
                logging.info(f"    Passage {passage_index}/{len(document_passages)} processed")

    # Ensure all lists have the same length
    min_length = min(len(document_ids), len(passage_ids), len(file_paths), len(passage_indices),
                     len(texts), len(titles), len(title_embeddings), len(embeddings))

    # Truncate all lists to the same length
    document_ids = document_ids[:min_length]
    passage_ids = passage_ids[:min_length]
    file_paths = file_paths[:min_length]
    passage_indices = passage_indices[:min_length]
    texts = texts[:min_length]
    titles = titles[:min_length]
    title_embeddings = title_embeddings[:min_length]
    embeddings = embeddings[:min_length]

    # Create DataFrame
    try:
        df = pd.DataFrame({
            'document_id': document_ids,
            'passage_id': passage_ids,
            'file_path': file_urls if args.source_type == 'azure_devops_wiki' else file_paths,
            'passage_index': passage_indices,
            'text': texts,
            'title': titles,
            'title_embedding': title_embeddings,
            'embedding': embeddings
        })
    except Exception as e:
        logging.error(f"Failed to create DataFrame: {e}")
        raise

    # Generate index definition if index_name is provided
    index_file = None
    if args.index_name:
        vector_dimension = len(embeddings[0]) if embeddings else 1536
        index_definition = generate_index_definition(args.index_name, vector_dimension)
        index_file = f"{args.output}_index_definition.json"
        with open(index_file, 'w') as f:
            json.dump(index_definition, f, indent=2)
        logging.info(f"\n{'='*50}")
        logging.info(f"INDEX DEFINITION GENERATED")
        logging.info(f"File: {index_file}")
        logging.info(f"{'='*50}\n")
        logging.info(f"Index definition has been written to {index_file}")
    else:
        logging.warning("\nNOTE: No index name provided. Index definition was not generated.")

    # Save the DataFrame based on the chosen output format
    output_file = f"{args.output}.{args.output_format}"
    if args.output_format == 'csv':
        try:
            df.to_csv(output_file, index=False)
            logging.info(f"Embeddings have been successfully written to {output_file}.")
        except Exception as e:
            logging.error(f"Failed to save DataFrame to CSV: {e}")
            raise
    else:  # JSON format
        try:
            json_data = convert_to_azure_search_json(df)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            logging.info(f"Embeddings have been successfully written to {output_file} in Azure Cognitive Search format.")
        except Exception as e:
            logging.error(f"Failed to save data to JSON: {e}")
            raise

    logging.info("\nScript execution completed.")
    logging.info(f"Output file: {output_file}")
    if args.index_name:
        logging.info(f"Index definition file: {index_file}")
    else:
        logging.info("No index definition file was generated.")

    return df, output_file, index_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=help_description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--input', required=True, help='Path to input file or directory')
    parser.add_argument('--output', required=True, help='Path to output file (without extension)')
    parser.add_argument('--output_format', choices=['csv', 'json'], default='json', help='Output format (csv or json)')
    parser.add_argument('--max_tokens', type=int, default=None, help='Maximum number of tokens per segment. If not set, entire documents will be vectorized.')
    parser.add_argument('--index_name', help='Name for the Azure Cognitive Search index. If provided, an index definition will be generated.')
    parser.add_argument('--openai_key', required=True, help='Azure OpenAI API key')
    parser.add_argument('--openai_endpoint', required=True, help='Azure OpenAI endpoint')
    parser.add_argument('--openai_api_version', default="2023-06-01-preview", help='Azure OpenAI API version')
    parser.add_argument('--dynamic_chunking', action='store_true', help='Enable chunking based on document structure such as paragraphs or headings')
    parser.add_argument('--overlap_tokens', type=int, default=50, help='Number of tokens to overlap between chunks')
    parser.add_argument('--model_name', default="text-embedding-3-large", help="OpenAI model name to be used for generating embeddings. Default is 'text-embedding-3-large'")
    parser.add_argument('--source_type', choices=['filesystem', 'azure_devops_wiki'], default='filesystem', 
                        help="Source type: 'filesystem' (default) or 'azure_devops_wiki'. Specifies how the file path is treated.")
    parser.add_argument('--wiki_subfolder', default='', help="Relative path of the subfolder inside the wiki repository. Used to adjust file paths in Azure DevOps Wiki URLs.")
    parser.add_argument('--wiki_url', help="Base URL of the Azure DevOps Wiki. Required if 'azure_devops_wiki' is selected as source_type.")
    args = parser.parse_args()

    if args.source_type == 'azure_devops_wiki' and not args.wiki_url:
        parser.error("You must provide --wiki_url when using 'azure_devops_wiki' as source_type")

    main(args)
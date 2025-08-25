# STAJ22001
Things i have done in my internship.

# URL Content Extractor

A Python application that extracts content from URLs, detects duplicates using multiple similarity algorithms, and categorizes content using LLM (Large Language Model) classification.

## Features

- **Content Extraction**: Extract clean text content from web URLs using Goose3
- **Duplicate Detection**: Advanced duplicate detection using three methods:
  - MinHash with LSH (Locality Sensitive Hashing)
  - SimHash for near-duplicate detection
  - Sentence embeddings with cosine similarity
- **LLM Classification**: Automatic categorization and summarization of extracted content
- **GUI Interface**: User-friendly interface built with ttkbootstrap
- **Batch Processing**: Process multiple URLs with progress tracking
- **Statistics**: Comprehensive similarity analysis and duplicate statistics

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/url-content-extractor.git
cd url-content-extractor
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

### Required Dependencies

- `goose3` - Web content extraction
- `datasketch` - MinHash and LSH implementation
- `simhash` - SimHash algorithm for duplicate detection
- `sentence-transformers` - Embedding model for semantic similarity
- `scikit-learn` - Machine learning utilities
- `numpy` - Numerical computing
- `ttkbootstrap` - Modern GUI framework
- `logging` - Built-in Python logging

## Usage

### Running the Application

Start the GUI application:
```bash
python main.py
```

### Input Format

#### URLs File
Create a text file with URLs, **one URL per line**:
```
https://example.com/article1
https://example.com/article2
https://example.com/article3
```

**Important**: Make sure your URL file contains one URL per line with no extra formatting.

#### Categories File (Optional)
You can upload your own categories as a CSV file. The application will use your custom categories for content classification.

**Note**: The categories file has been removed from the repository. Please provide your own categories CSV file if you want custom categorization.

### Configuration

The similarity thresholds can be adjusted in `similarity_checker.py`:

- `threshold_minhash`: MinHash similarity threshold (default: 0.35)
- `threshold_simhash`: SimHash distance threshold (default: 16)
- `threshold_embedding`: Embedding similarity threshold (default: 0.8)

## How It Works

### 1. Content Extraction
The application uses Goose3 to extract clean text content from web pages, removing HTML tags and extracting the main article content.

### 2. Duplicate Detection
Three algorithms work together to detect duplicates:

- **MinHash**: Creates compact signatures for text similarity detection
- **SimHash**: Detects near-duplicate content with configurable distance thresholds  
- **Embeddings**: Uses sentence transformers for semantic similarity detection

### 3. LLM Classification
Non-duplicate content is processed through an LLM classifier that:
- Categorizes content into predefined categories
- Generates summaries of the extracted content
- Caches results to avoid reprocessing duplicates

### 4. Results
The application provides:
- Extracted title and content
- Duplicate status with similarity scores
- Content category and summary
- Comprehensive statistics

## File Structure

```
├── main.py                 # Application entry point
├── extractor.py           # Main URL extraction logic
├── similarity_checker.py  # Duplicate detection algorithms
├── llm_classifier.py      # LLM-based classification 
├── gui/
│   └── main_window.py     # GUI implementation
    └──preview_window.py   # Preview Before Saving 
└── README.md
```

## Output Format

For each processed URL, the application returns:

```python
{
    'url': 'https://example.com',
    'title': 'Article Title',
    'content': 'Extracted clean text...',
    'status': 'success',
    'child_category': 'Technology',
    'summary': 'Brief summary of content...',
    'is_duplicate': False,
    'similarity_scores': {
        'minhash_max_similarity': 0.12,
        'simhash_min_distance': 45,
        'embedding_max_similarity': 0.23
    }
}
```

## Performance Notes

- **Embedding Model**: Uses 'all-MiniLM-L6-v2' by default for fast inference
- **Batch Processing**: Includes configurable delays between requests
- **Memory Efficient**: Stores compact signatures rather than full text
- **Caching**: LLM results are cached to avoid reprocessing duplicates

## Troubleshooting

### Common Issues

1. **Timeout Errors**: Increase the timeout value in the URLExtractor configuration
2. **Memory Usage**: For large datasets, consider processing in smaller batches
3. **Model Loading**: Ensure you have sufficient disk space for the embedding model download

### Error Types

The application handles various error types:
- Connection errors
- Timeout errors  
- HTTP status errors (404, 403, 500, etc.)
- Invalid URL format errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Acknowledgments

- Goose3 for web content extraction
- DataSketch for MinHash implementation
- Sentence Transformers for embedding models
- ttkbootstrap for the modern GUI framework

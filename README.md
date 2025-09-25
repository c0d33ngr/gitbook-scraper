# Gitbook Scraper

This repository contains a Python script for scraping documentation from Gitbook and saving the extracted content as Markdown files.

## Usage
1. Clone this repository:
   ```bash
   git clone https://github.com/c0d33ngr/gitbook-scraper.git
   cd gitbook-scraper
   ```
2. Install dependencies:
   ```bash
   pip install requests beautifulsoup4 html2text
   ```
3. Run the scraper script:
   ```bash
   python gitbook-scraper.py
   ```
4. Extracted documentation will be available in the `extracted_docs/` folder.

## Requirements
- Python 3.x
- requests
- beautifulsoup4
- html2text

## Folder Structure
- `gitbook-scraper.py`: Main script for scraping Gitbook documentation
- `extracted_docs/`: Contains extracted Markdown files

## Contributing
Feel free to open issues or submit pull requests for improvements or bug fixes.

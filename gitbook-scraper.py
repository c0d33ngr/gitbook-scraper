import requests
from bs4 import BeautifulSoup
import html2text
import urllib.parse
import os
import re

# --- Configuration ---
# Consider making these easily adjustable
GITBOOK_BASE_URL = 'https://developers.make.com/api-documentation' # Base URL, links are relative to this
STARTING_PAGE_PATH = '/api-documentation/getting-started' # Path to the main page relative to base
OUTPUT_DIR = 'extracted_docs'
# ---------------------

def fetch_html(url):
    """Fetches the HTML content of a given URL."""
    print(f"  Fetching: {url}")
    try:
        # Add headers to mimic a real browser request, sometimes needed
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers, timeout=10) # Added timeout
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"    ERROR fetching {url}: {e}")
        return None # Return None on error to signal failure

def extract_content_from_html(html, url):
    """Extracts the main content area from the HTML."""
    if not html:
        return None, "No HTML content provided"

    soup = BeautifulSoup(html, 'html.parser')

    # --- Attempt to find the main content area ---
    # Strategy 1: Look for common content containers (adjust selectors as needed)
    content_selectors = [
        'main',            # Standard HTML5 main content
        'article',         # Semantic article tag
        '[role="main"]',   # ARIA role for main content
        '.markdown-body',  # Common class used by renderers like GitHub
        '.book-body',      # GitBook specific?
        '.content',        # Generic content class
        '#content',        # Generic content ID
        '.main-content',   # Another common class
        '.documentation-page', # Hypothetical specific class
        '.post-content',   # Blog/content post style
        '.entry-content',  # WordPress style
    ]

    content_element = None
    used_selector = ""
    for selector in content_selectors:
        content_element = soup.select_one(selector)
        if content_element:
            used_selector = selector
            # print(f"    Content found using selector: {used_selector}")
            break

    # Strategy 2: If common selectors fail, fall back to body or the whole soup
    if not content_element:
        content_element = soup.find('body')
        used_selector = "body (fallback)"
        # print(f"    Content found using fallback selector: {used_selector}")
    if not content_element:
        content_element = soup # Ultimate fallback
        used_selector = "entire document (fallback)"
        # print(f"    Content is entire document (fallback)")

    if content_element:
        # Optional: Remove common non-content elements
        for nav in content_element.find_all('nav', recursive=False): # Remove top-level navs
            nav.decompose()
        # Add more elements to remove if needed (e.g., footers within content)

        # print(f"    Extracted content using '{used_selector}' for {url}")
        return str(content_element), None # Return HTML string, no error
    else:
        error_msg = f"Failed to find content area in the HTML for {url}."
        print(f"    ERROR: {error_msg}")
        return None, error_msg


def convert_html_to_markdown(html_content):
    """Converts HTML string to Markdown."""
    if not html_content:
        return ""

    h = html2text.HTML2Text()
    # Configure html2text options for better output
    h.ignore_links = False
    h.body_width = 0 # Don't wrap lines
    h.mark_code = True # Use backticks for code
    # h.protect_links = True # Protect links from line breaks (if available in your html2text version)
    # h.skip_internal_links = False
    # You can adjust other options like tables, images, etc. as needed

    try:
        markdown_content = h.handle(html_content)
        return markdown_content
    except Exception as e:
        print(f"    ERROR converting HTML to Markdown: {e}")
        return f"<!-- Error converting HTML to Markdown: {e} -->\n{html_content}" # Fallback: return HTML with error comment


def get_filename_from_url(url, base_url):
    """Derives a filename from the URL path."""
    try:
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path.rstrip('/') # Remove trailing slash

        # Handle the base URL path (e.g., /api-documentation/)
        parsed_base = urllib.parse.urlparse(base_url)
        base_path = parsed_base.path.rstrip('/')

        # Remove the base path from the URL path if present
        if path.startswith(base_path):
            relative_path = path[len(base_path):]
        else:
            relative_path = path

        # Get the last part of the path
        if relative_path:
            filename_part = os.path.basename(relative_path)
        else: # If path was just the base path or empty after removal
            filename_part = "index"

        # Sanitize filename: replace non-alphanumeric chars (except dash/underscore) with underscores
        # and ensure it doesn't start/end with a dot or dash
        filename_safe = re.sub(r'[^a-zA-Z0-9\-_]', '_', filename_part)
        filename_safe = filename_safe.strip('._-') # Remove leading/trailing unsafe chars

        # Ensure it's not empty and handle potential issues
        if not filename_safe:
            filename_safe = "untitled_page"
        if filename_safe.startswith(('.', '-')): # If it starts with dot/dash after sanitization
             filename_safe = "page_" + filename_safe

        # Ensure unique name if needed (basic check, could be improved)
        # (This simple check might not be perfect for all cases)
        # counter = 1
        # original_filename_safe = filename_safe
        # while os.path.exists(os.path.join(OUTPUT_DIR, f"{filename_safe}.md")):
        #     filename_safe = f"{original_filename_safe}_{counter}"
        #     counter += 1

        return f"{filename_safe}.md"

    except Exception as e:
        print(f"    ERROR deriving filename from URL {url}: {e}")
        return "error_url.md" # Fallback filename

def get_filename_from_title(html, default="untitled"):
    """Attempts to get the page title for filename."""
    if not html:
        return default
    try:
        soup = BeautifulSoup(html, 'html.parser')
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            title = title_tag.string.strip()
            # Sanitize title for filename use
            filename_safe = re.sub(r'[^a-zA-Z0-9\-_ ]', '', title) # Keep spaces initially
            filename_safe = re.sub(r'\s+', '_', filename_safe) # Replace spaces with underscores
            filename_safe = filename_safe.strip('._-')
            if not filename_safe:
                 filename_safe = default
            return f"{filename_safe}.md"
        else:
            return f"{default}.md"
    except Exception as e:
       print(f"    ERROR extracting title: {e}")
       return f"{default}.md"


def save_markdown_to_file(markdown_content, filename, output_dir):
    """Saves Markdown content to a specified file."""
    if not markdown_content:
        print(f"    WARNING: No content to save for {filename}")
        return

    filepath = os.path.join(output_dir, filename)
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"    Saved: {filepath}")
    except Exception as e:
        print(f"    ERROR saving file {filepath}: {e}")

def extract_page_links(html, base_url):
    """Finds links to other pages within the same domain."""
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    links = set() # Use a set to avoid duplicates
    try:
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            # Resolve relative URLs
            full_url = urllib.parse.urljoin(base_url, href)

            # Parse the full URL
            parsed_full = urllib.parse.urlparse(full_url)
            parsed_base = urllib.parse.urlparse(base_url)

            # Check if the link is within the same domain and scheme
            if (parsed_full.netloc == parsed_base.netloc and
                parsed_full.scheme == parsed_base.scheme and
                # Often, you want to filter for specific paths or extensions
                # This example assumes API docs are under the base path
                full_url.startswith(base_url) and
                # Avoid obvious non-page links (you might need to adjust this)
                not href.startswith('#') and # Fragments
                not href.startswith('mailto:') and
                not href.endswith(('.pdf', '.jpg', '.png', '.gif', '.zip')) # Common non-HTML files
                # Consider filtering by path prefix if docs are in a subdirectory
                # e.g., if parsed_full.path.startswith('/api-documentation/')
               ):
                # Normalize the URL (remove fragments, ensure trailing slash consistency if needed)
                normalized_url = urllib.parse.urlunparse((
                    parsed_full.scheme,
                    parsed_full.netloc,
                    parsed_full.path.rstrip('/') + ('/' if parsed_full.path.endswith('/') and parsed_full.path != '/' else ''), # Keep trailing slash logic if important
                    '', # params
                    '', # query
                    ''  # fragment
                ))
                links.add(normalized_url)
    except Exception as e:
        print(f"    ERROR extracting links: {e}")

    return list(links)

def process_single_page(url, base_url, output_dir):
    """Fetches, extracts, converts, and saves a single page."""
    print(f"Processing page: {url}")
    html_content = fetch_html(url)
    if html_content is None:
        return # Stop processing this page if fetch failed

    extracted_html, error = extract_content_from_html(html_content, url)
    if error:
        # Even if extraction isn't perfect, try to save *something*
        print(f"    Warning during extraction: {error}. Attempting to convert raw HTML.")
        extracted_html = html_content # Fallback to raw HTML

    markdown_content = convert_html_to_markdown(extracted_html)

    # Decide on filename: try URL path first, then title
    filename = get_filename_from_url(url, base_url)
    # Optional: If URL filename seems bad, try title
    # if filename in ['index.md', 'error_url.md'] or filename.startswith('untitled'):
    #     title_filename = get_filename_from_title(html_content)
    #     if title_filename and title_filename != 'untitled.md':
    #         filename = title_filename

    save_markdown_to_file(markdown_content, filename, output_dir)


def main(base_url, start_path, output_dir):
    """Main function to orchestrate the scraping process."""
    print(f"Starting documentation extraction...")
    print(f"Base URL: {base_url}")
    print(f"Starting Path: {start_path}")
    print(f"Output Directory: {output_dir}")
    print("-" * 20)

    start_url = urllib.parse.urljoin(base_url, start_path)
    print(f"Fetching main page to discover links: {start_url}")
    main_page_html = fetch_html(start_url)

    if main_page_html is None:
        print("Failed to fetch the starting page. Exiting.")
        return

    print("Extracting links from the main page...")
    page_links = extract_page_links(main_page_html, base_url)
    print(f"Found {len(page_links)} potential page links.")

    # Add the starting page itself if it's not already discovered or you want to ensure it's processed
    if start_url not in page_links:
        page_links.append(start_url)
        print(f"Added starting URL to processing list.")

    if not page_links:
        print("No links found to process. Exiting.")
        return

    print("-" * 20)
    print("Processing individual pages...")
    for link in page_links:
        try:
            process_single_page(link, base_url, output_dir)
        except Exception as e:
            print(f"  Unexpected error processing {link}: {e}")
    print("-" * 20)
    print("Extraction process completed.")

if __name__ == '__main__':
    # Use the defined constants
    main(GITBOOK_BASE_URL, STARTING_PAGE_PATH, OUTPUT_DIR)
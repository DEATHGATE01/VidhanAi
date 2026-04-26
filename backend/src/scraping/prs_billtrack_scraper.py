"""
PRS India Bill Track Scraper
Original working version that properly scrapes bills from PRS India
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time


class PRSBillTrackScraper:
    """
    Scraper for PRS India Legislative Brief - Bill Track
    https://prsindia.org/billtrack
    """
    
    def __init__(self):
        self.base_url = "https://prsindia.org"
        self.billtrack_url = f"{self.base_url}/billtrack"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def fetch_bill_list(self, max_items=None):
        """
        Fetch list of bills from PRS BillTrack page
        
        Args:
            max_items: Maximum number of bills to fetch (None = fetch all)
        
        Returns:
            list: List of bill dictionaries with metadata
        """
        try:
            print(f"Fetching bills from {self.billtrack_url}")
            response = self.session.get(self.billtrack_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            bills = []
            
            # PRS website updated - now uses div.views-row instead of tables
            bill_rows = soup.find_all('div', class_='views-row')
            
            if not bill_rows:
                print("WARNING: Could not find bill rows on page")
                return []
            
            print(f"Found {len(bill_rows)} bills on page")
            
            # Limit if max_items specified, otherwise fetch all
            rows_to_process = bill_rows[:max_items] if max_items else bill_rows
            
            for idx, row in enumerate(rows_to_process):
                try:
                    # Extract bill title and link from h3 > a
                    title_field = row.find('div', class_='views-field-title-field')
                    if not title_field:
                        continue
                    
                    title_link = title_field.find('a')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    bill_url = title_link.get('href', '')
                    
                    # Make URL absolute
                    if bill_url and not bill_url.startswith('http'):
                        bill_url = self.base_url + bill_url
                    
                    # Extract status from status field
                    status_field = row.find('div', class_='views-field-field-bill-status')
                    status = 'Unknown'
                    if status_field:
                        status_span = status_field.find('span')
                        if status_span:
                            status = status_span.get_text(strip=True)
                    
                    # Try to extract ministry from other fields (if available)
                    ministry = 'Unknown'
                    ministry_field = row.find('div', class_='views-field-field-ministry') or \
                                   row.find('div', class_='views-field-ministry')
                    if ministry_field:
                        ministry = ministry_field.get_text(strip=True)
                    
                    # Extract introduction date if available
                    introduction_date = None
                    date_field = row.find('div', class_='views-field-field-date') or \
                               row.find('div', class_='views-field-date')
                    if date_field:
                        date_text = date_field.get_text(strip=True)
                        # Try to parse date formats
                        for fmt in ['%d %B, %Y', '%d %b, %Y', '%d-%m-%Y', '%B %d, %Y']:
                            try:
                                introduction_date = datetime.strptime(date_text, fmt)
                                break
                            except:
                                continue
                    
                    bill_data = {
                        'title': title,
                        'url': bill_url,
                        'ministry': ministry,
                        'status': status,
                        'introduction_date': introduction_date
                    }
                    
                    bills.append(bill_data)
                    
                    if (idx + 1) % 50 == 0:
                        print(f"  Processed {idx + 1} bills...")
                
                except Exception as e:
                    print(f"Error parsing row {idx}: {e}")
                    continue
            
            print(f"Successfully fetched {len(bills)} bills")
            return bills
        
        except Exception as e:
            print(f"Error fetching bill list: {e}")
            return []

    def fetch_ministry_and_date(self, bill_url):
        """Lightweight fetch to extract only ministry and introduction_date from a bill detail page.

        This is intentionally minimal to speed up bulk updates (no full content parsing).
        """
        try:
            if not bill_url:
                return {'ministry': 'Unknown', 'introduction_date': None}

            resp = self.session.get(bill_url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')

            # Extract ministry (multiple possible class names)
            ministry = 'Unknown'
            m_field = (
                soup.find('div', class_='field-name-field-ministry') or
                soup.find('div', class_='field-name-ministry') or
                soup.find('div', class_='views-field-field-ministry')
            )
            if m_field:
                ministry = m_field.get_text(strip=True)

            # Extract introduction date from likely containers
            introduction_date = None
            date_field = (
                soup.find('div', class_='entity-field-collection-item') or
                soup.find('div', class_='field-name-field-date') or
                soup.find('div', class_='views-field-field-date')
            )
            if date_field:
                date_text = date_field.get_text(strip=True)
                for fmt in ['%d %B, %Y', '%d %b, %Y', '%d-%m-%Y', '%B %d, %Y']:
                    try:
                        introduction_date = datetime.strptime(date_text, fmt)
                        break
                    except Exception:
                        continue

            return {'ministry': ministry, 'introduction_date': introduction_date}
        except Exception as e:
            print(f"Error fetching ministry for {bill_url}: {e}")
            return {'ministry': 'Unknown', 'introduction_date': None}
    
    def fetch_bill_content(self, bill_url):
        """
        Fetch full content of a specific bill from PRS India
        
        Args:
            bill_url: URL of the bill page
        
        Returns:
            dict: Bill content with full_text, sections, paragraphs
        """
        try:
            print(f"Fetching content from: {bill_url}")
            response = self.session.get(bill_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Initialize content containers
            full_text = ''
            sections = []
            paragraphs = []
            summary_link = None
            pdf_link = None
            ministry = None
            introduction_date = None
            
            # Extract metadata from bill page
            # Ministry
            ministry_field = soup.find('div', class_='field-name-field-ministry')
            if ministry_field:
                ministry_items = ministry_field.find('div', class_='field-items')
                if ministry_items:
                    ministry = ministry_items.get_text(strip=True)
                    print(f"Found ministry: {ministry}")
            
            # Introduction date from status details
            date_fields = soup.find_all('div', class_='entity-field-collection-item')
            for field in date_fields:
                status_text = field.get_text(strip=True)
                if 'Introduced' in status_text:
                    # Extract date from text like "IntroducedLok SabhaAug 20, 2025"
                    import re
                    date_match = re.search(r'([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})', status_text)
                    if date_match:
                        date_str = date_match.group(1)
                        try:
                            introduction_date = datetime.strptime(date_str, '%b %d, %Y')
                            print(f"Found introduction date: {introduction_date}")
                        except:
                            pass
                    break
            
            # Try multiple content selectors (PRS uses different structures)
            content_containers = [
                soup.find('div', class_='field-name-body'),
                soup.find('div', class_='field-item'),
                soup.find('div', class_='field-type-text-with-summary'),
                soup.find('div', {'id': 'bill-content'}),
                soup.find('article'),
                soup.find('div', class_='content'),
                soup.find('main')  # Fallback to main content area
            ]
            
            content_div = None
            for container in content_containers:
                if container:
                    content_div = container
                    break
            
            # If still no content div found, try to get all paragraphs from body
            if not content_div:
                print("WARNING: No specific content div found, extracting from entire body")
                content_div = soup.find('body')
            
            if content_div:
                # Extract all paragraphs
                paras = content_div.find_all('p')
                paragraphs = [p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 20]
                
                # Extract sections (h2, h3 headers with following content)
                headers = content_div.find_all(['h2', 'h3', 'h4'])
                for header in headers:
                    section_title = header.get_text(strip=True)
                    section_paras = []
                    
                    # Get paragraphs following this header until next header
                    for sibling in header.find_next_siblings():
                        if sibling.name in ['h2', 'h3', 'h4']:
                            break
                        if sibling.name == 'p':
                            para_text = sibling.get_text(strip=True)
                            if len(para_text) > 20:
                                section_paras.append(para_text)
                    
                    if section_title:
                        sections.append({
                            'title': section_title,
                            'content': '\n'.join(section_paras),
                            'paragraphs': section_paras
                        })
                
                # Get full text
                full_text = content_div.get_text(separator='\n', strip=True)
            
            # If no structured content found, try to get main text
            if not full_text or len(full_text) < 100:
                main_content = soup.find('main') or soup.find('body')
                if main_content:
                    # Remove unwanted elements
                    for elem in main_content(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                        elem.decompose()
                    full_text = main_content.get_text(separator='\n', strip=True)
                    
                    # Extract paragraphs from cleaned text
                    paragraphs = [p.strip() for p in full_text.split('\n') if len(p.strip()) > 50]
            
            # Look for PDF and summary links
            pdf_links = soup.find_all('a', href=True)
            for link in pdf_links:
                href = link.get('href', '')
                if '.pdf' in href.lower():
                    pdf_link = href if href.startswith('http') else self.base_url + href
                    break
            
            # Validate content
            if not full_text or len(full_text) < 50:
                print(f"WARNING: Insufficient content extracted (only {len(full_text)} chars)")
                return None
            
            print(f"Extracted {len(paragraphs)} paragraphs, {len(sections)} sections ({len(full_text)} chars)")
            
            return {
                'full_text': full_text,
                'sections': sections,
                'paragraphs': paragraphs,
                'summary_link': summary_link,
                'pdf_link': pdf_link,
                'ministry': ministry,
                'introduction_date': introduction_date
            }
        
        except Exception as e:
            print(f"Error fetching bill content: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def fetch_bill_details(self, bill_url):
        """
        Alias for fetch_bill_content for backward compatibility.
        Fetches complete bill details including ministry, date, and content.
        
        Args:
            bill_url: URL of the bill page
        
        Returns:
            dict: Bill details with ministry, introduction_date, content, pdf_url
        """
        content_data = self.fetch_bill_content(bill_url)
        
        if not content_data:
            # Try lightweight fetch for at least ministry and date
            basic_data = self.fetch_ministry_and_date(bill_url)
            return {
                'ministry': basic_data.get('ministry', 'Unknown'),
                'introduction_date': basic_data.get('introduction_date'),
                'content': None,
                'pdf_url': None
            }
        
        return {
            'ministry': content_data.get('ministry', 'Unknown'),
            'introduction_date': content_data.get('introduction_date'),
            'content': content_data.get('full_text'),
            'pdf_url': content_data.get('pdf_link')
        }
    
    def close(self):
        """Close the session"""
        self.session.close()

import json
from metapub import PubMedFetcher, FindIt
from metapub.exceptions import InvalidPMID
import requests
from PyPDF2 import PdfReader
import csv
from itertools import islice
import os
import re
import traceback
import time

fetch = PubMedFetcher()

def sanitize_text(text):
    if not text:
        return ""

    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    text = re.sub(r'[^\x00-\x7F]+', '', text)

    text = re.sub(r'[^\w\s.,;:!?()-]', '', text)

    text = re.sub(r'<[^>]*>', '', text)

    return text

def get_pmids():
    pmids = []

    with open('SB_publication_PMC.csv', 'r') as file:
        csvFile = csv.reader(file)
        next(csvFile)
        for row in islice(csvFile, 551, 608):
            title = row[0]
            
            # Get the PMID
            pmid = fetch.pmids_for_query(query=title, pmc_only=True, retmax=1)
            pmids.append(pmid[0])
    
    return pmids

def extract_section(text, section_title):
    section_pattern = re.compile(rf'({section_title})')
    
    section_start = re.search(section_pattern, text)
    if not section_start:
        return None 
    

    section_text = text[section_start.end():]

    next_section_start = re.search(r'(Introduction|Conclusion|Methods|Results|Discussion)', section_text)
    if next_section_start:
        section_text = section_text[:next_section_start.start()]

    return section_text.strip()

def extract_image_descriptions(text):
    image_captions = []

    pattern = re.compile(r'(Figure \d+\.)\s+([^.]+)\.', re.IGNORECASE)
    matches = pattern.findall(text)

    for match in matches:
        figure_number = match[0]  # "Figure 1.", "Figure 2.", etc.
        description = match[1].strip()  # The description part

        if description:
            # Store the captions as a dictionary with keys 'figure_number' and 'caption'
            image_captions.append({
                "figure_number": figure_number,
                "caption": description
            })
    
    return image_captions

def get_article_data(pmid):
    try:
        article_data = []

        article = fetch.article_by_pmid(pmid)

        data = {
            'pmid': pmid,
            'title': article.title,
            'year': article.year,
            'journal': article.journal,
            'abstract': article.abstract,
            'full_text': "",
            'introduction': None,
            'conclusion': None,
            'images': []
        }

        article_data.append(data)

        # Make output dir
        output_dir = f"data/{pmid}"
        images_dir = os.path.join(output_dir, 'images')
        os.makedirs(images_dir, exist_ok=True)

        src = FindIt(pmid, retry_errors=True)

        if src.url:
            print(f"Downloading PDF from {src.url}")
            pdf_response = requests.get(src.url)

            pdf_filename = os.path.join(output_dir, f"article_{pmid}.pdf")
            with open(pdf_filename, 'wb') as f:
                f.write(pdf_response.content)

            print(f"PDF saved as {pdf_filename}")

            count = 0

            try:
                with open(pdf_filename, 'rb') as file:
                    reader = PdfReader(file)
                    text = ""

                    for page in reader.pages:
                        page_text = page.extract_text()

                        text += page_text

                        image_captions = extract_image_descriptions(text)
                        print(image_captions)

                        for image_file_object in page.images:
                            figure_number = f"Figure_{count + 1}"
                            image_filename = os.path.join(images_dir, f"{figure_number}.jpg")
                            with open(image_filename, "wb") as fp:
                                fp.write(image_file_object.data)

                            matching_caption = next((caption["caption"] for caption in image_captions if caption["figure_number"] == f"Figure {count}."), "No caption available")
                            print(matching_caption)
                            
                            data['images'].append({
                                'filename': f"{figure_number}.jpg",
                                'caption': matching_caption
                            })

                            count += 1

                print("PDF text extraction successful.")

                data['introduction'] = extract_section(sanitize_text(text), "Introduction")
                data['conclusion'] = extract_section(sanitize_text(text), "Conclusion")

                data['full_text'] = sanitize_text(text)

            except Exception as e:
                traceback.print_exc()
                print(f"Error converting PDF to text: {e}")
        else:
            print(src.reason)
        
        json_filename = os.path.join(output_dir, 'article_data.json')
        with open(json_filename, 'w') as json_file:
            json.dump(article_data, json_file, indent=4)

        print(f"Data has been exported to {json_filename}")

    except InvalidPMID:
        print("Invalid PMID")

pmids = get_pmids()

for pmid in pmids:
    get_article_data(pmid)
    time.sleep(5)
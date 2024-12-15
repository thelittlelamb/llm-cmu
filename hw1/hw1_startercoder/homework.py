import argparse
import re
import requests
import json
from utils import  read_warc_file, retrieve_bad_words, read_wet_file
# from datasets import load_dataset
from typing import Set, Dict
from bs4 import BeautifulSoup
import string
import chardet

def retrieve_bad_words() -> set[str]:
    """Helper function - that reads a list of bad words from a file and returns them as a set.
    Returns:
        Set[str]: A set containing lowercase bad words.
    """
    with open('./bad_word_list.txt', 'r') as file:
        records = file.read().strip().split('\n')
        bad_words = [record.lower() for record in records]
        return set(bad_words)


def html_to_text(html: str) -> str:
    """Converts HTML content to plain text..
    Args:
        html (bytes): HTML content as bytes.
    Returns:
        str: Plain text extracted from HTML.
    """
    # Attempt to decode the HTML content with error handling
    # try:
    #     html_str = html.decode("utf-8")
    # except UnicodeDecodeError:
    #     html_str = html.decode("utf-8", errors="replace")  # Replace undecodable characters

    # Determine if the content is XML or HTML
    # if html.strip().startswith("<?xml") or html.strip().startswith("<!DOCTYPE"):
    #     # Use XML parser if it's XML-like content
    #     soup = BeautifulSoup(html_str, features="xml")
    # else:
        # Default to HTML parser
    # 假设 html_content 是从网页获取的字节内容
    # import pdb;pdb.set_trace()
    detect_res = chardet.detect(html)
    detected_encoding = detect_res['encoding']
    detected_confidence = detect_res['confidence']
    # 如果检测结果为空或置信度低，使用默认编码
    if detected_encoding is None or detected_confidence < 0.5:
        detected_encoding = 'utf-8'
    html = html.decode(detected_encoding, errors='replace')
    # import pdb;pdb.set_trace()
    # soup = BeautifulSoup(html_str, 'html.parser')
    if html.strip().startswith("<?xml"):
        # Use XML parser if it's XML-like content
        soup = BeautifulSoup(html, features="xml")
    else:
        soup = BeautifulSoup(html, "html.parser")
    # 特别处理代码块
    for code in soup.find_all('code'):
        code.string = f"`{code.get_text()}`"  # 用反引号包裹代码片段

    # 特别处理表格
    for table in soup.find_all('table'):
        table_text = []
        for row in table.find_all('tr'):
            cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
            table_text.append("\t".join(cells))  # 使用制表符分隔单元格
        table.replace_with("\n".join(table_text))  # 将表格替换为纯文本形式

    # 特别处理图片
    for img in soup.find_all('img'):
        alt_text = img.get('alt', '[Image]')  # 提取图片的替代文本
        img.replace_with(alt_text)  # 用替代文本替换图片标签

    # 提取纯文本
    plain_text = soup.get_text(separator='\n')  # 用换行符分隔文本
    # 清理多余的空白符和空行
    plain_text = re.sub(r'\n+', '\n', plain_text)  # 合并多余的换行符
    plain_text = re.sub(r'[ \t]+', ' ', plain_text)  # 合并多余的空格
    plain_text = plain_text.strip()  # 去除首尾空白符
    return plain_text


def replace_pii(text: str) -> str:
    """Masks personally identifiable information (PII) from text with the specified masking formats.
    Args: 
        text (str): Candidate text.
    Returns:
        str: Text with PII obfuscated.
    """
    # Mask US Social Security numbers of the format XXX-XX-XXXX
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', 'XXX-XX-XXXX', text)
    # Mask 10-digit phone numbers preceded by +1
    text = re.sub(r'\+1\d{10}\b', '+1XXXXXXXXXX', text)
    
    return text

def clean_text(text: str) -> str:
    """Removes substrings identified as low-quality according to alphanumeric, whitespace and valid document checks.  
    Args:
        text (str): document to process.
    Returns:
        str: cleaned document
    """
    paragraphs = text.split("\n")
    cleaned_paragraphs = []
    
    for paragraph in paragraphs:
        # Remove paragraphs with >100 alphanumeric characters with no whitespace
        if re.search(r'\b[a-zA-Z0-9]{101,}\b', paragraph):
            continue
        
        # Remove paragraphs that do not contain punctuation
        if not any(char in string.punctuation for char in paragraph):
            continue
        
        cleaned_paragraphs.append(paragraph)
    
    return "\n".join(cleaned_paragraphs)

def heuristic_quality_filter(text: str) -> bool:
    """Rejects documents based on the presence of bad words and punctuation.
    Args:
        text (str): document to check
    Returns:
        bool: returns True if the document passes the filters, False otherwise.
    """
    # Load bad words from the provided list
    bad_words = retrieve_bad_words() # Replace with the actual list from the file
    if any(bad_word in text for bad_word in bad_words):
        return False
    
    # Check if document contains punctuation
    if not any(char in string.punctuation for char in text):
        return False
    
    # Check if document contains non-whitespace characters
    if not text.strip():
        return False
    
    # Check if at least 80% of characters are alphanumeric, punctuation, or whitespace
    valid_chars = sum(1 for char in text if char.isalnum() or char in string.punctuation or char.isspace())
    if valid_chars / len(text) < 0.8:
        return False
    
    return True


if __name__ == '__main__' :
    parser = argparse.ArgumentParser()
    parser.add_argument('--fname', type = str,  default = '', help = 'Specify the path for your warc file.')
    parser.add_argument('--num_records', type = int,  default=10, help = 'Specify the number of records you want to parse (only used for debugging with smaller sets)')
    args = parser.parse_args()

    if args.fname:
        count = 0
        for url, html_text in read_warc_file(args.fname):
            # print(html_text.strip()[:100])
            text = html_to_text(html_text)
            cleaned_text = clean_text(text)
            cleaned_nopii_text = replace_pii(cleaned_text)
            passes_check = heuristic_quality_filter(cleaned_nopii_text)
            
            # print("Passes heuristic quality filter:", passes_check)
            if passes_check:
                count += 1
            # print(cleaned_nopii_text)
            # print("\n\n\n")
        # for url, text in read_wet_file(args.fname, args.num_records):
        #     decoded_text = text.decode('utf-8', errors='replace')  # 替换无法解码的字符
        #     print(decoded_text)
        print(count)
    else:
        print("Usage: python homework.py --fname data.warc")
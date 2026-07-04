import re

def normalize_company_name(name: str) -> str:
    """
    Normalizes a company name by converting to lowercase, stripping common 
    corporate suffixes, removing punctuation, and collapsing whitespace.
    
    Example:
    "Zenlyte Solutions Pvt. Ltd." -> "zenlyte solutions"
    "Zenlyte Solutions Private Limited" -> "zenlyte solutions"
    """
    if not name:
        return ""
        
    # Convert to lowercase
    name_clean = name.lower()
    
    # Strip common punctuation (commas, periods, hyphens)
    name_clean = re.sub(r"[.,\-()\[\]{}]", " ", name_clean)
    
    # Define corporate suffixes to remove (as distinct word boundaries)
    suffixes = [
        r"\bpvt\b", r"\bltd\b", r"\bprivate\b", r"\blimited\b", 
        r"\bllp\b", r"\binc\b", r"\bco\b", r"\bcorp\b", r"\bcorporation\b"
    ]
    
    # Remove each suffix
    for suffix in suffixes:
        name_clean = re.sub(suffix, " ", name_clean)
        
    # Collapse multiple spaces and strip leading/trailing spaces
    name_clean = re.sub(r"\s+", " ", name_clean).strip()
    
    return name_clean

import difflib

def get_similarity_ratio(str1: str, str2: str) -> float:
    """
    Returns the similarity ratio between two strings using standard difflib.
    Returns a float between 0.0 and 1.0.
    """
    if not str1 or not str2:
        return 0.0
    return difflib.SequenceMatcher(None, str1, str2).ratio()

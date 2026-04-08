from difflib import SequenceMatcher

def get_similarity(text1, text2):
    return SequenceMatcher(None, text1, text2).ratio() * 100
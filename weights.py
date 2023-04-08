from collections import Counter
from arxiv import Search, SortCriterion
import arxiv
import re
import bibtexparser
import os
import glob
import json


def clean_text(text):
    re_keyword=r'[^-\w]+' 
    text = re.sub(re_keyword, ' ', text.lower())
    return text.strip()

def get_most_common_words(text_list, n=10):
    words = []
    for text in text_list:
        words.extend([word for word in clean_text(text).split() if len(word) > 3] )
    counter = Counter(words)
    return counter.most_common(n)

def get_most_common_authors(authors_list, n=10):
    authors = []
    for author in authors_list:
        clean_name = clean_text(author.name).split()
        # print(author.name,clean_name)
        if clean_name:
            clean_name = clean_name[0][0]+" "+clean_name[-1]
            authors.append(clean_name)
    counter = Counter(authors)
    return counter.most_common(n)

def parse_bib_file(file_path):
    with open(file_path, 'r') as bib_file:
        bib_database = bibtexparser.load(bib_file)
    return bib_database.entries

def main():
    bib_directory = "."

    titles = []
    abstracts = []
    authors = []

    # Iterate over all .bib files in the directory
    for bib_file_path in glob.glob(os.path.join(bib_directory, "*.bib")):
        print(bib_file_path)
        # Parse the .bib file and extract eprint numbers
        bib_entries = parse_bib_file(bib_file_path)
        eprint_numbers = [entry.get("eprint") for entry in bib_entries if entry.get("eprint")]

        for eprint_number in eprint_numbers:
            search = Search(query=f"id:{eprint_number}", max_results=1, sort_by=SortCriterion.SubmittedDate)
            results = search.results()
            paper = next(results, None)
            # print(paper)

            if paper:
                titles.append(paper.title)
                # abstracts.append(paper.summary)
                authors.extend(paper.authors)

    top_n = 150
    top_title_keywords = get_most_common_words(titles, top_n)
    # top_abstract_keywords = get_most_common_words(abstracts, top_n)
    top_authors = get_most_common_authors(authors, top_n)

    # Prepare the data for JSON serialization
    data = {
        "keywords": [
            {"keyword": keyword, "weight": weight}
            for keyword, weight in top_title_keywords # + top_abstract_keywords
        ],
        "authors": [
            {"author": author, "weight": weight} for author, weight in top_authors
        ],
    }

    # Save the data to a JSON file
    with open("preferences_gen.json", "w") as outfile:
        json.dump(data, outfile, indent=2)


    # print("Most common keywords in abstracts:", top_abstract_keywords)
    print("Most common keywords in titles:", top_title_keywords)
    print("Most common authors:", top_authors)

if __name__ == "__main__":
    main()


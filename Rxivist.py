import feedparser
import urllib
import urllib.parse
import json
import pandas as pd
from bs4 import BeautifulSoup
import re
from numpy import sqrt
import datetime

preferences_file = "preferences_gen.json"

def smooth(w):
    w3 = w#*w*w
    return w3/sqrt(abs(w3))

def parse_authors(arxiv_entry):
    # return [a.get_text() for a in BeautifulSoup(arxiv_entry.author, 'html.parser').find_all('a')]
    return [author["name"] for author in arxiv_entry.authors]

def parse_summary(arxiv_entry):
    return arxiv_entry.summary
    # return BeautifulSoup(arxiv_entry.summary, 'html.parser').get_text() 

def parse_title(arxiv_entry):
    # return re.split("\s\(arXiv", arxiv_entry.title)[0]
    return arxiv_entry.title

def standardize_authors(authors):
    re_author=r'[^-\w]+' 
    standard_authors = []
    for author in authors:
        clean_name = re.sub(re_author, ' ', author.lower())
        clean_name = clean_name.split()
        if clean_name:
            clean_name = clean_name[0][0]+" "+clean_name[-1] # first initial _ surname
            standard_authors.append(clean_name)
    return standard_authors

def standardize_keywords(text):
    return re.findall(r'\b[\w-]{4,}\b', text.lower())

def fetch_arxiv_papers(feed_url, date=None):
    # if date:
    #     date_query = urllib.parse.urlencode({"date": date})
    #     feed_url += "?" + date_query
    response = urllib.request.urlopen(feed_url)
    feed_data = response.read()
    return feedparser.parse(feed_data)


def load_preferences(file_path):
    with open(file_path, 'r') as f:
        preferences = json.load(f)
    return preferences

def filter_papers(papers, keywords, favorite_authors, threshold = 10 ):
    filtered_papers = []
    for entry in papers.entries:
        title = parse_title(entry)
        title_words = standardize_keywords(title)
        summary = parse_summary(entry)
        summary_words = standardize_keywords(summary)
        authors = parse_authors(entry) 
        standard_authors = standardize_authors(authors)

        title_score = sum(smooth(kw["weight"]) for kw in keywords if kw["keyword"].lower() in title_words)/len(title_words)
        summary_score = sum(smooth(kw["weight"]) for kw in keywords if kw["keyword"].lower() in summary_words)/len(summary_words)
        author_score = sum(smooth(au["weight"]) for au in favorite_authors if au["author"] in standard_authors)/len(standard_authors)
        
        title_weight = 10
        summary_weight = 10
        author_weight = 10
        if author_score != author_score:
            for au in favorite_authors:
                if au["author"] in standard_authors: 

                    print(au["weight"],smooth(au["weight"])) 
        paper_score = int( title_score*title_weight + summary_score*summary_weight + author_score*author_weight)
        
        if paper_score > threshold:
            filtered_papers.append({"paper": entry, "score": paper_score})

    filtered_papers.sort(key=lambda x: x["score"], reverse=True)
    return filtered_papers

def update_preferences(preferences, paper, downvote = False):
    # Extract authors
    author_string = paper["Authors"]

    author_names = standardize_authors(author_string)
    for author_name in author_names:
        existing_author = next((a for a in preferences["authors"] if a["author"] == author_name), None)
        if existing_author:
            if downvote:
                existing_author["weight"] -= 1
            else:
                existing_author["weight"] += 1
        else:
            if downvote:
                preferences["authors"].append({"author": author_name, "weight": -1})
            else:
                preferences["authors"].append({"author": author_name, "weight": 1})

    # Extract title keywords
    title = paper["Title"]
    words = standardize_keywords(title)
    for word in words:
        existing_keyword = next((kw for kw in preferences["keywords"] if kw["keyword"] == word), None)
        if existing_keyword:
            if downvote:
                existing_keyword["weight"] -= 1
            else:
                existing_keyword["weight"] += 1
        else:
            if downvote:
                preferences["keywords"].append({"keyword": word, "weight": -1})
            else:
                preferences["keywords"].append({"keyword": word, "weight": 1})

    # Save updated preferences to the JSON file
    with open(preferences_file, "w") as f:
        json.dump(preferences, f, indent=2)


def papers_table(date):
    end_date = date
    start_date = end_date - datetime.timedelta(days=1)

    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    feed_url = f'https://export.arxiv.org/api/query?search_query=submittedDate:[{start_date_str}+TO+{end_date_str}]&start=0&max_results=1400'

    papers = fetch_arxiv_papers(feed_url)

    preferences = load_preferences(preferences_file)

    preferred_keywords = preferences["keywords"]
    favorite_authors = preferences["authors"]

    filtered_papers = filter_papers(papers, preferred_keywords, favorite_authors)
    print("There are ",len(filtered_papers),"important papers out of",len(papers.entries) ," total papers that day.")


    data = {
        "Title": [parse_title(item["paper"])  for item in filtered_papers],
        "Authors": [', '.join(parse_authors(item["paper"])) for item in filtered_papers],
        "Link": [item["paper"].link for item in filtered_papers],
        "Summary": [parse_summary(item["paper"])for item in filtered_papers],
        "Score": [item["score"] for item in filtered_papers]
    }

    df = pd.DataFrame(data)
    df.index = pd.RangeIndex(start=1, stop=len(df) + 1)
    return df 


def main():

    date = datetime.datetime.today() # use the current date
    df = papers_table(date)
    batch_n = 0
    
    while True:
        print(df[batch_n*10:(batch_n+1)*10])
        print("\nEnter the index of the paper you want to update your preferences with or type 'q' to quit, 'w' to move up, 's' to move down:")
        
        user_input = input()


        if user_input.lower() == 'q':
            break
        elif user_input.lower() == 'y':
            date = date - datetime.timedelta(days=1)
            df = papers_table(date)
            batch_n = 0

        elif user_input.lower() == 't':
            if date<today:
                date = date + datetime.timedelta(days=1)
                df = papers_table(date)
                batch_n = 0
            else: 
                print("It's not tomorrow yet! duh...")
        elif user_input.lower() == 'w':
            if  batch_n > 0:
                batch_n -= 1
            else:
                print("This is already the top of the list.")
        elif user_input.lower() == 's':
            if (batch_n + 1) * 10 < len(df):
                batch_n += 1
            else:
                print("No more papers to show.") 
        else:
            try:
                index = int(user_input)
                if  0 < abs(index) < len(df) + 1:
                    paper = df.iloc[abs(index)-1]
                    update_preferences(preferences, paper, index<0)
                    print("Preferences updated.")
                else:
                    print("Invalid index. Please enter a valid index.")
            except ValueError:
                print("Invalid input.") #" Please enter a valid index or 'q' to quit, 'w' to move up, 's' to move down.")

if __name__ == "__main__":
    main()

  
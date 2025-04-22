from urllib.parse import urlparse


with open('Links.txt', 'r') as file:
    links = file.readlines()

cleaned = []
for link in links:
    if link == '\n':
        cleaned.append('')
    else:
        cleaned.append(link)


def extract_unique_sources(url_list):
    sources = set()
    for url in url_list:
        url = url.strip()
        if url:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            sources.add(base_url)
    print(len(list(sources)))
    return list(sources)

extract_unique_sources(cleaned)
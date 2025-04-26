from google.genai import types
from google import genai
import os
import json
from config import GEMINI_MODEL

gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
html_sample = str(open("html_dumps/npr.html", "r").read())

everything = {
    "URL": "https://www.npr.org/2025/02/09/g-s1-47467/egypt-emergency-arab-summit",
    "json_ld": {
        "ld_json_list": [
            {
                "@type": "NewsArticle",
                "publisher": {
                    "@type": "Organization",
                    "name": "NPR",
                    "logo": {
                        "@type": "ImageObject",
                        "url": "https://media.npr.org/chrome/npr-logo-2025.jpg",
                    },
                },
                "headline": "Egypt to host Gaza summit as Israel withdraws troops from Netzarim Corridor",
                "mainEntityOfPage": {
                    "@type": "WebPage",
                    "@id": "https://www.npr.org/2025/02/09/g-s1-47467/egypt-emergency-arab-summit",
                },
                "datePublished": "2025-02-09T06:13:44-05:00",
                "dateModified": "2025-02-09T06:13:44-05:00",
                "author": {"@type": "Person", "name": ["Jerome Socolovsky"]},
                "description": "A statement by the Egyptian foreign ministry said the leaders will gather on Feb. 27 amid alarm in the region over President Trump's proposals regarding the future of Gaza.",
                "image": {
                    "@type": "ImageObject",
                    "url": "https://npr.brightspotcdn.com/dims3/default/strip/false/crop/5184x3456+0+0/resize/5184x3456!/?url=http%3A%2F%2Fnpr-brightspot.s3.amazonaws.com%2F4a%2F30%2F268408214881aa51ab3046fe858d%2Fgettyimages-2195940703.jpg",
                },
                "@context": "http://schema.org",
            }
        ],
        "article_text": 'The conflict between Israel and Palestinians â\x80\x94 and other groups in the Middle East â\x80\x94 goes back decades. These stories provide context for current developments and the history that led up to them. By Jerome Socolovsky , Robbie Griffiths People head towards their homes in the Shijaiyah neighborhood, Gaza City, on January 28, 2025. Displaced Palestinians return following a ceasefire, finding their neighborhoods in ruins.Youssef Alzanoun/AFP via Gettyhide caption TEL AVIV, Israel â\x80\x94 Egypt announced Sunday it would host a summit of Arab leaders later in the month, amid alarm in the region over President Trump\'s proposals regarding the future of Gaza. A statement by the Egyptian foreign ministry says the summit is being called in response to a Palestinian request. It said the leaders will gather on Feb. 27 to discuss "the new and dangerous developments in the Palestinian issue." Also Sunday, Israeli forces began withdrawing from the Netzarim corridor in Gaza, in the latest stage of the ceasefire deal between Israel and Hamas. The Netzarim corridor is a four mile strip of land bisecting northern and southern Gaza that Israel fortified during the war, using it as a military zone. Last month, as part of the ceasefire deal, Israel started allowing Palestinians to cross the Netzarim corridor and return to their homes in the North. The withdrawal is part of the six week first phase of the ceasefire, in which Hamas is gradually releasing 33 Israeli hostages in exchange for hundreds of Palestinian prisoners and detainees, while allowing aid to Gaza. In the next stage of the ceasefire, all remaining living hostages would be released in return for a complete Israeli withdrawal from Gaza, and "sustainable calm." But negotiations are ongoing on the details. Israel wants Hamas\' military and political capabilities eliminated, while Hamas wants all Israeli troops removed from Gaza. Egypt\'s announcement of a summit comes less than a week after many Arab states rejected Trump\'s recent comments about relocating Gaza\'s residents and creating a "Riviera of the Middle East" there, as have Palestinian leaders. Trump made the proposal Tuesday when he met Israeli Prime Minister Benjamin Netanyahu in Washington D.C. Speaking to reporters at the White House Friday, Trump said he viewed the proposal as "a real estate transaction, where we\'ll be an investor in that part of the world." He added that he was in "no rush to do anything." Several countries also condemned a suggestion by Israeli Prime Minister Benjamin Netanyahu â\x80\x94 that Saudi Arabia has enough land for a Palestinian state. Netanyahu appeared to be joking in response to a slip by an Israeli TV interviewer, but his words reverberated through the region at a time when tensions are running high. Also on Sunday, there were emotional scenes in Bangkok airport, as five Thai workers who were released after being held hostage for over a year in Gaza arrived back home. "We are all very grateful and very happy that we get to return to our homeland. We all would really like to thank you. I don\'t know what else to say," one of the Thai hostages, Pongsak Thaenna, told a news conference at the airport. The war in Gaza, sparked by Hamas\' attack that killed 1,200 people and saw 250 taken hostage, has killed more than 47,000 Palestinians according to local health authorities. In recent days, violence in the West Bank has intensified. On Sunday morning, the Palestinian Health Ministry said a 23-year-old Palestinian woman, who was eight months pregnant, was fatally shot by Israeli gunfire in the Nur Shams urban refugee camp in northern occupied West Bank. The Israeli military said in a statement that it is investigating the incident. Sponsor Message Become an NPR sponsor',
    },
    "article_text": html_sample,
}

html_parser_sys_prompt = f"""You are a highly accurate and detail-oriented extraction engine. You will be given a URL, optional json+ld data, and the full raw HTML from a news article page from an online publication. Your job is to extract and return only the essential structured content in the following JSON format:
Use this JSON schema:

{{
  "title": "...",
  "authors": "...",
  "source": "...",
  "article_text": "...",
  "published_date": "...",
  "updated_date": "..."
}}
Field Descriptions:
title (str): The headline or main title of the article, as shown on the page. This should match what a reader would consider the article's title.

authors (str): The full name(s) of the journalist(s) or author(s) who wrote the article. If multiple names are listed, include them as a comma-separated string.

source (str): The name of the publication or website (e.g., "The New York Times", "BBC", "Reuters").

article_text (str): The full readable body of the article. This includes all meaningful paragraphs that make up the story content. Do not include navigation links, ads, sidebars, or captions. Return this as a single plain string with whitespace cleaned up. Do not edit or summarize any of the article text.

published_date (str): The original publication date and time of the article, as shown on the page or in embedded metadata. If you are given a time zone, convert it to Eastern Time (ET). If you are not given a time zone, leave as is. Use this format: "2025-04-23T14:52:05"

updated_date (str): The last modified or updated date and time of the article, if present. If there is no update time, return the same value as published_date.

Instructions:
Look first in structured data (json ld, OpenGraph tags, and meta tags).

If structured data is missing or incomplete, fall back to text in visible headers, bylines, or timestamp areas.

If a field is truly not present, return an empty string "" for that field.

Your output must be a single, well-formed JSON object with only the specified keys.

Respond only with the final JSON — do not include explanations or notes.

Example Input:
{json.dumps(everything)}
Example Output:
{{
  "title": "Egypt to host Gaza summit as Israel withdraws troops from Netzarim Corridor",
  "authors": "Jerome Socolovsky, Robbie Griffiths",
  "source": "NPR",
  "article_text": "TEL AVIV, Israel — Egypt announced Sunday it would host a summit of Arab leaders later in the month, amid alarm in the region over President Trump's proposals regarding the future of Gaza.\n\nPresident Donald Trump and Israeli Prime Minister Benjamin Netanyahu speak during a news conference in the East Room of the White House on Tuesday.\nMiddle East crisis — explained\nTrump says the U.S. will 'take over' Gaza and relocate its people. What does it mean?\nA statement by the Egyptian foreign ministry says the summit is being called in response to a Palestinian request.\n\nIt said the leaders will gather on Feb. 27 to discuss 'the new and dangerous developments in the Palestinian issue.'\n\nAlso Sunday, Israeli forces began withdrawing from the Netzarim corridor in Gaza, in the latest stage of the ceasefire deal between Israel and Hamas.\n\nThe Netzarim corridor is a four mile strip of land bisecting northern and southern Gaza that Israel fortified during the war, using it as a military zone. Last month, as part of the ceasefire deal, Israel started allowing Palestinians to cross the Netzarim corridor and return to their homes in the North.\n\nThe withdrawal is part of the six week first phase of the ceasefire, in which Hamas is gradually releasing 33 Israeli hostages in exchange for hundreds of Palestinian prisoners and detainees, while allowing aid to Gaza.\n\nIn the next stage of the ceasefire, all remaining living hostages would be released in return for a complete Israeli withdrawal from Gaza, and 'sustainable calm.'\n\nBut negotiations are ongoing on the details. Israel wants Hamas' military and political capabilities eliminated, while Hamas wants all Israeli troops removed from Gaza.\n\nEgypt's announcement of a summit comes less than a week after many Arab states rejected Trump's recent comments about relocating Gaza's residents and creating a \"Riviera of the Middle East\" there, as have Palestinian leaders.\n\nTrump made the proposal Tuesday when he met Israeli Prime Minister Benjamin Netanyahu in Washington D.C. Speaking to reporters at the White House Friday, Trump said he viewed the proposal as \"a real estate transaction, where we'll be an investor in that part of the world.\" He added that he was in \"no rush to do anything.\"\n\nSeveral countries also condemned a suggestion by Israeli Prime Minister Benjamin Netanyahu — that Saudi Arabia has enough land for a Palestinian state.\n\nNetanyahu appeared to be joking in response to a slip by an Israeli TV interviewer, but his words reverberated through the region at a time when tensions are running high.\n\nDisplaced Palestinians making their way back on foot from the southern regions to their homes in the north via Al Rashid Road after the ceasefire agreement in Gaza Strip on January 28, 2025.\nMiddle East crisis — explained\nA brief history of Gaza's tortured role in the Middle East conflict\nAlso on Sunday, there were emotional scenes in Bangkok airport, as five Thai workers who were released after being held hostage for over a year in Gaza arrived back home.\n\n\"We are all very grateful and very happy that we get to return to our homeland. We all would really like to thank you. I don't know what else to say,\" one of the Thai hostages, Pongsak Thaenna, told a news conference at the airport.\n\nThe war in Gaza, sparked by Hamas' attack that killed 1,200 people and saw 250 taken hostage, has killed more than 47,000 Palestinians according to local health authorities.\n\nIn recent days, violence in the West Bank has intensified. On Sunday morning, the Palestinian Health Ministry said a 23-year-old Palestinian woman, who was eight months pregnant, was fatally shot by Israeli gunfire in the Nur Shams urban refugee camp in northern occupied West Bank. The Israeli military said in a statement that it is investigating the incident.",
  "published_date": "2025-02-09T06:13:44",
  "updated_date": "2025-02-09T06:13:44"
}}
"""


def create_cache():
    try:
        cache_name = gemini_client.caches.list()[0].name
        potential_existing = gemini_client.caches.get(name=cache_name)
        print(f"found existing cache: {cache_name}")
        return potential_existing
    except Exception as e:
        print("cache probably not created yet:", e)

        # Create a cache with a 1 hour TTL
        print("creating cached system prompt")
        cache = gemini_client.caches.create(
            model=GEMINI_MODEL,
            config=types.CreateCachedContentConfig(
                system_instruction=(html_parser_sys_prompt),
                ttl="3600s",  # 1 hour
            ),
        )
        print(cache.name)
        print("finished creating cache")
        return cache


# print(create_cache())

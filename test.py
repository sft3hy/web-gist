import os


def count_files_with_ld_json(directory="html_dumps"):
    total_files = 0
    files_with_ld_json = 0

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)

        if os.path.isfile(filepath):
            total_files += 1
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "ld+json" in content:
                        files_with_ld_json += 1
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    print(f"Total files: {total_files}")
    print(f"Files containing 'ld+json': {files_with_ld_json}")


# Run the function
# count_files_with_ld_json()


sample = """https://apnews.com/article/iran-us-nuclear-talks-iaea-zarif-tehran-c3a8afc699c670300b9521f1e2019ef7
https://www.cbc.ca/news/politics/carney-trump-no-call-election-1.7491734
https://www.excelsior.com.mx/nacional/operacion-frontera-da-resultados-positivos-en-2-dias-de-operativos/1698767
https://www.devdiscourse.com/article/business/3249768-faas-critical-messaging-system-back-online-after-outage
https://asia.nikkei.com/Economy/China-GDP-grows-5.4-in-first-quarter-as-tariff-war-darkens-outlook
https://www.securityweek.com/china-admitted-to-us-that-it-conducted-volt-typhoon-attacks-report/
https://timesofindia.indiatimes.com/business/india-business/india-new-zealand-to-restart-fta-talks-after-a-10-year-gap/articleshow/119085808.cms
https://www.themoscowtimes.com/2025/02/13/why-are-we-handing-russia-what-it-wants-eus-chief-diplomat-blasts-us-over-ukraine-a87993
https://www.wsls.com/weather/2025/02/15/flash-flood-warning-for-portions-of-southwest-virginia-through-1045-pm/
https://balkaninsight.com/2025/02/20/montenegro-parliament-to-probe-decades-of-attacks-on-journalists/
https://www.washingtonhttps://apnews.com/article/pakistan-bannu-explosion-suicide-bombers-10efba049007e483270ba1225973438epost.com/world/2025/03/04/pakistan-bannu-explosion-suicide-bombers/15be6924-f909-11ef-bbd0-5841f0ec1418_story.html
https://www.axios.com/2025/03/09/us-trump-israel-hamas-gaza-talks
https://www.plenglish.com/news/2025/03/21/nicaragua-foreign-investment-exceeded-three-billion-dollars/
https://www.eleconomista.com.mx/politica/sheinbaum-anuncia-5-principios-politica-exterior-negociar-eu-20250329-752599.html
https://www.vanguardngr.com/2025/04/insecurity-fg-rejects-us-embassys-post-pastors-testimonies-as-unfair-inaccurate/
https://www.washingtontimes.com/news/2025/apr/5/defense-energy-deals-india-sri-lanka-modis-visit-strengthens-ties/
https://www.rfi.fr/en/africa/20250411-fears-for-political-stability-as-joseph-kabila-plans-return-to-eastern-drc
https://www.politico.com/newsletters/national-security-daily/2025/04/11/the-clock-is-ticking-for-iran-00287080
https://www.usnews.com/news/world/articles/2025-04-13/voters-in-gabon-await-results-of-presidential-election-with-likely-victory-for-coup-leader
https://www.france24.com/en/europe/20250415-french-pm-bayrou-warns-trump-s-hurricane-has-made-france-vulnerable
https://www.africanews.com/2025/04/15/south-africa-appoints-mcebisi-jonas-as-special-us-envoy-in-bid-to-ease-tensions/
https://www.washingtonpost.com/world/2025/04/16/russia-ukraine-expiration-energy-ceasefire/
https://www.bloomberg.com/news/articles/2025-04-16/russia-seeks-to-buy-boeing-jets-with-frozen-assets-after-ukraine-ceasefire
https://www.governor.virginia.gov/newsroom/news-releases/2025/february/name-1041143-en.html
http://https://news.afp.com/#/c/main/actu/articles?id=newsml.afp.com.20250315T090647Z.doc-372h2ty&type=news
https://www.timesunion.com/news/article/sheriff-state-police-investigating-small-plane-20272639.php
https://www.jpost.com/breaking-news/article-850289
https://en.yna.co.kr/view/AEN20250416003400315?section=national/politics
https://en.mehrnews.com/news/230599/Leader-to-receive-lawmakers-for-meeting-today
https://www.timesofisrael.com/liveblog_entry/lebanons-pm-visits-syrian-president-to-discuss-border-demarcation-and-security/
https://www.kyivpost.com/post/50721
https://english.alarabiya.net/topics/russia-ukraine-war
https://www.space.com/space-exploration/launches-spacecraft/spacex-launches-9th-batch-of-proliferated-architecture-spy-satellites-for-us-government
https://www.abc4.com/news/local-news/massive-flames-visible-from-i-215-in-salt-lake-city/
https://www.firstcoastnews.com/article/news/local/folkston-georgia-plane-crash-davis-field/77-5ac26a38-35c2-4f85-8b6e-cce3e4fb7c98
https://www.ilmessaggero.it/en/pope_francis_uncertain_path_to_recovery-8761087.html?refresh_ce
https://www.hindustantimes.com/top-news/modi-leaves-for-thailand-sri-lanka-says-visit-to-bolster-ties-benefit-region-101743646746990.html
https://www.europeafrica.army.mil/ArticleViewPressRelease/Article/4139490/press-release-three-us-soldiers-found-deceased-after-m88a2-hercules-recovered/
https://ktla.com/news/local-news/rapidly-growing-silver-fire-prompts-evacuation-orders-in-inyo-mono-counties/
https://buenosairesherald.com/economics/caputo-confirms-us20-billion-deal-between-argentina-and-imf
https://www.woodtv.com/news/kalamazoo-county/police-investigate-shooting-in-kalamazoo-3/
https://tass.com/politics/1934781
https://www.ktsm.com/news/las-cruces-police-multiple-gunshot-victims-at-park/
https://katu.com/news/local/state-emergency-declared-as-storms-cause-fatal-flooding-landslides-in-southern-oregon
https://wjla.com/news/local/cia-headquarters-threats-police-presence-bomb-squad-team-fairfax-county-police-mclean-safety-public-government-trump-administration
https://www.straitstimes.com/singapore/singapore-thailand-and-us-air-forces-hold-exercise-to-enhance-readiness-cooperation
https://ism.smart.state.sbu/search/25 OFFICE OF SUDAN AFFAIRS 152<
https://kdvr.com/news/local/passengers-evacuated-after-american-airlines-plane-fire-at-denver-international-airport/
https://www.channelnewsasia.com/asia/rodrigo-duterte-icc-arrest-hague-drugs-4993946
https://www.manchesterjournal.com/local-news/plane-crash-in-manchester/article_7ad91033-dab6-5c16-a8ee-28433e9773bc.html
https://www.wlwt.com/article/kentucky-flooding-death-water-rescues/63807787
https://www.bbc.co.uk/news/resources/idt-943c9a5e-32c0-4eae-8abb-4d9c4c6eae1e
https://yemen.un.org/en/288092-un-yemen-statement-detention-additional-personnel-de-facto-authorities"""


def get_naughty_links():
    just_base_urls = ""
    for link in sample.split("\n"):
        splitted = link.split("/")
        tmp_text = "/".join(splitted[:3])  # Join first 3 parts with slashes
        just_base_urls += tmp_text + "\n"

    with open("links_that_dont_work.txt", "w") as f:
        f.write(just_base_urls.strip())

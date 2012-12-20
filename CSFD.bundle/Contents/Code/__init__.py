import datetime, re, time, unicodedata, hashlib, urlparse, types, urllib, httplib
import BeautifulSoup

re_years = ("^(19\d\d)[+]", "^(20\d\d)[+]", "[+](19\d\d)$", "[+](20\d\d)$", "[+](19\d\d)[+]", "[+](20\d\d)[+]")
re_csfdid = ("^/film/(\d+)\S+")
re_duration = ("([0-9]+)\s+min")
re_photo = ("(/photos/filmy/\S+.jpg)")

def Start():
    HTTP.CacheTime = CACHE_1HOUR * 4


class CSFDAgent(Agent.Movies):
    name = 'CSFD'
    languages = [Locale.Language.English, Locale.Language.Swedish, Locale.Language.French,
                 Locale.Language.Spanish, Locale.Language.Dutch, Locale.Language.German,
                 Locale.Language.Italian, Locale.Language.Danish]
    primary_provider = True
    fallback_agent = False
    accepts_from = None
    contributes_to = None

    def identifierize(self, string):
        string = re.sub(r"\s+", " ", string.strip())
        string = unicodedata.normalize('NFKD', safe_unicode(string))
        string = re.sub(r"['\"!?@#$&%^*\(\)_+\.,;:/]", "", string)
        string = re.sub(r"[_ ]+", "_", string)
        string = string.strip('_')
        return string.strip().lower()

    def name_to_url(self, name):
        norm_name, year = fix_title(String.StripDiacritics(name))
        search_url = "/hledat/?q=" + String.Quote(norm_name)
        conn = httplib.HTTPConnection("www.csfd.cz")
        conn.request("GET", search_url)
        r1 = conn.getresponse()
        #lets try to figure out what the result is
        data1 = r1.read()
        local_results = []

        if r1.status not in (301, 302):
            soup = BeautifulSoup.BeautifulSoup(data1)
            search_films = soup.find(id="search-films")
            n = 3
            top_results_soup = search_films.find("ul", {'class': "ui-image-list js-odd-even"})
            if top_results_soup != None:
                top_results = top_results_soup.findAll('li')
                for top_result in top_results:
                    #link to title
                    link = top_result.h3.a
                    path = link.get('href')
                    candidate_name = String.StripDiacritics(link.string)
                    yearx = top_result.p.string[-4:]
                    #score = score_strs(name, lookup_name)
                    score = -Util.LevenshteinDistance(norm_name, candidate_name)/len(norm_name)
                    if year != None and yearx.find(year) >= 0:
                        score += 0.5
                    score += 0.001 * n
                    if n > 0:
                        n = n - 1
                    local_results.append(
                        [score,
                         {'search_url': search_url, 'score': score, 'candidate_name': candidate_name, 'link': path,
                          'year': yearx}])
            other_results_soup = search_films.find("ul", {'class': "films others"})
            #print other_results_soup
            if other_results_soup != None:
                other_results = other_results_soup.findAll('li')
                for result in other_results:
                    link = result.a
                    path = link.get('href')
                    candiate_name = String.StripDiacritics(link.string)
                    yearx_r = result.find("span", {"class": "film-year"})
                    yearx = "-1"
                    if year != None and yearx_r != None:
                        yearx = yearx_r.string
                        if yearx[-1] == ')':
                            yearx = yearx[:-1]
                        if yearx[0] == '(':
                            yearx = yearx[1:]
                    score = -Util.LevenshteinDistance(norm_name, candidate_name)/len(norm_name)
                    if year != None and yearx.find(year) >= 0:
                        score += 0.5
                    score += 0.001 * n
                    if n > 0:
                        n = n - 1
                    local_results.append(
                        [score, {'search_url': search_url, 'candidate_name': candidate_name, 'link': path,
                                 'year': yearx}])
                    #print top_results_soup
            local_results.sort(reverse=True)

            if len(local_results) == 0:
                Log("Failed to find any results for " + norm_name)
                return None
            local_result = local_results[0][1]
        else:
            local_result = {'search_url': search_url, 'score': 1, 'candidate_name': norm_name,
                            'link': r1.getheader('location', '').replace('http://www.csfd.cz', ''), 'year': year}
        m=re.match(re_csfdid, local_result['link'])
        if m!=None:
            local_result['csfdid'] = "csfd:" + m.group(1)
        else:
            local_result['csfdid'] = "csfd:-1"
        local_result['name'] = norm_name
        return local_result

    def get_movie_info(self, csfdid):
        conn = httplib.HTTPConnection("www.csfd.cz")
        #norm_name, year = fix_title(String.StripDiacritics(name))
        search_url = ""
        print csfdid[5:]
        conn.request("GET", "/film/" + csfdid[5:], {}, {'Referer': "http://www.csfd.cz" + search_url})
        r1 = conn.getresponse()
        data1 = r1.read()
        soup = BeautifulSoup.BeautifulSoup(data1)
        if soup.h1.text.lower() == "redirect":
            l = soup.p.a['href'].replace('http://www.csfd.cz', '')
            conn.request("GET", l, {}, {'Referer': search_url})
            r1 = conn.getresponse()
            data1 = r1.read()
            soup = BeautifulSoup.BeautifulSoup(data1)

        if not soup:
            return None
        result = {}

        #lets try to get the name
        try:
            profile = soup.find('div', {'id': 'profile'})
            info = profile.find('div', {'class': 'info'})
            result['title'] = String.StripDiacritics(info.h1.string).strip()
        except:
            print "Failed to parse title"

        #lets try to get the origin and year
        try:
            profile = soup.find('div', {'id': 'profile'})
            info = profile.find('div', {'class': 'info'})
            origin = info.find('p', {'class': 'origin'})
            if origin == None or origin.string == None:
                pass
            else:
                result['origin'] = String.StripDiacritics(origin.string)
                m = re.search("([12][0-9]\d\d)", result['origin'].replace(',', ' '))
                if m:
                    result['year'] = m.group(1)
                m = re.search(re_duration, result['origin'].replace(',', ' '))
                if m:
                    result['duration'] = m.group(1)

        except:
            print "Failed to get origin"

        #lets get rating
        try:
            rating = soup.find('div', {'id': 'rating'})
            if rating == None or rating.h2 == None or rating.h2.string == None:
                pass
            else:
                result['rating'] = String.StripDiacritics(rating.h2.string)[:-1] # take out the percent symbol
        except:
            print "Failed to get rating"

        #lets get votes
        try:
            ratings = soup.find('div', {'id': 'ratings'})
            votes = ratings.find('div', {'id': 'count'})
            if votes == None or votes.string == None:
                pass
            else:
                votes_string = votes.string.replace('&nsbp', '').replace(' ', '').replace('(', '').replace(')', '')
                result['votes'] = int(votes_string)
        except:
            print "Failed to get votes"

        #lets get summary
        # //*[@id="plots"]/div[2]/ul/li/div[2]/text()[1]
        try:
            plots = soup.find('div', {'id': 'plots'})
            content = plots.find('div', {'class': 'content'})
            if content == None:
                pass
            else:
                result['summary'] = String.StripDiacritics(content.ul.li.div.text.replace('&nbsp', ''))
        except:
            print "Failed to get plot"

        #lets get the genres
        try:
            profile = soup.find('div', {'id': 'profile'})
            info = profile.find('div', {'class': 'info'})
            genres = info.find('p', {'class': 'genre'}).string.split('/')
            result['genres'] = []
            for genre in genres:
                genre = genre.strip()
                result['genres'].append(genre)
        except:
            print "Failed to get genres"

        #lets get the writers, actors, and other
        try:
            profile = soup.find('div', {'id': 'profile'})
            info = profile.find('div', {'class': 'info'})
            for div in info.findAll('div'):
                section = String.StripDiacritics(div.h4.string).lower()[:-1]
                if section == 'rezie':
                    #directors
                    result['directors'] = []
                    for director in div.span.text.split(','):
                        result['directors'].append(String.StripDiacritics(director).strip())
                elif section == 'hraji':
                    #actors
                    result['actors'] = []
                    for actor in div.span.text.split(','):
                        result['actors'].append(String.StripDiacritics(actor).strip())
                elif section == 'hudba':
                    #music
                    result['music'] = []
                    for musician in div.span.text.split(','):
                        result['music'].append(String.StripDiacritics(musician).strip())
        except:
            print "Failed to get actors"

        #lets try to get the images
        try:
            #find out if we have images
            photos = soup.find('li', {'class': 'photos'})
            if photos == None:
                pass
            else:
                photos_link = photos.a.get('href')
                #lets get this page
                conn.request("GET", photos_link, {}, {'Referer': search_url})
                r2 = conn.getresponse()
                data2 = r2.read()
                soup2 = BeautifulSoup.BeautifulSoup(data2)
                result['artwork'] = []
                for photo in soup2.findAll('div', {'class': 'photo'}):
                    for x, y in photo.attrs:
                        z = x + " " + y
                        m = re.search(re_photo, z)
                        if m:
                            result['artwork'].append("http://img.csfd.cz" + m.group(1))
        except:
            print "Failed to get artwork"

        #lets try to pull some poster
        try:
            profile = soup.find('div', {'id': 'profile'})
            poster = profile.find('div', {'class': 'image'})
            result['poster'] = String.StripDiacritics(poster.img['src'])
        except:
            print "Failed to get poster"

        #results.Append(MetadataSearchResult(id="csfd_id:" + csfd_id, name=csfd_name, year=2000, score=100,lang = Locale.Language.English))
        return result

    def update(self, metadata, media, lang):
        movie_info = self.get_movie_info(metadata.id)
        if movie_info!=None:
            print movie_info
            proxy = Proxy.Preview
            if 'title' in movie_info:
                metadata.title=movie_info['title']
            if 'year' in movie_info:
                metadata.year=int(movie_info['year'])
            if 'rating' in movie_info:
                metadata.rating=float(movie_info['rating'])
            if 'summary' in movie_info:
                metadata.summary=movie_info['summary']
            if 'genres' in movie_info:
                metadata.genres.clear()
                for genre in movie_info['genres']:
                    metadata.genres.add(genre)
            if 'duration' in movie_info:
                metadata.duration=int(movie_info['duration'])*60*1000
            if 'actors' in movie_info:
                metadata.roles.clear()
                for actor in movie_info['actors']:
                    role=metadata.roles.new()
                    role.actor=actor
            if 'directors' in movie_info:
                metadata.directors.clear()
                for director in movie_info['directors']:
                    metadata.directors.add(director)
            if 'music' in movie_info:
                pass
            if 'artwork' in movie_info:
                for url in movie_info['artwork']:
                    art = HTTP.Request(url)
                    metadata.art[url] = proxy(art, sort_order = 1)
                    print "added artwork " + url
            if 'poster' in movie_info:
                url=movie_info['poster']
                print "Added poster " + url
                art=HTTP.Request(url)
                metadata.posters[url]=proxy(art,sort_order=1)

    def search(self, results, media, lang, manual=False):
        print "Calling search"
        d = self.name_to_url(media.name)
        if d != None:
            print d
            if -d['score']<0.1:
                results.Append(MetadataSearchResult(id=d['csfdid'], name=d['name'], year=d['year'], score=90,
                    lang=Locale.Language.English))
            else:
                print "->skipping"
        return


def safe_unicode(s, encoding='utf-8'):
    if s is None:
        return None
    if isinstance(s, basestring):
        if isinstance(s, types.UnicodeType):
            return s
        else:
            return s.decode(encoding)
    else:
        return str(s).decode(encoding)


def fix_title(s):
    delimiters = (".", ",", " ", "_", "-")
    for delimiter in delimiters:
        s = s.replace(delimiter, '+')
    replaces = [('Directors+Cut', '')]
    for r, b in replaces:
        s = s.replace(r, b)
    year = None
    for re_year in re_years:
        m = re.search(re_year, s)
        if m:
            year = m.group(1)
    s = s.split('+')
    stops = (
        'AC3', 'ac3', 'DVDRiP', 'dvd', 'dvdrip', 'xvid', 'divx', 'REPACK', 'RECUT', 'EXTENDED', 'Limited', 'RETAIL',
        'RETAiL', 'screener', 'r5', 'proper', 'nfo', 'ws', '1080p', '720p', 'hdtv', 'avi', 'AVI', 'Avi', 'mkv', 'MKV',
        'Mkv')
    removes = ('Disney', 'Disneys', 'Platinum', 'Edition', 'iTALiAN', 'REMASTERED','cast','Cast')
    output = []
    for tok in s:
        m_stop = None
        for stop in stops:
            m_stop = re.match(stop, tok, flags=re.I)
            if m_stop:
                break
        m_remove = None
        for remove in removes:
            m_remove = re.match(remove, tok)
            if m_remove:
                break
        if not m_stop:
            if not m_remove:
                output += [tok]
        else:
            break
    if year == None:
        return  " ".join(output).strip(), year
    else:
        return " ".join(output).replace(year, '').strip(), year


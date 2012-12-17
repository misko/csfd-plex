import datetime, re, time, unicodedata, hashlib, urlparse, types, urllib, httplib
import BeautifulSoup

re_years = ("^(19\d\d)[+]", "^(20\d\d)[+]", "[+](19\d\d)$", "[+](20\d\d)$", "[+](19\d\d)[+]", "[+](20\d\d)[+]")
re_csfdid = ("^/film/(\d+)\S+")


def Start():
    HTTP.CacheTime = CACHE_1HOUR * 4


class CSFDAgent(Agent.Movies):
    name = 'CSFD'
    languages = [Locale.Language.English, Locale.Language.Swedish, Locale.Language.French,
                 Locale.Language.Spanish, Locale.Language.Dutch, Locale.Language.German,
                 Locale.Language.Italian, Locale.Language.Danish]

    def identifierize(self, string):
        string = re.sub(r"\s+", " ", string.strip())
        string = unicodedata.normalize('NFKD', safe_unicode(string))
        string = re.sub(r"['\"!?@#$&%^*\(\)_+\.,;:/]", "", string)
        string = re.sub(r"[_ ]+", "_", string)
        string = string.strip('_')
        return string.strip().lower()

    def search(self, results, media, lang, manual=False):
        media.name = String.StripDiacritics(media.name)
        print media.name
        print self.identifierize(media.name)
        print media.year
        name, year = fix_title(String.StripDiacritics(media.name))
        print name, year, " xxc"
        search_url = "/hledat/?q=" + String.Quote(name)
        print name, year, " xxf"
        conn = httplib.HTTPConnection("www.csfd.cz")

        conn.request("GET", search_url)
        print "#" + search_url
        r1 = conn.getresponse()
        #print r1
        #print r1.read()
        data1 = r1.read()
        local_results = []

        if r1.status not in (301, 302):
            print "making soup"
            soup = BeautifulSoup.BeautifulSoup(data1)
            print "done soup"
            search_films = soup.find(id="search-films")
            #<ul class="ui-image-list js-odd-even">
            n = 3
            top_results_soup = search_films.find("ul", {'class': "ui-image-list js-odd-even"})
            print "TOP RESULTS"
            if top_results_soup != None:
                top_results = top_results_soup.findAll('li')
                for top_result in top_results:
                    #link to title
                    link = top_result.h3.a
                    path = link.get('href')
                    candidate_name = String.StripDiacritics(link.string)
                    yearx = top_result.p.string[-4:]
                    #score = score_strs(name, lookup_name)
                    score = -Util.LevenshteinDistance(name, candidate_name)
                    if yearx.find(year) >= 0:
                        score += 0.5
                    score += 0.001 * n
                    if n > 0:
                        n = n - 1
                    local_results.append([score, name, path, yearx, link.string])
            other_results_soup = search_films.find("ul", {'class': "films others"})
            print "REST RESULTS"
            #print other_results_soup
            if other_results_soup != None:
                other_results = other_results_soup.findAll('li')
                for result in other_results:
                    link = result.a
                    path = link.get('href')
                    candiate_name = String.StripDiacritics(link.string)
                    yearx_r = result.find("span", {"class": "film-year"})
                    yearx = "-1"
                    if yearx_r != None:
                        yearx = yearx_r.string
                        if yearx[-1] == ')':
                            yearx = yearx[:-1]
                        if yearx[0] == '(':
                            yearx = yearx[1:]
                    score = -Util.LevenshteinDistance(name, candidate_name)
                    if yearx.find(year) >= 0:
                        score += 0.5
                    score += 0.001 * n
                    if n > 0:
                        n = n - 1
                    local_results.append([score, name, path, yearx, link.string])
                    #print top_results_soup
            local_results.sort(reverse=True)

            if len(local_results) == 0:
                Log("Failed to find any results for " + name)
                return
            local_result = local_results[0]
        else:
            local_result = [1, name, r1.getheader('location', '').replace('http://www.csfd.cz', ''), year, name]
        print "GETTING NEXT", local_result
        conn.request("GET", local_result[2], {}, {'Referer': "http://www.csfd.cz" + search_url})
        print "#" + local_result[2]
        m = re.match(re_csfdid, local_result[2])
        if m == None:
            return
        csfd_id = m.group(1)
        r1 = conn.getresponse()
        data1 = r1.read()
        soup = BeautifulSoup.BeautifulSoup(data1)
        if soup.h1.text.lower() == "redirect":
            l = soup.p.a['href'].replace('http://www.csfd.cz', '')
            conn.request("GET", l, {}, {'Referer': local_result[2]})
            print "#" + l
            r1 = conn.getresponse()
            data1 = r1.read()
            soup = BeautifulSoup.BeautifulSoup(data1)

        csfd_name = "?"
        csfd_genre = "?"
        csfd_origin = "?"
        csfd_rating = "?"
        csfd_name = String.StripDiacritics(local_result[4].string)
        #print soup
        try:
            profile = soup.find('div', {'id': 'profile'})
            info = profile.find('div', {'class': 'info'})
            genre = info.find('p', {'class': 'genre'})
        except:
            return

        #try to get the type
        csfd_type = "Movie"
        try:
            ty = info.find('span', {'class': 'film-type'})
            csfd_type = String.StripDiacritics(ty.text)
        except:
            pass
        if genre == None or genre.string == None:
            pass
        else:
            csfd_genre = String.StripDiacritics(genre.string)
        origin = info.find('p', {'class': 'origin'})
        if origin == None or origin.string == None:
            pass
        else:
            csfd_origin = String.StripDiacritics(origin.string)
        rating = soup.find('div', {'id': 'rating'})
        if rating == None or rating.h2 == None or rating.h2.string == None:
            pass
        else:
            csfd_rating = String.StripDiacritics(rating.h2.string)
        print csfd_name, csfd_genre, csfd_rating, local_result[3]
        results.Append(MetadataSearchResult(id="csfd_id:" + csfd_id, name=csfd_name, year=2000, score=100,
            lang=Locale.Language.English))
        print csfd_name, csfd_genre, csfd_rating

    def update(self, metadata, media, lang):
        print "UPDATE CLALLED!"
        print metadata.id
        print metadata.id
        conn = httplib.HTTPConnection("www.csfd.cz")
        print metadata.id
        request_url = "/film/" + metadata.id[8:]
        print metadata.id
        conn.request("GET", request_url)
        print metadata.id
        r1 = conn.getresponse()
        print metadata.id + " " + request_url
        data1 = r1.read()
        soup = BeautifulSoup.BeautifulSoup(data1)
        if soup.h1.text.lower() == "redirect":
            l = soup.p.a['href'].replace('http://www.csfd.cz', '')
            conn.request("GET", l, {}, {'Referer': request_url})
            print "#" + l
            r1 = conn.getresponse()
            data1 = r1.read()
            soup = BeautifulSoup.BeautifulSoup(data1)

        print metadata.id + " XX"
        csfd_name = "?"
        csfd_genre = "?"
        csfd_origin = "?"
        csfd_rating = "?"
        csfd_name = "?"
        csfd_year = "?"
        csfd_poster_link = "?"
        #print soup
        try:
            profile = soup.find('div', {'id': 'profile'})
            info = profile.find('div', {'class': 'info'})
            genre = info.find('p', {'class': 'genre'})
            poster = profile.find('div', {'class': 'image'})
        except:
            return

        try:
            csfd_name = String.StripDiacritics(info.h1.string).strip()
            print csfd_name
        except:
            pass
        try:
            print poster
            print poster.img
            print poster.img['src']
            csfd_poster_link = String.StripDiacritics(poster.img['src'])
            print csfd_poster_link
        except:
            pass

        #try to get the type
        csfd_type = "Movie"
        try:
            ty = info.find('span', {'class': 'film-type'})
            csfd_type = String.StripDiacritics(ty.text)
        except:
            pass
        if genre == None or genre.string == None:
            pass
        else:
            csfd_genre = String.StripDiacritics(genre.string)
        origin = info.find('p', {'class': 'origin'})
        if origin == None or origin.string == None:
            pass
        else:
            csfd_origin = String.StripDiacritics(origin.string)
            m=re.search("([12][0-9]\d\d)",csfd_origin.replace(',',' '))
            if m:
                print "FOUND"
                csfd_year=m.group(1)
        rating = soup.find('div', {'id': 'rating'})
        if rating == None or rating.h2 == None or rating.h2.string == None:
            pass
        else:
            csfd_rating = String.StripDiacritics(rating.h2.string)
        print csfd_name, csfd_genre, csfd_rating
        metadata.title = "found: " + csfd_name
        metadata.year = int(csfd_year)
        metadata.rating = float(csfd_rating)
        metadata.summary = "HAPPEND"
        print csfd_name, csfd_genre, csfd_rating
        metadata.genres.add("comedy")
        print csfd_poster_link
        art = HTTP.Request(csfd_poster_link)
        print csfd_name, csfd_genre, csfd_rating
        proxy = Proxy.Preview
        metadata.posters[csfd_poster_link] = proxy(art, sort_order=1)
        print csfd_name, csfd_genre, csfd_rating


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
    removes = ('Disney', 'Disneys', 'Platinum', 'Edition', 'iTALiAN', 'REMASTERED')
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
    return " ".join(output).replace(year, '').strip(), year


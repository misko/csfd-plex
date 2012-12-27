import datetime, re, time, unicodedata, hashlib, urlparse, types, urllib, httplib

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

    def name_to_url(self, search_name, original_name=None, depth=0):
        norm_name, year = fix_title(String.StripDiacritics(search_name))
        if original_name==None:
            original_name=norm_name
        print norm_name ,year
        #lets remove the sequel number from the norm_name
        search_name_x = norm_name.split()
        search_name = ""
        for k in search_name_x:
            if k in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
                pass
            else:
                search_name += " "+k
        search_url = "http://www.csfd.cz/hledat/?q=" + String.Quote(search_name)
        try:
            print "fetching " + search_url
            data=HTTP.Request(search_url)
            print data.headers
            #data.headers
        except:
            print "Failed to get page"

        h=HTML.ElementFromString(data)

        #lets try to figure out what the result is
        local_results = []


        #try to get the name if we can then got redirected!
        if depth==0:
            try:
                title=String.StripDiacritics(h.xpath('//div[@id="profile"]//div[@class="info"]//h1')[0].text_content()).strip()
                new_result = self.name_to_url(title + " " + original_name, original_name=original_name, depth=1)
                if new_result != None:
                    local_results.append([new_result['score'], new_result])
            except:
                pass


        n =3
        try:
            for x in h.xpath('//div[@id="search-films"]//ul[@class="ui-image-list js-odd-even"]/li'):
                #print "found"
                x_link = x.xpath('.//a[contains(@class,"film")]')[0]
                link = x_link.get('href')
                candidate_name=String.StripDiacritics(x_link.text)
                x_details = x.xpath('.//p')[0]
                details=String.StripDiacritics(x_details.text)
                yearx = details[-4:]
                #score = score_strs(name, lookup_name)
                dist=Util.LevenshteinDistance(original_name.lower(), candidate_name)
                lcs = len(Util.LongestCommonSubstring(original_name.lower(), candidate_name))
                score = -dist / float(len(original_name)) + 3*lcs/float(len(search_name))
                if year != None and yearx.find(year) >= 0:
                    score += 0.5
                score += 0.001 * n
                if n > 0:
                    n = n - 1
                local_results.append(
                    [score,
                     {'search_url': search_url, 'score': score, 'candidate_name': candidate_name, 'link': link,
                      'year': yearx, 'dist': dist, 'lcs':lcs}])
                #print x.text_content(),x_link.text_content(),candidate_name
            for x in h.xpath('//div[@id="search-films"]//ul[@class="films others"]/li'):
                #print x.text_content(),candidate_name
                x_link = x.xpath('.//a[contains(@class,"film")]')[0]
                link = x_link.get('href')
                candidate_name=String.StripDiacritics(x_link.text)
                x_span=x.xpath('.//span[@class="film-year"]')[0]
                yearx=x_span.text
                if yearx[-1] == ')':
                    yearx = yearx[:-1]
                if yearx[0] == '(':
                    yearx = yearx[1:]
                dist=Util.LevenshteinDistance(original_name.lower(), candidate_name)
                lcs = len(Util.LongestCommonSubstring(original_name.lower(), candidate_name))
                score = -dist / float(len(original_name)) + 3*lcs/float(len(search_name))
                if year != None and yearx.find(year) >= 0:
                    score += 0.5
                score += 0.001 * n
                if n > 0:
                    n = n - 1
                local_results.append(
                    [score, {'search_url': search_url, 'candidate_name': candidate_name, 'link': link,
                             'year': yearx, 'score':score, 'dist': dist, 'lcs':lcs}])
        except:
            print "Got exception on lookup!"
        local_results.sort(reverse=True)
        #print local_results
        if len(local_results) == 0:
            Log("Failed to find any results for " + norm_name)
            return None


        local_results.sort(reverse=True)
        #print local_results
        local_result = local_results[0][1]
        m = re.match(re_csfdid, local_result['link'])
        if m != None:
            local_result['csfdid'] = "csfd:" + m.group(1)
        else:
            local_result['csfdid'] = "csfd:-1"
        local_result['name'] = norm_name
        return local_result

    def get_movie_info(self, csfdid):
        #norm_name, year = fix_title(String.StripDiacritics(name))
        print csfdid[5:]
        request_url="http://www.csfd.cz/film/" + csfdid[5:]
        data=HTTP.Request(request_url).content

        h=HTML.ElementFromString(data)
        result = {}

        #lets try to get the name
        try:
            result['title']=String.StripDiacritics(h.xpath('//div[@id="profile"]//div[@class="info"]//h1')[0].text_content()).strip()
        except:
            print "Failed to parse title"

        #lets try to get the origin and year
        try:

            origin=h.xpath('//div[@id="profile"]//div[@class="content"]//div[@class="info"]//p[@class="origin"]')[0].text
            if origin == None:
                pass
            else:
                result['origin'] = String.StripDiacritics(origin)
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
            rating = h.xpath('//div[@id="rating"]//h2')[0].text
            if rating == None:
                pass
            else:
                result['rating'] = String.StripDiacritics(rating)[:-1] # take out the percent symbol
        except:
            print "Failed to get rating"

        #lets get votes
        try:
            votes=h.xpath('//div[@id="ratings"]//div[@class="count"]')[0].text_content().split('(')[1].split(')')[0]
            if votes == None:
                pass
            else:
                votes_string = "".join(votes.replace('&nsbp', '').split())
                result['votes'] = int(votes_string)
        except:
            print "Failed to get votes"

        #lets get summary
        # //*[@id="plots"]/div[2]/ul/li/div[2]/text()[1]
        try:
            plot=h.xpath('//div[@id="plots"]//div[@class="content"]//div')[0].text_content()
            if plot == None:
                pass
            else:
                result['summary'] = String.StripDiacritics(plot.replace('&nbsp', '')).strip()
        except:
            print "Failed to get plot"

        #lets get the genres
        try:
            genres=String.StripDiacritics(h.xpath('//div[@id="profile"]//div[@class="info"]//p[@class="genre"]')[0].text_content()).split('/')
            result['genres'] = []
            for genre in genres:
                genre = genre.strip()
                result['genres'].append(genre)
        except:
            print "Failed to get genres"

        #lets get the writers, actors, and other
        try:
            for x in h.xpath('//div[@id="profile"]//div[@class="info"]//div'):
                #print x.text_content()
                section=String.StripDiacritics(x.xpath('.//h4')[0].text_content()).strip().lower()[:-1]
                text=String.StripDiacritics(x.xpath('.//span')[0].text_content().strip())
                if section == 'rezie':
                    #directors
                    result['directors'] = []
                    for director in text.split(','):
                        result['directors'].append(String.StripDiacritics(director).strip())
                elif section == 'hraji':
                    #actors
                    result['actors'] = []
                    for actor in text.split(','):
                        result['actors'].append(String.StripDiacritics(actor).strip())
                elif section == 'hudba':
                    #music
                    result['music'] = []
                    for musician in text.split(','):
                        result['music'].append(String.StripDiacritics(musician).strip())
        except:
            print "Failed to get actors"

        #lets try to get the images
        try:
            #find out if we have images
            photos_link="http://www.csfd.cz/"+h.xpath('//li[@class="photos"]//a')[0].get('href')
            #lets get this page
            print photos_link
            data2=HTTP.Request(photos_link,headers={'Referer':request_url}).content
            print photos_link
            h2=HTML.ElementFromString(data2)
            result['artwork'] = []
            print "what"
            for photo in h2.xpath('//div[@class="photo"]'):
                z=""
                for x,y in photo.items():
                    z+=(x+y)
                m=re.search(re_photo,z)
                if m:
                    if 'artwork' not in result:
                        result['artwork']=[]
                    result['artwork'].append("http://img.csfd.cz"+m.group(1))
        except:
            print "Failed to get artwork"

        #lets try to pull some poster
        try:
            result['poster']=h.xpath('//div[@id="profile"]//div[@class="image"]//img')[0].get('src')
        except:
            print "Failed to get poster"

        return result

    def update(self, metadata, media, lang):
        print "Calling update"
        movie_info = self.get_movie_info(metadata.id)
        if movie_info != None:
            print movie_info
            proxy = Proxy.Preview
            if 'title' in movie_info:
                metadata.title = movie_info['title']
            if 'year' in movie_info:
                metadata.year = int(movie_info['year'])
            if 'rating' in movie_info:
                metadata.rating = float(movie_info['rating'])
            if 'summary' in movie_info:
                metadata.summary = movie_info['summary']
            if 'genres' in movie_info:
                metadata.genres.clear()
                for genre in movie_info['genres']:
                    metadata.genres.add(genre)
            if 'duration' in movie_info:
                metadata.duration = int(movie_info['duration']) * 60 * 1000
            if 'actors' in movie_info:
                metadata.roles.clear()
                for actor in movie_info['actors']:
                    role = metadata.roles.new()
                    role.actor = actor
            if 'directors' in movie_info:
                metadata.directors.clear()
                for director in movie_info['directors']:
                    metadata.directors.add(director)
            if 'music' in movie_info:
                pass
            if 'artwork' in movie_info:
                for url in movie_info['artwork']:
                    art = HTTP.Request(url)
                    metadata.art[url] = proxy(art, sort_order=1)
                    print "added artwork " + url
            if 'poster' in movie_info:
                url = movie_info['poster']
                print "Added poster " + url
                art = HTTP.Request(url)
                metadata.posters[url] = proxy(art, sort_order=1)

    def search(self, results, media, lang, manual=False):
        print "Calling search"
        d = self.name_to_url(media.name)
        if d != None:
            print d
            if -d['score'] < 0.3:
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
        'Mkv','HDTV')
    removes = (
    'Disney', 'Disneys', 'Platinum', 'Edition', 'iTALiAN', 'REMASTERED', 'cast', 'Cast', 'kinobox', 'Kinobox','Drama','drama','cz','Cz','CZ','cZ')
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
    title = ""
    if year == None:
        title = " ".join(output).strip()
    else:
        title = " ".join(output).replace(year, '').strip()
    title = title.lower()
    title.replace('iii', '3')
    title.replace('ii', '2')
    title.replace('iv', '4')
    return title, year
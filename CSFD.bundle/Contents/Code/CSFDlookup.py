import unicodedata, re, urllib, sys, os
from lxml import html

Quote = urllib.quote

re_years = (
    "^(19\d\d)[+]", "^(20\d\d)[+]", "[+](19\d\d)$", "[+](20\d\d)$", "[+](19\d\d)[+]", "[+](20\d\d)[+]", "\[([12]\d\d\d)\]","\(([12]\d\d\d)\)")
re_csfdid = ("^/film/(\d+)\S+")
re_duration = ("([0-9]+)\s+min")
re_photo = ("(/photos/filmy/\S+.jpg)")
re_csfd_title_tag = ("(\([^)]*\))")

def get_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

# From http://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Longest_common_substring#Python
def longest_common_substring(first, second):
    S = first
    T = second

    m = len(S);
    n = len(T)
    L = [[0] * (n + 1) for i in xrange(m + 1)]
    LCS = set()
    longest = 0
    for i in xrange(m):
        for j in xrange(n):
            if S[i] == T[j]:
                v = L[i][j] + 1
                L[i + 1][j + 1] = v
                if v > longest:
                    longest = v
                    LCS = set()
                if v == longest:
                    LCS.add(S[i - v + 1:i + 1])
    if len(LCS) > 0:
        return LCS.pop()
    return ''


def request(page):
    p = urllib.urlopen(page)
    return p.read()


#from plex
def StripDiacritics(s):
    """
      Removes diacritics from a given string.
    """
    u = unicode(s).replace(u"\u00df", u"ss").replace(u"\u1e9e", u"SS")
    nkfd_form = unicodedata.normalize('NFKD', u)
    only_ascii = nkfd_form.encode('ASCII', 'ignore')
    return only_ascii


def to_xpath(data):
    return html.fromstring(data)


# TODO: Attribution http://www.korokithakis.net/node/87
def levenshtein_distance(first, second):
    if len(first) > len(second):
        first, second = second, first
    if len(second) == 0:
        return len(first)
    first_length = len(first) + 1
    second_length = len(second) + 1
    distance_matrix = [[0] * second_length for x in range(first_length)]
    for i in range(first_length):
        distance_matrix[i][0] = i
    for j in range(second_length):
        distance_matrix[0][j] = j
    for i in xrange(1, first_length):
        for j in range(1, second_length):
            deletion = distance_matrix[i - 1][j] + 1
            insertion = distance_matrix[i][j - 1] + 1
            substitution = distance_matrix[i - 1][j - 1]
            if first[i - 1] != second[j - 1]:
                substitution = substitution + 1
            distance_matrix[i][j] = min(insertion, deletion, substitution)
    return distance_matrix[first_length - 1][second_length - 1]


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
        'RETAiL', 'screener', 'r5', 'proper', 'nfo', 'ws', '1080p', '720p', '480p','560p', 'hdtv', 'avi', 'AVI', 'Avi', 'mkv', 'MKV',
        'Mkv', 'HDTV')
    removes = (
        'Disney', 'Disneys', 'Platinum', 'Edition', 'iTALiAN', 'REMASTERED', 'cast', 'Cast', 'kinobox', 'Kinobox',
        'Drama', 'drama', 'cz', 'Cz', 'CZ', 'cZ')
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


def name_to_url(search_name, filename, original_name=None, depth=0):
    norm_name, year = fix_title(StripDiacritics(search_name))
    if filename != None:
        #print "FN:" + filename
        file_name, file_year = fix_title(StripDiacritics(filename))
        if year == None:
            year = file_year
    if original_name == None:
        original_name = norm_name
    print >> sys.stderr, norm_name, year
    #lets remove the sequel number from the norm_name
    search_name_x = norm_name.split()
    search_name = ""
    for k in search_name_x:
        if k in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
            pass
        else:
            search_name += " " + k
    search_name = " ".join(search_name.strip().split())
    search_url = "http://www.csfd.cz/hledat/?q=" + Quote(search_name)
    try:
        print >> sys.stderr, "fetching " + search_url
        data = request(search_url)
        #data.headers
    except:
        print >> sys.stderr, "Failed to get page"

    h = to_xpath(data)

    #lets try to figure out what the result is
    local_results = []


    #try to get the name if we can then got redirected!
    if depth == 0:
        try:
            title = StripDiacritics(h.xpath('//div[@id="profile"]//div[@class="info"]//h1')[0].text_content()).strip()
            new_title=title+" " + original_name
            if year!=None:
                new_title= new_title + " " + year
            new_result = name_to_url(new_title, filename, original_name=original_name, depth=1)
            if new_result != None:
                local_results.append([new_result['score'], new_result])
            else:
                link = h.xpath('//html//head//link[@rel="canonical"]')[0].get('href').replace('http://www.csfd.cz', '')
                local_results.append([1.0, {'search_url': search_url, 'candidate_name': title, 'link': link,
                                            'year': "0", 'score': 1.0, 'dist': len(search_name),
                                            'lcs': len(search_name)}])
        except:
            pass

    n = 3
    #try:
    for x in h.xpath('//div[@id="search-films"]//ul[@class="ui-image-list js-odd-even"]/li'):
        #print "found"
        x_link = x.xpath('.//a[contains(@class,"film")]')[0]
        link = x_link.get('href')
        candidate_name,y = fix_title(StripDiacritics(x_link.text).lower())
        x_alt = x.xpath('.//span[@class="search-name"]')
        if len(x_alt) > 0:
            candidate_name = StripDiacritics(x_alt[0].text.replace('(', '').replace(')', ''))
        x_details = x.xpath('.//p')[0]
        details = StripDiacritics(x_details.text)
        yearx = details[-4:]
        #score = score_strs(name, lookup_name)
        dist = levenshtein_distance(original_name.lower(), candidate_name)
        lcs = len(longest_common_substring(original_name.lower(), candidate_name))
        score = -dist / float(max(len(candidate_name),len(original_name))) + 5 * lcs / float(len(search_name))
        score += 0.001 * n
        if n > 0:
            n = n - 1

        if year != None and yearx.find(year) >= 0:
            score = score
        elif year != None and abs(int(yearx) - int(year)) < 2:
            score = score - 2
        elif year != None:
            score = score - 5
        local_results.append(
            [score,
             {'search_url': search_url, 'score': score, 'candidate_name': candidate_name, 'link': link,
              'year': yearx, 'dist': dist, 'lcs': lcs}])
        #print x.text_content(),x_link.text_content(),candidate_name
        #print local_results[-1]
    for x in h.xpath('//div[@id="search-films"]//ul[@class="films others"]/li'):
        #print x.text_content(),candidate_name
        x_link = x.xpath('.//a[contains(@class,"film")]')[0]
        link = x_link.get('href')
        candidate_name,y = fix_title(StripDiacritics(x_link.text).lower())
        x_alt = x.xpath('.//span[@class="search-name"]')
        if len(x_alt) > 0:
            candidate_name = StripDiacritics(x_alt[0].text.replace('(', '').replace(')', ''))
        try:
            x_span = x.xpath('.//span[@class="film-year"]')[0]
            yearx = x_span.text
            if yearx[-1] == ')':
                yearx = yearx[:-1]
            if yearx[0] == '(':
                yearx = yearx[1:]
        except:
            yearx="0"

        dist = levenshtein_distance(original_name.lower(), candidate_name)
        lcs = len(longest_common_substring(original_name.lower(), candidate_name))
        score = -dist / float(max(len(candidate_name),len(original_name))) + 5 * lcs / float(len(search_name))
        score += 0.001 * n
        if year != None and yearx.find(year) >= 0:
            score = score
        elif year != None and abs(int(yearx) - int(year)) < 2:
            score = score - 2
        elif year != None:
            score = score - 5
        if n > 0:
            n = n - 1
        local_results.append(
            [score, {'search_url': search_url, 'candidate_name': candidate_name, 'link': link,
                     'year': yearx, 'score': score, 'dist': dist, 'lcs': lcs}])
        #except:
    #    print >> sys.stderr, "Got exception on lookup!"

    local_results.sort(reverse=True)
    #print local_results
    if len(local_results) == 0:
        #Log("Failed to find any results for " + norm_name)
        return None

    local_results.sort(reverse=True)

    #for result in local_results[:10]:
    #    print result
    #print local_results
    local_result = local_results[0][1]
    m = re.search(re_csfdid, local_result['link'])
    if m != None:
        local_result['csfdid'] = "csfd:" + m.group(1)
    else:
        local_result['csfdid'] = "csfd:-1"
    local_result['name'] = norm_name
    return local_result


def get_movie_info(csfdid):
    #norm_name, year = fix_title(String.StripDiacritics(name))
    #print csfdid[5:]
    request_url = "http://www.csfd.cz/film/" + csfdid[5:]
    data = request(request_url)

    h = to_xpath(data)
    result = {}

    #lets try to get the name
    try:
        result['title'] = StripDiacritics(
            h.xpath('//div[@id="profile"]//div[@class="info"]//h1')[0].text_content()).strip()
        if "(TV serial)" in result['title']:
            result['type'] = 'TV'
        elif "(TV film)" in result['title']:
            result['type'] = 'TV MOVIE'
        else:
            result['type'] = 'MOVIE'
        m=True
        while m:
            m=re.search(re_csfd_title_tag,result['title'])
            if m:
                result['title']=result['title'].replace(m.group(1),'').strip()
    except:
        print >> sys.stderr, "Failed to parse title"

    #lets try to get the origin and year
    try:
        origin = h.xpath('//div[@id="profile"]//div[@class="content"]//div[@class="info"]//p[@class="origin"]')[0].text
        if origin == None:
            pass
        else:
            result['origin'] = StripDiacritics(origin)
            m = re.search("([12][0-9]\d\d)", result['origin'].replace(',', ' '))
            if m:
                result['year'] = m.group(1)
            m = re.search(re_duration, result['origin'].replace(',', ' '))
            if m:
                result['duration'] = m.group(1)
    except:
        print >> sys.stderr, "Failed to get origin"

    #lets get rating
    try:
        rating = h.xpath('//div[@id="rating"]//h2')[0].text
        if rating == None:
            pass
        else:
            result['rating'] = StripDiacritics(rating)[:-1] # take out the percent symbol
    except:
        print >> sys.stderr, "Failed to get rating"

    #lets get votes
    try:
        votes = h.xpath('//div[@id="ratings"]//div[@class="count"]')[0].text_content().split('(')[1].split(')')[0]
        if votes == None:
            pass
        else:
            votes_string = "".join(votes.replace('&nsbp', '').split())
            result['votes'] = int(votes_string)
    except:
        print >> sys.stderr, "Failed to get votes"

    #lets get summary
    # //*[@id="plots"]/div[2]/ul/li/div[2]/text()[1]
    try:
        plot = h.xpath('//div[@id="plots"]//div[@class="content"]//div')[0].text_content()
        if plot == None:
            pass
        else:
            result['summary'] = StripDiacritics(plot.replace('&nbsp', '')).strip()
    except:
        print >> sys.stderr, "Failed to get plot"

    #lets get the genres
    try:
        genres = StripDiacritics(
            h.xpath('//div[@id="profile"]//div[@class="info"]//p[@class="genre"]')[0].text_content()).split('/')
        result['genres'] = []
        for genre in genres:
            genre = genre.strip()
            result['genres'].append(genre)
    except:
        print >> sys.stderr, "Failed to get genres"

    #lets get the writers, actors, and other
    try:
        for x in h.xpath('//div[@id="profile"]//div[@class="info"]//div'):
            #print x.text_content()
            section = StripDiacritics(x.xpath('.//h4')[0].text_content()).strip().lower()[:-1]
            text = StripDiacritics(x.xpath('.//span')[0].text_content().strip())
            if section == 'rezie':
                #directors
                result['directors'] = []
                for director in text.split(','):
                    result['directors'].append(StripDiacritics(director).strip())
            elif section == 'hraji':
                #actors
                result['actors'] = []
                for actor in text.split(','):
                    result['actors'].append(StripDiacritics(actor).strip())
            elif section == 'hudba':
                #music
                result['music'] = []
                for musician in text.split(','):
                    result['music'].append(StripDiacritics(musician).strip())
    except:
        print >> sys.stderr, "Failed to get actors"


    #lets try to get the images
    try:
        #find out if we have images
        photos_link = request_url + "/galerie/"
        #lets get this page
        #print photos_link
        data2 = request(photos_link)
        #print photos_link
        h2 = to_xpath(data2)
        result['artwork'] = []
        for photo in h2.xpath('//div[@class="photo"]'):
            z = ""
            for x, y in photo.items():
                z += (x + y)
            m = re.search(re_photo, z)
            if m:
                if 'artwork' not in result:
                    result['artwork'] = []
                result['artwork'].append("http://img.csfd.cz" + m.group(1))
    except:
        print >> sys.stderr, "Failed to get artwork"

    #lets try to pull some poster
    try:
        result['poster'] = h.xpath('//div[@id="profile"]//div[@class="image"]//img')[0].get('src')
    except:
        print >> sys.stderr, "Failed to get poster"

    return result


def usage():
    print "%s options" % sys.argv[0]
    print "-f filename - if provided without title will try to extract title from this"
    print "-t title - used to search csfd, if year is in title script will try to extract it"
    print "-y year - the year of the release, preferably within 1 year of what is says on csfd"
    print "-m movies_root - if provided with filename and the result of lookup is movie, print mkdir and mv commands"
    print "-v tv_root - if provided with filename and the result of lookup is tv, print mkdir and mv commands"
    print "-x - print output in xls format"
    print "* at least, filename or title must be provided"
    print "examples:"
    print "%s -t 'Dedictvi aneb Kurvahosigutntag'" % sys.argv[0]
    print "%s -f 'Dedictvi_aneb_Kurvahosigutntag.mkv'" % sys.argv[0]
    print "%s -f 'Dedictvi_aneb Kurvahosigutntag_1992.mkv'" % sys.argv[0]
    print "%s -f 'Dedictvi_aneb Kurvahosigutntag.mkv' -y 1992" % sys.argv[0]
    sys.exit(1)

if __name__ == '__main__':
    title = ""
    filename = ""
    year = ""
    root_movies = ""
    root_tv = ""
    xls=False
    x = 1
    while x < len(sys.argv):
        if sys.argv[x] in "-f":
            filename = sys.argv[x + 1].decode("utf-8")
            x = x + 2
        elif sys.argv[x] in "-y":
            year = sys.argv[x + 1].decode("utf-8")
            x = x + 2
        elif sys.argv[x] in "-t":
            title = sys.argv[x + 1].decode("utf-8")
            x = x + 2
        elif sys.argv[x] in "-m":
            root_movies = sys.argv[x + 1].decode("utf-8")
            x = x + 2
        elif sys.argv[x] in "-v":
            root_tv = sys.argv[x + 1].decode("utf-8")
            x = x + 2
        elif sys.argv[x].lower() in ("-h", "--help"):
            usage()
        elif sys.argv[x].lower() in ('-x'):
            xls=True
            x = x + 1
        else:
            x = x + 1
    if (title != "" or filename != ""):
        #print "We can run",title,filename,year
        if title == "":
            title = filename
        if year != None:
            title = title + " " + year
        title = StripDiacritics(title)
        print >> sys.stderr, title, year

        original_filename=filename
        x_filename = os.path.basename(urllib.unquote(filename))
        if x_filename.lower() == "video_ts.ifo" or x_filename.lower() == "video_ts":
            unquoted=StripDiacritics(urllib.unquote(filename))
            x_filename = unquoted.split(os.path.sep)[-3]
        filename=x_filename

        d = name_to_url(title, filename)
        if d:
            #print d
            if -d['score'] < 0.3:
                x = get_movie_info(d['csfdid'])
                if xls:
                    output_string=""
                    #first lets get the title
                    if 'title' in x:
                        output_string+=x['title']+"\t"
                    else:
                        output_string+="\t"
                    #lets get the origin
                    if 'origin' in x:
                        output_string+=x['origin'].split(',')[0]+"\t"
                    else:
                        output_string+="\t"
                    #lets include the genre
                    if 'genres' in x:
                        output_string+=",".join(x['genres'])+"\t"
                    else:
                        output_string+="\t"
                    #lest get the year
                    if 'year' in x:
                        output_string+=x['year']+"\t"
                    else:
                        output_string+="\t"
                    #lets include the rating
                    if 'rating' in x:
                        output_string+=x['rating']+"\t"
                    else:
                        output_string+="\t"
                    #lets include the type
                    if 'type' in x:
                        output_string+=x['type']+"\t"
                    else:
                        output_string+="\t"
                    #lets include the filename
                    if original_filename!="":
                        mbytes=get_size(start_path=original_filename)/(1024*1024)
                        output_string+=original_filename+"\t"+str(mbytes)+"\t"
                    else:
                        output_string+="\t\t"
                    print output_string
                else:
                    print "#" + str(x)
                    root = ""
                    if x['type'] == "MOVIE" or x['type']=="TV MOVIE":
                        root = root_movies
                    else:
                        root = root_tv
                    if filename != "" and root != "":
                        try:
                            dest_folder = ""
                            if x['type'] == "MOVIE" or x['type']=="TV MOVIE":
                                dest_folder = root + "/" + str(x['year']) + "/" + str(x['title']) + "/"
                            else:
                                dest_folder = root + "/" + str(x['title']) + "/"
                            print "mkdir -p \'" + dest_folder + "\'"
                            print "mv -v \'" + filename + "\' \'" + dest_folder + "\'"
                        except:
                            pass
            else:
                #print "did not find a good match"
                pass

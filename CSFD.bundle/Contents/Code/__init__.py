# Moviepilot metadata agent for Plex
# Adds German titles, summaries and posters from www.moviepilot.de to movies

import htmlentitydefs, re

BASE_URL            = 'http://www.moviepilot.de'
API_KEY             = '734xthw33clipcnv6nqdtnq3em3rmj'
MOVIE_INFO_BY_IMDB  = '%s/movies/imdb-id-%%s.json?api_key=%s' % (BASE_URL, API_KEY)
MOVIE_INFO_BY_TITLE = '%s/movies/%%s.json?api_key=%s' % (BASE_URL, API_KEY)
CAST_INFO_BY_IMDB   = '%s/movies/imdb-id-%%s/casts.json?api_key=%s' % (BASE_URL, API_KEY)

def Start():
  HTTP.CacheTime = CACHE_1DAY
  HTTP.Headers['User-Agent'] = 'Plex/Nine'


##
# Removes HTML or XML character references and entities from a text string.
# http://effbot.org/zone/re-sub.htm#unescape-html
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.

def unescape(text):
  def fixup(m):
    text = m.group(0)
    if text[:2] == "&#":
      # character reference
      try:
        if text[:3] == "&#x":
          return unichr(int(text[3:-1], 16))
        else:
          return unichr(int(text[2:-1]))
      except ValueError:
        pass
    else:
      # named entity
      try:
        text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
      except KeyError:
        pass
    return text # leave as is
  return re.sub("&#?\w+;", fixup, text)


class MoviepilotAgent(Agent.Movies):
  name = 'Moviepilot'
  languages = ['de']
  primary_provider = False
  contributes_to = ['com.plexapp.agents.imdb']

  def search(self, results, media, lang):
    # Use the IMDB id found by the primary metadata agent (IMDB/Freebase)
    results.Append(MetadataSearchResult(id=media.primary_metadata.id.lstrip('t0'), score=100))

  def update(self, metadata, media, lang):
    # Only use data from Moviepilot if the user has set the language for this section to German (Deutsch)
    if lang == 'de':
      try:
        movie = JSON.ObjectFromURL(MOVIE_INFO_BY_IMDB % (metadata.id))

        metadata.title = ''
        if Prefs['title']:
          title = movie['display_title'].replace('&#38;', '&').replace('&amp;', '&')
          metadata.title = unescape(title)

        if movie['production_year'] and str(movie['production_year']).strip() != '':
          metadata.year = int(movie['production_year'])

        metadata.summary = ''
        if Prefs['summary']:
          summary = movie['short_description']
          summary = re.split('(\r)?\n((\r)?\n)+', summary, 1)[0].strip() # Split after paragraphs, keep the first paragraph only

          summary_obj = Summary(metadata.id)                             # Create an instance of the callable class Summary and make the metadata.id available in it
          summary = re.sub('\[\[(.+?)\]\]', summary_obj, summary)        # Replace linked movie titles and names with full title or name
          summary = summary.replace('&#38;', '&').replace('&amp;', '&')
          summary = unescape(summary)
          summary = String.StripTags(summary)                            # Strip HTML tags
          summary = re.sub(r'\*([^\s].+?[^\s])\*', r'\1', summary)       # Strip asterisks from movie titles
          metadata.summary = summary

        # Get the poster from Moviepilot if it is available
        try:
          poster_url = ''.join([movie['poster']['base_url'], movie['poster']['photo_id'], '/', movie['poster']['file_name_base'], '.', movie['poster']['extension']])
        except:
          poster_url = None

        if poster_url is not None:
          if Prefs['poster']:
            try:
              if poster_url not in metadata.posters:
                img = HTTP.Request(poster_url)
                metadata.posters[poster_url] = Proxy.Preview(img)
            except:
              pass
          else:
            del metadata.posters[poster_url]
      except:
        pass


class Summary(object):
  def __init__(self, metadata_id):
    self.metadata_id = metadata_id

  def __call__(self, matchobj):
    type = matchobj.group(1)[0:1]
    name = matchobj.group(1)[2:-2]

    if type == 's':
      full_name = ''
      try:
        cast = JSON.ObjectFromURL(CAST_INFO_BY_IMDB % (self.metadata_id))
        for people in cast['movies_people']:
          if people['person']['restful_url'].find(name) != -1:
            # First or last name item can be empty or missing
            first_name = ''
            if 'first_name' in people['person'] and people['person']['first_name']:
              first_name = people['person']['first_name']

            last_name = ''
            if 'last_name' in people['person'] and people['person']['last_name']:
              last_name = people['person']['last_name']

            full_name = ' '.join([first_name, last_name]).strip()
            break
          else:
            continue
      except:
        pass
      return full_name
    elif type == 'm':
      title = ''
      try:
        movie = JSON.ObjectFromURL(MOVIE_INFO_BY_TITLE % (name))
        title = movie['display_title']
      except:
        pass
      return title

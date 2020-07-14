# pylint: disable=line-too-long
# pylint: disable=W0702, W0703, C0103, C0410
# encoding=utf8
'''
# PornTeam - (IAFD)
                                                  Version History
                                                  ---------------
    Date            Version                         Modification
    11 Jul 2020   2020.05.21.01    Creation: based on PornTeam

-----------------------------------------------------------------------------------------------------------------------------------
'''
import datetime, linecache, platform, os, re, string, subprocess, sys, unicodedata, urllib, urllib2
from googletrans import Translator

# Version / Log Title
VERSION_NO = '2020.05.21.01'
PLUGIN_LOG_TITLE = 'PornTeam'

# Pattern: (Studio) - Title (Year).ext: ^\((?P<studio>.+)\) - (?P<title>.+) \((?P<year>\d{4})\)
REGEX = Prefs['regex']

# Delay used when requesting HTML, may be good to have to prevent being banned from the site
DELAY = int(Prefs['delay'])

# detect the language the summary appears in on the web page
DETECT = Prefs['detect']

# URLS
BASE_URL = 'http://www.pornteam.com/catalog/'
BASE_SEARCH_URL = BASE_URL + '_search.php?q={0}&x=0&y=0&page=1'

# Date Formats used by website
DATE_YMD = '%Y%m%d'
DATEFORMAT = '%Y%m%d'

# Website Language
SITE_LANGUAGE = 'en'

# ----------------------------------------------------------------------------------------------------------------------------------
def Start():
    ''' initialise process '''
    HTTP.CacheTime = CACHE_1WEEK
    HTTP.Headers['User-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36'

# ----------------------------------------------------------------------------------------------------------------------------------
def ValidatePrefs():
    ''' validate changed user preferences '''
    pass

# ----------------------------------------------------------------------------------------------------------------------------------
def anyOf(iterable):
    '''  used for matching strings in lists '''
    for element in iterable:
        if element:
            return element
    return None

# ----------------------------------------------------------------------------------------------------------------------------------
class PornTeam(Agent.Movies):
    ''' define Agent class '''
    name = 'PornTeam (IAFD)'
    languages = [Locale.Language.English]
    primary_provider = False
    preference = True
    media_types = ['Movie']
    contributes_to = ['com.plexapp.agents.GayAdult', 'com.plexapp.agents.GayAdultFilms']

    # -------------------------------------------------------------------------------------------------------------------------------
    def matchFilename(self, filename):
        ''' return groups from filename regex match else return false '''
        pattern = re.compile(REGEX)
        matched = pattern.search(filename)
        if matched:
            groups = matched.groupdict()
            return groups['studio'], groups['title'], groups['year']
        else:
            raise Exception("File Name [{0}] not in the expected format: (Studio) - Title (Year)".format(file))

    # -------------------------------------------------------------------------------------------------------------------------------
    def matchStudioName(self, fileStudioName, siteStudioName):
        ''' match file studio name against website studio name: Boolean Return '''
        siteStudioName = self.NormaliseComparisonString(siteStudioName)

        if siteStudioName == fileStudioName:
            self.log('SELF:: Studio: Full Word Match: Site: {0} = File: {1}'.format(siteStudioName, fileStudioName))
        elif siteStudioName in fileStudioName:
            self.log('SELF:: Studio: Part Word Match: Site: {0} IN File: {1}'.format(siteStudioName, fileStudioName))
        elif fileStudioName in siteStudioName:
            self.log('SELF:: Studio: Part Word Match: File: {0} IN Site: {1}'.format(fileStudioName, siteStudioName))
        else:
            raise Exception('Match Failure: File: {0} != Site: {1} '.format(fileStudioName, siteStudioName))

        return True

    # -------------------------------------------------------------------------------------------------------------------------------
    def matchReleaseDate(self, fileDate, siteDate):
        ''' match file year against website release date: return formatted site date if no error or default to formated file date '''
        if len(siteDate) == 4:      # a year has being provided - default to 31st December of that year
            siteDate = siteDate + '1231'
            siteDate = datetime.datetime.strptime(siteDate, DATE_YMD)
        else:
            siteDate = datetime.datetime.strptime(siteDate, DATEFORMAT)

        # there can not be a difference more than 366 days between FileName Date and SiteDate
        dx = abs((fileDate - siteDate).days)
        msg = 'Match{0}: File Date [{1}] - Site Date [{2}] = Dx [{3}] days'.format(' Failure' if dx > 366 else '', fileDate.strftime('%Y %m %d'), siteDate.strftime('%Y %m %d'), dx)
        if dx > 366:
            raise Exception('Release Date: {0}'.format(msg))
        else:
            self.log('SELF:: Release Date: {0}'.format(msg))

        return siteDate

    # -------------------------------------------------------------------------------------------------------------------------------
    def NormaliseComparisonString(self, myString):
        ''' Normalise string for, strip uneeded characters for comparison of web site values to file name regex group values '''
        # convert to lower case and trim
        myString = myString.strip().lower()

        # normalise unicode characters
        myString = unicode(myString)
        myString = unicodedata.normalize('NFD', myString).encode('ascii', 'ignore')

        # replace ampersand with 'and'
        myString = myString.replace('&', 'and')

        # strip domain suffixes, vol., volume from string, standalone "1's"
        pattern = ur'[.](org|com|net|co[.][a-z]{2})|Vol[.]|\bPart\b|\bVolume\b|(?<!\d)1(?!\d)|[^A-Za-z0-9]+'
        myString = re.sub(pattern, '', myString, flags=re.IGNORECASE)

        return myString

    # -------------------------------------------------------------------------------------------------------------------------------
    def CleanSearchString(self, myString):
        ''' Prepare Video title for search query '''
        self.log('SELF:: Original Search Query [{0}]'.format(myString))

        # convert to lower case and trim and strip diacritics, fullstops, enquote
        myString = myString.replace('.', '').replace('-', '')
        myString = myString.lower().strip()
        myString = String.StripDiacritics(myString)

        # remove first word of title if its numeric
        pattern = r'[0-9]'
        myWords = myString.split()
        matched = re.search(pattern, myWords[0])  # match against first word
        if matched:
            self.log("SELF:: Search Query:: Dropping first word [{0}], as it's numeric".format(myWords[0]))
            myWords.remove(myWords[0])
            myString = ' '.join(myWords)
            self.log('SELF:: Amended Search Query [{0}]'.format(myString))
        else:
            self.log('SELF:: Search Query:: First word is not numeric')

        # sort out double encoding: & html code %26 for example is encoded as %2526; on MAC OS '*' sometimes appear in the encoded string
        myNormalString = String.URLEncode(myString).replace('%25', '%').replace('*', '')
        myQuotedString = String.URLEncode('"{0}"'.format(myString)).replace('%25', '%').replace('*', '')
        myString = [myNormalString, myQuotedString]
        self.log('SELF:: Returned Search Query [{0}]'.format(myString))

        return myString

    # -------------------------------------------------------------------------------------------------------------------------------
    def TranslateString(self, myString, language):
        ''' Translate string into Library language '''
        myString = myString.strip()
        if language == 'xn' or language == 'xx':    # no language or language unknown
            self.log('SELF:: Library Language: [%s], Run Translation: [False]', 'No Language' if language == 'xn' else 'Unknown')
        elif myString:
            translator = Translator(service_urls=['translate.google.com', 'translate.google.ca', 'translate.google.co.uk',
                                                  'translate.google.com.au', 'translate.google.co.za', 'translate.google.br.com',
                                                  'translate.google.pt', 'translate.google.es', 'translate.google.com.mx',
                                                  'translate.google.it', 'translate.google.nl', 'translate.google.be',
                                                  'translate.google.de', 'translate.google.ch', 'translate.google.at',
                                                  'translate.google.ru', 'translate.google.pl', 'translate.google.bg',
                                                  'translate.google.com.eg', 'translate.google.co.il', 'translate.google.co.jp',
                                                  'translate.google.co.kr', 'translate.google.fr', 'translate.google.dk'])
            runTranslation = (language != SITE_LANGUAGE)
            self.log('SELF:: [Library:Site] Language: [%s:%s], Run Translation: [%s]', language, SITE_LANGUAGE, runTranslation)
            if DETECT:
                detectString = re.findall(ur'.*?[.!?]', myString)[:4]   # take first 4 sentences of string to detect language
                detectString = ''.join(detectString)
                self.log('SELF:: Detect Site Language [%s] using this text: %s', DETECT, detectString)
                try:
                    detected = translator.detect(detectString)
                    runTranslation = (language != detected.lang)
                    self.log('SELF:: Detected Language: [%s] Run Translation: [%s]', detected.lang, runTranslation)
                except Exception as e:
                    self.log('SELF:: Error Detecting Text Language: %s', e)

            try:
                myString = translator.translate(myString, dest=language).text if runTranslation else myString
                self.log('SELF:: Translated [%s] Summary Found: %s', runTranslation, myString)
            except Exception as e:
                self.log('SELF:: Error Translating Text: %s', e)

        return myString if myString else ' '     # return single space to initialise metadata summary field

    # -------------------------------------------------------------------------------------------------------------------------------
    def getIAFDActorImage(self, myString, FilmYear):
        ''' check IAFD web site for better quality actor thumbnails irrespective of whether we have a thumbnail or not '''

        actorname = myString
        myString = String.StripDiacritics(myString).lower()

        # build list containing three possible cast links 1. Full Search in case of AKAs 2. as Performer 3. as Director
        # the 2nd and 3rd links will only be used if there is no search result
        urlList = []
        fullname = myString.replace(' ', '').replace("'", '').replace(".", '')
        full_name = myString.replace(' ', '-').replace("'", '&apos;')
        for gender in ['m', 'd']:
            url = 'http://www.iafd.com/person.rme/perfid={0}/gender={1}/{2}.htm'.format(fullname, gender, full_name)
            urlList.append(url)

        myString = String.URLEncode(myString)
        url = 'http://www.iafd.com/results.asp?searchtype=comprehensive&searchstring={0}'.format(myString)
        urlList.append(url)

        for count, url in enumerate(urlList, start=1):
            photourl = ''
            try:
                self.log('SELF:: %s. IAFD Actor search string [ %s ]', count, url)
                html = HTML.ElementFromURL(url)
                if 'gender=' in url:
                    career = html.xpath('//p[.="Years Active"]/following-sibling::p[1]/text()[normalize-space()]')[0]
                    try:
                        startCareer = career.split('-')[0]
                        self.log('SELF:: Actor: %s  Start of Career: [ %s ]', actorname, startCareer)
                        if startCareer <= FilmYear:
                            photourl = html.xpath('//*[@id="headshot"]/img/@src')[0]
                            photourl = 'nophoto' if 'nophoto' in photourl else photourl
                            self.log('SELF:: Search %s Result: IAFD Photo URL [ %s ]', count, photourl)
                            break
                    except:
                        continue
                else:
                    xPathString = '//table[@id="tblMal" or @id="tblDir"]/tbody/tr/td[contains(normalize-space(.),"{0}")]/parent::tr'.format(actorname)
                    actorList = html.xpath(xPathString)
                    for actor in actorList:
                        try:
                            startCareer = actor.xpath('./td[4]/text()[normalize-space()]')[0]
                            self.log('SELF:: Actor: %s  Start of Career: [ %s ]', actorname, startCareer)
                            if startCareer <= FilmYear:
                                photourl = actor.xpath('./td[1]/a/img/@src')[0]
                                photourl = 'nophoto' if photourl == 'http://www.iafd.com/graphics/headshots/thumbs/th_iafd_ad.gif' else photourl
                                self.log('SELF:: Search %s Result: IAFD Photo URL [ %s ]', count, photourl)
                                break
                        except:
                            continue
                    break
            except Exception as e:
                photourl = ''
                self.log('SELF:: Error: Search %s Result: Could not retrieve IAFD Actor Page, %s', count, e)
                continue

        return photourl

    # -------------------------------------------------------------------------------------------------------------------------------
    def log(self, message, *args):
        ''' log messages '''
        if re.search('ERROR', message, re.IGNORECASE):
            Log.Error(PLUGIN_LOG_TITLE + ' - ' + message, *args)
        else:
            Log.Info(PLUGIN_LOG_TITLE + ' - ' + message, *args)

    # -------------------------------------------------------------------------------------------------------------------------------
    def search(self, results, media, lang, manual):
        ''' Search For Media Entry '''
        if not media.items[0].parts[0].file:
            return
        folder, filename = os.path.split(os.path.splitext(media.items[0].parts[0].file)[0])

        self.log('-----------------------------------------------------------------------')
        self.log('SEARCH:: Version               : v.%s', VERSION_NO)
        self.log('SEARCH:: Python                : %s', sys.version_info)
        self.log('SEARCH:: Platform              : %s %s', platform.system(), platform.release())
        self.log('SEARCH:: Prefs-> delay         : %s', DELAY)
        self.log('SEARCH::      -> detect        : %s', DETECT)
        self.log('SEARCH::      -> regex         : %s', REGEX)
        self.log('SEARCH:: Library:Site Language : %s:%s', lang, SITE_LANGUAGE)
        self.log('SEARCH:: Media Title           : %s', media.title)
        self.log('SEARCH:: File Name             : %s', filename)
        self.log('SEARCH:: File Folder           : %s', folder)
        self.log('-----------------------------------------------------------------------')

        # Check filename format
        try:
            FilmStudio, FilmTitle, FilmYear = self.matchFilename(filename)
            self.log('SEARCH:: Processing: Studio: %s   Title: %s   Year: %s', FilmStudio, FilmTitle, FilmYear)
        except Exception as e:
            self.log('SEARCH:: Error: %s', e)
            return

        # Compare Variables used to check against the studio name on website: remove all umlauts, accents and ligatures
        compareStudio = self.NormaliseComparisonString(FilmStudio)
        compareTitle = self.NormaliseComparisonString(FilmTitle)
        compareReleaseDate = datetime.datetime(int(FilmYear), 12, 31)  # default to 31 Dec of Filename year

        # Search Query - for use to search the internet
        searchTitleList = self.CleanSearchString(FilmTitle)
        for count, searchTitle in enumerate(searchTitleList, start=1):
            searchQuery = BASE_SEARCH_URL.format(searchTitle)
            self.log('SEARCH:: %s. Search Query: %s', count, searchQuery)

            morePages = True
            while morePages:
                self.log('SEARCH:: Search Query: %s', searchQuery)
                try:
                    html = HTML.ElementFromURL(searchQuery, timeout=20, sleep=DELAY)
                    # Finds the entire media enclosure
                    titleList = html.xpath('//div[@class="video-title-container"]')
                    if not titleList:
                        break   # out of WHILE loop to the FOR loop
                except Exception as e:
                    self.log('SEARCH:: Error: Search Query did not pull any results: %s', e)
                    return

                try:
                    searchQuery = html.xpath('//a[@class="right-arrow"]/@href')[0]
                    searchQuery = (BASE_URL if BASE_URL not in searchQuery else '') + searchQuery
                    self.log('SEARCH:: Next Page Search Query: %s', searchQuery)
                    pageNumber = int(searchQuery.split('page=')[1])
                    morePages = True if pageNumber <= 10 else False
                except:
                    searchQuery = ''
                    self.log('SEARCH:: No More Pages Found')
                    pageNumber = 1
                    morePages = False

                self.log('SEARCH:: Result Page No: %s, Titles Found %s', pageNumber, len(titleList))
                for title in titleList:
                    # Site Title
                    try:
                        siteTitle = title.xpath('./a/text()')[0]
                        # strip studio if found in title
                        siteTitle = re.sub(FilmStudio, '', siteTitle, flags=re.IGNORECASE)
                        siteTitle = self.NormaliseComparisonString(siteTitle)
                        self.log('SEARCH:: Title Match: [%s] Compare Title - Site Title "%s - %s"', (compareTitle == siteTitle), compareTitle, siteTitle)
                        if siteTitle != compareTitle:
                            continue
                    except:
                        self.log('SEARCH:: Error getting Site Title')
                        continue

                    # Site Title URL
                    try:
                        siteURL = title.xpath('./a/@href')[0]
                        siteURL = ('' if BASE_URL in siteURL else BASE_URL) + siteURL
                        self.log('SEARCH:: Site Title url: %s', siteURL)
                    except:
                        self.log('SEARCH:: Error getting Site Title Url')
                        continue

                    # Access Site URL for Studio and Release Date information
                    try:
                        html = HTML.ElementFromURL(siteURL, sleep=DELAY)
                    except Exception as e:
                        self.log('SEARCH:: Error reading Site URL page: %s', e)
                        continue

                    # Site Studio
                    try:
                        foundStudio = False
                        htmlSiteStudio = html.xpath('//td[contains(.,"Studio:")]/following-sibling::td/a/text()')
                        self.log('SEARCH:: %s Site URL Studios: %s', len(htmlSiteStudio), htmlSiteStudio)
                        for siteStudio in htmlSiteStudio:
                            try:
                                self.matchStudioName(compareStudio, siteStudio)
                                self.log('SEARCH:: %s Compare with: %s', compareStudio, siteStudio)
                                foundStudio = True
                            except Exception as e:
                                self.log('SEARCH:: Error: %s', e)
                                continue

                            if foundStudio:
                                break
                    except Exception as e:
                        self.log('SEARCH:: Error getting Site Studio %s', e)
                        continue

                    if not foundStudio:
                        self.log('SEARCH:: Error No Matching Site Studio')
                        continue

                    # Site Release Date
                    try:
                        siteReleaseDate = html.xpath('//td[contains(.,"Year Produced:")]/following-sibling::td/text()')[0]
                        self.log('SEARCH:: Site URL Release Date: %s', siteReleaseDate)
                        try:
                            siteReleaseDate = self.matchReleaseDate(compareReleaseDate, siteReleaseDate)
                        except Exception as e:
                            self.log('SEARCH:: Error getting Site URL Release Date: %s', e)
                            continue
                    except:
                        self.log('SEARCH:: Error getting Site URL Release Date: Default to Filename Date')
                        siteReleaseDate = compareReleaseDate

                    # we should have a match on studio, title and year now
                    results.Append(MetadataSearchResult(id=siteURL + '|' + siteReleaseDate.strftime(DATE_YMD), name=FilmTitle, score=100, lang=lang))
                    return

    # -------------------------------------------------------------------------------------------------------------------------------
    def update(self, metadata, media, lang, force=True):
        ''' Update Media Entry '''
        folder, filename = os.path.split(os.path.splitext(media.items[0].parts[0].file)[0])
        self.log('-----------------------------------------------------------------------')
        self.log('UPDATE:: Version    : v.%s', VERSION_NO)
        self.log('UPDATE:: File Name  : %s', filename)
        self.log('UPDATE:: File Folder: %s', folder)
        self.log('-----------------------------------------------------------------------')

        # Check filename format
        try:
            FilmStudio, FilmTitle, FilmYear = self.matchFilename(filename)
            self.log('UPDATE:: Processing: Studio: %s   Title: %s   Year: %s', FilmStudio, FilmTitle, FilmYear)
        except Exception as e:
            self.log('UPDATE:: Error: %s', e)
            return

        # Fetch HTML.
        html = HTML.ElementFromURL(metadata.id, sleep=DELAY)

        #  The following bits of metadata need to be established and used to update the movie on plex
        #    1.  Metadata that is set by Agent as default
        #        a. Studio               : From studio group of filename - no need to process this as is used to find it on website
        #        b. Title                : From title group of filename - no need to process this as is used to find it on website
        #        c. Tag line             : Corresponds to the url of movie
        #        d. Originally Available : set from metadata.id (search result)
        #        e. Content Rating       : Always X
        #    2.  Metadata retrieved from website
        #        a. Summary
        #        b. Directors            : List of Drectors (alphabetic order)
        #        c. Cast                 : List of Actors and Photos (alphabetic order) - Photos sourced from IAFD
        #        d. Genres
        #        e. Rating
        #        f. Posters/Background

        # 1a.   Studio - straight of the file name
        metadata.studio = FilmStudio
        self.log('UPDATE:: Studio: %s' % metadata.studio)

        # 1b.   Set Title
        metadata.title = FilmTitle
        self.log('UPDATE:: Video Title: %s' % metadata.title)

        # 1c/d. Set Tagline/Originally Available from metadata.id
        metadata.tagline = metadata.id.split('|')[0]
        metadata.originally_available_at = datetime.datetime.strptime(metadata.id.split('|')[1], DATE_YMD)
        metadata.year = metadata.originally_available_at.year
        self.log('UPDATE:: Tagline: %s', metadata.tagline)
        self.log('UPDATE:: Default Originally Available Date: %s', metadata.originally_available_at)

        # 1e.   Set Content Rating to Adult
        metadata.content_rating = 'X'
        self.log('UPDATE:: Content Rating: X')

        # 2a.   Summary
        try:
            htmlsummary = html.xpath('//div[@id="productInfo_content_holder"]/p/text()')
            htmlsummary = [x.strip() for x in htmlsummary]
            summary = '\n'.join(htmlsummary)
            self.log('UPDATE:: Summary Found: %s', summary)
            metadata.summary = self.TranslateString(summary, lang)
        except Exception as e:
            summary = ''
            self.log('UPDATE:: Error getting Summary: %s', e)

        # 2b.   Directors
        try:
            directors = []
            htmldirector = html.xpath('//td[contains(.,"Director:")]/following-sibling::td/a/text()')
            self.log('UPDATE:: Director List %s', htmldirector)
            for director in htmldirector:
                director = director.strip()
                if director:
                    if ' and ' in director:
                        director = director.split(' and ')
                        directors.extend(director)
                    elif ' with ' in director:
                        director = director.split(' with ')
                        directors.extend(director)
                    else:
                        directors.append(director)

            # sort the dictionary and add kv to metadata
            directors.sort()
            metadata.directors.clear()
            for director in directors:
                Director = metadata.directors.new()
                Director.name = director
        except Exception as e:
            self.log('UPDATE:: Error getting Director(s): %s', e)

        # 2c.   Cast: get thumbnails from IAFD as they are right dimensions for plex cast list and have more actor photos than AdultEntertainmentBroadcastNetwork
        try:
            castdict = {}
            castlist = []
            htmlcast = html.xpath('//td[contains(.,"Cast:")]/following-sibling::td/a/text()')
            self.log('UPDATE:: Cast List %s', htmlcast)
            for cast in htmlcast:
                cast = cast.strip()
                if cast:
                    if ' and ' in cast:
                        cast = cast.split(' and ')
                        castlist.extend(cast)
                    elif ' with ' in director:
                        cast = cast.split(' with ')
                        castlist.extend(cast)
                    else:
                        castlist.append(cast)

            for cast in castlist:
                if '(' in cast:
                    cast = cast.split('(')[0]
                castdict[cast] = self.getIAFDActorImage(cast, FilmYear)
                castdict[cast] = '' if castdict[cast] == 'nophoto' else castdict[cast]

            # sort the dictionary and add kv to metadata
            metadata.roles.clear()
            for key in sorted(castdict):
                role = metadata.roles.new()
                role.name = key
                role.photo = castdict[key]
        except Exception as e:
            self.log('UPDATE:: Error getting Cast: %s', e)

        # 2d.   Genres
        try:
            ignoreGenres = ['PornTeam.com Exclusives!', 'PORNTEAM.TV Most Watched', 'Blu-ray', 'Award Winning Movies', 'High Definition', 'GayVn Nominated', 'Gay Classics', 'VOD Award Nominees', 'Top Sellers of 2006']
            genres = []
            htmlgenres = html.xpath('//div[@id="genres_content"]/a/text()')
            self.log('UPDATE:: %s Genres Found: %s', len(htmlgenres), htmlgenres)
            for genre in htmlgenres:
                genre = genre.strip()
                if not genre:
                    continue
                if anyOf(x in genre.lower() for x in ignoreGenres):
                    continue
                genres.append(genre)

            genres.sort()
            metadata.genres.clear()
            for genre in genres:
                metadata.genres.add(genre)
        except Exception as e:
            self.log('UPDATE:: Error getting Genres: %s', e)

        # 2e.   Rating (out of 5 Stars) = Rating can be a maximum of 10 - float value
        try:
            rating = html.xpath('//div[@id="rewiew_content"]//div[contains(@title, "Average customer rating")]/@title')[0].strip()
            rating = rating.split(';')[0]
            rating = rating.split(':')[1].strip()
            rating = float(rating) * 2.0
            self.log('UPDATE:: Film Rating %s', rating)
            metadata.rating = rating
        except Exception as e:
            self.log('UPDATE:: Error getting Rating: %s', e)


        # 2f.   Posters/Background Art - Front Cover set to poster, Back Cover to background art
        # In this list we are going to save the posters that we want to keep
        try:
            htmlimages = html.xpath('//div[@class="image-box"]/a/@href')
            self.log('UPDATE:: %s Poster/Background Art Found: %s', len(htmlimages), htmlimages)

            validPosterList = []
            image = htmlimages[0].split('?')[0]
            image = ('http:' if 'http:' not in image else '') + image
            self.log('UPDATE:: Movie Poster Found: %s', image)
            validPosterList.append(image)
            if image not in metadata.posters:
                metadata.posters[image] = Proxy.Media(HTTP.Request(image).content, sort_order=1)
            #  clean up and only keep the poster we have added
            metadata.posters.validate_keys(validPosterList)

            validArtList = []
            image = htmlimages[1].split('?')[0]
            image = ('http:' if 'http:' not in image else '') + image
            self.log('UPDATE:: Movie Background Art Found: %s', image)
            validArtList.append(image)
            if image not in metadata.art:
                metadata.art[image] = Proxy.Media(HTTP.Request(image).content, sort_order=1)
            #  clean up and only keep the Art we have added
            metadata.art.validate_keys(validArtList)
        except Exception as e:
            self.log('UPDATE:: Error getting Poster/Background Art: %s', e)

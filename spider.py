# -*- coding: utf-8 -*-

"""
2016 (c) Iakhin Ilia
Spider Hren - let's parse Web Site and do some 'deep ANALytics'!
"""

import urllib2
import logging
import unittest
import itertools
import zlib
import urllib
import os
import sys
import ssl
import time
from urllib2 import URLError
from urlparse import urljoin
from HTMLParser import HTMLParser
from logging import info, debug, error
from multiprocessing import Pool as ThreadPool

URI = str(sys.argv[1])
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


def unify_uri(uri):
    """
    :param uri: is not unified on the site,
    sometimes it ended by slash, sometimes not.
    Let's add slash everywhere it absent and
    :return: it
    """
    info("URI before unifying: %s" % uri)
    uri += '/' if uri[-1] != '/' else uri
    uri = URI + uri if uri[0] == '/' else uri
    uri = URI + '/' + uri if 'http' not in uri else uri
    info("URI after unifying: %s" % uri)
    return uri


def exec_multi(thread_count, function, multi_args):
    pool = ThreadPool(thread_count)
    responses = pool.map(function, multi_args)
    pool.close()
    pool.join()
    return responses


def filt(a):
    """
    Remove matches from list
    """
    a.sort()
    return list(a for a, _ in itertools.groupby(a))


def urlopen(url):
    """
    Get HTTP code
    func. from sitemap
    """

    def try_urlopen(message):
        try:
            urllib2.urlopen(url, timeout=30)
        except URLError, e:
            if hasattr(e, 'code'):
                message = str(e.code)
            elif hasattr(e, 'reason'):
                message = e.reason
            # this message should be 'debug'
            info("%s - %s" % (message, str(url)))
            return message
        except ssl.CertificateError, e:
            if e.message == "hostname 'vl.pdfm10.parallels.com' doesn't match either " \
                            "of 'registration.parallels.com', 'www.registration.parallels.com'":
                # this message should be 'debug'
                info("XFail: %s - %s" % (e.message, str(url)))
                return e.message
            else:
                info('Got exception: %s - differ than XFail on URI: %s' % (e, url))
                return e.message
        except Exception, e:
            error('Exception: %s - %s - %s' % (str(url), str(e.message), str(e.args)))
            time.sleep(1)
            try_urlopen('OK')
        return message

    message = try_urlopen('OK')
    return message


class UrlFinder(HTMLParser):
    def __init__(self, my_tag):
        HTMLParser.__init__(self)
        self.links = []
        self.my_tag = my_tag

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.my_tag == tag:
            try:
                self.links.append(attrs['href'])
            except:
                pass


def parser(node, tag):
    """
    Parse sitemap "where - node" / "search inside this tag"
    """
    result = []
    _parser = UrlFinder(tag)
    try:
        response = urllib.urlopen(node).read()
    except Exception as e:
        info("urllib failed: %s" % e.__repr__())
        response = []

    if response and len(response) > 0:
        if urllib.urlopen(node).headers.getheader('Content-Encoding') == 'gzip':
            content = zlib.decompress(response, zlib.MAX_WBITS | 32)
        else:
            content = response
        _parser.feed(content)
        for link in _parser.links:
            if URI in link or 'http' not in link:
                processed_link = unify_uri(link)
                result.append([processed_link, node])
        return result
    else:
        info('Content length: %s on %s by tag: %s' %
             (str(len(response)), str(node), str(tag)))


class Spider(object):
    def __init__(self, base_url):
        self.base_url = base_url
        self.output = []
        self.message = []

    def iterator(self, node):
        """
        Iterator walks through the website and launch itself if child-link found
        """
        info("__________________")
        info("Iterator started on node: %s" % node)

        def nodelist_checker(node, nodelist):
            """
            Find 'node' inside the parentals from 'nodelist',
            if found: return 1
            if not: return 0

            nodelist cell format:
            [0] - children node
            [1] - parental node
            """
            for transition in nodelist:
                if transition[0] == node:
                    return 1
            return 0

        """
        Get all href's from node via 'parser' function
        """
        childs = parser(node, 'a')
        info("Output during child processing contain %s lines" % len(childs))
        for j in childs:
            info("Trying to compare child node: %s from\n"
                 "parental node: %s" % (j[0], j[1]))
            if not nodelist_checker(j[0], self.output):
                info("Child %s was not visited, start iterator!" % j[0])
                self.output.append(j)
                self.iterator(j[0])
            else:
                info("Child %s was visited, skip!" % j[0])

            info("Iterator completed, exit loop")

        # self.output = self.output + childs
        self.output = filt(self.output)

    def check(self):
        """
        For each broken URI generate string like:
        HTTP status code :: broken URI :: <<< parental URI
        and append to message
        """
        info("Call zero iterator on node: %s" % self.base_url)
        self.iterator(self.base_url)
        info("Crawling completed!")
        uris = []
        for cell in self.output:
            if cell[1].find('https') == -1:
                uris.append(cell[1])
            else:
                uris.append(str(cell[1]).replace("https", "http"))
        uris = filt(uris)
        info("Links: %s" % str(len(uris)))
        code = exec_multi(1, urlopen, uris)
        message = []
        for i in range(0, len(uris)):
            if code[i] != "OK":
                for cell in self.output:
                    if cell[1] == uris[i]:
                        message.append([code[i], cell[1], " <<< " + cell[0]])
        return message


class SpiderHren(unittest.TestCase):
    """
    Unittest class,pylint make me a capitan
    """

    def test_spider(self):
        """
        Show message if it exist
        """
        spider_unit = Spider(URI)
        message = spider_unit.check()
        self.assertTrue(len(message) == 0, "\n" + "\n".join(' :: '.join(x) for x in message))


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)

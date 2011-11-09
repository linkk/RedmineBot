''' IRC bot for Redmine
    Copyright (C) 2011 Jasmin Rahimic

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.                  '''

import sys # not needed?
import os
import random
import time
import feedparser # http://www.feedparser.org/
import xml.dom.minidom
#import therapist
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.words.protocols import irc
import zlib
import json
from time import mktime, localtime

class SubversionBroadcast(DatagramProtocol):
    def __init__(self):
        self.callback = None

    def datagramReceived(self, data, (host, port)):
        if self.callback != None:
            d = json.loads(zlib.decompress(data))
            try:
                #print d
                if len(d['message']) > 0 and d['message'].find('NOREVIEW') != -1 :
                    self.callback('Subversion (%s): (%s) %s' % (d['repository'], d['author'], d['message']))
                    print 'Subversion (%s): (%s) %s' % (d['repository'], d['author'], d['message'])
            except Exception as e:
                print 'Subversion failed'
                print e


class RwBot(irc.IRCClient):
    def __init__(self):
        # time.time() is a floating point number expressed in seconds since the epoch, in UTC.
        self.wiki_next = time.time() # Next time we will get the Wiki RSS.
        self.wiki_latest = time.time() # Date of last Wiki RSS item we printed.
        self.redmine_next = time.time() # Next time we will get the Redmine RSS.
        self.redmine_latest = time.time() # Date of last Redmine RSS item we printed.
    
    # Hacky: factory isn't available until after __init__
    # http://www.eflorenzano.com/blog/post/writing-markov-chain-irc-bot-twisted-and-python/
    def _get_nickname(self):
        return self.factory.nickname
    
    nickname = property(_get_nickname)
    
    def signedOn(self):
        self.join(self.factory.channel)
        self.factory.svn.callback = self.svn_commit
    
    def privmsg(self, user, channel, msg):
        if msg.find(self.nickname) != -1 :
            self.msg(channel, '> ' + ':P' )
    
    def irc_PING(self, prefix, params):
        irc.IRCClient.irc_PING(self, prefix, params) # call base method (required to PONG).
        #self._Wiki()
        self._Redmine()
        r = random.random()
        t = time.gmtime()
        if t.tm_hour > 10 and t.tm_hour < 17 and t.tm_wday < 6 and r > 0.99:
            silly = self._Silly()
            self.msg(self.factory.channel, silly)
    
    def _Wiki(self):
        t = time.time()
        if t > self.wiki_next:
            latest_new = self.wiki_latest
            # Then we run.
            self.wiki_next = self.wiki_next + 60 * 5
            wiki = feedparser.parse("http://wiki/Special:RecentChanges?title=Special:RecentChanges&feed=atom")
            for i in reversed(range(len(wiki.entries))):
                e = wiki.entries[i]
                et = time.mktime(e.updated_parsed)
                if et > self.wiki_latest:
                    # print it
                    msg = "Wiki (%s): %s" % (e.author_detail.name, e.link)
                    self.msg(self.factory.channel, msg.encode('utf-8', 'ignore'))
                    
                    # find the new latest time
                    if et > latest_new:
                        latest_new = et
                #if
            #for
            self.wiki_latest = latest_new
    #_DoWiki
    
    def _Redmine(self):
        t = time.time()
        if t > self.redmine_next:
            latest_new = self.redmine_latest
            # Then we run.
            self.redmine_next = self.redmine_next + 60 * 5
            redmine = feedparser.parse("http://redmine/activity.atom?key=7c58101c32da49aba2e02f9c3354452efdcc0e7b")
            
            for i in reversed(range(len(redmine.entries))):
                e = redmine.entries[i]
                et = localtime(mktime(e.updated_parsed))
                if et > self.redmine_latest:
                    # print it
                    #if e.title.find('(New)') != -1 or e.title.find('(Reopened)') != -1:
                    
                    msg = "Redmine: (%s): %s" % (e.link, e.title)
                    self.msg(self.factory.channel, msg.encode('utf-8', 'ignore'))
                    
                    # find the new latest time
                    if et > latest_new:
                        latest_new = et
                    #!if
            #for
            self.redmine_latest = latest_new
    #_Redmine
   
    def _Silly(self):
        try:
            cmd = os.popen('fortune -n 80')
            fortune = cmd.read()
            cmd.close()
            lines = fortune.strip().split()
            return ' '.join(lines)
        except Exception as e:
            print e
            return ''
    #_Silly
    
    
    def svn_commit(self, msg):
        msg1 = msg.encode('ascii', 'ignore')
        words = msg1.split()
        #self.msg(self.factory.channel, ' '.join(words))
    #svn_commit
#RwBot



class RwBotFactory(protocol.ClientFactory):
    protocol = RwBot # http://twistedmatrix.com/documents/8.2.0/api/twisted.internet.protocol.Factory.html

    def __init__(self, channel, nickname, svn):
        self.channel = channel
        self.nickname = nickname
        self.realname = nickname
        self.username = nickname
        self.lineRate = 12
        self.svn = svn

    def clientConnectionLost(self, connector, reason):
        print "Lost connection (%s), reconnecting." % (reason,)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Could not connect: %s" % (reason,)
#RwBotFactory

svn = SubversionBroadcast()
rwBot = RwBotFactory('#knowhowERP_dev', 'rwbot', svn)

reactor.connectTCP('irc.freenode.org', 6667, rwBot)
reactor.listenUDP(45679, svn)
reactor.run()


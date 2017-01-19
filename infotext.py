#!/usr/bin/python
# -*- coding: utf-8 -*-

""" infotext.py v0.2

Simply prints data and stats from various sources. Most useful as input
program to xscreensavers that simply takes some text and displays it.

Currently implemented:
  * MPD playing status
  * OpenWeatherMap weather data and forecast
  * System stats: Local time, date, cpuload, load average, memory info

Written specifically for RaspberryPi, but useable on other systems too.

Usage: Edit the configuration variables below to suit your needs. 
You may want to apply for an app key (APPID) at http://openweathermap.org.
Then configure xscreensaver to use any text-displaying screensaver
(e.g. Phosphor, Apple2, StarWars, ...). Then, in the xscreensavers
configuration dialog's advanced tab, configure this program as text source.


Raspbian package dependencies:
python python-mpd xscreensaver xscreensaver-data xscreensaver-data-extra

Optional GL screensavers (slow on a raspi!):
xscreensaver-gl xscreensaver-gl-extra libgl1-mesa-swx11


Published under the terms of the MIT License:

Copyright (c) 2013 Dave Kliczbor <maligree@gmx.de>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

### configuration variables

MAXLINES     = 17
MAXLEN       = 51
SHOWMPD      = True
SHOWWEATHER  = True
SHOWCPUTIME  = True
SHOWTIME     = False
SHOWMEM      = False
SHOWFORTUNE  = True

WEATHERCITY  = 'dortmund'
WEATHERAPPID = ''

MPDHOST      = 'localhost'
MPDPORT      = 6600

FORTUNEOPTS  = [ '-s', '-o', '-n', '%d' % (MAXLEN*5,) ]

# the following config variables probably do not need to be changed
WEATHERDATAURL = 'http://api.openweathermap.org/data/2.5/weather?q=%s&units=metric&APPID=%s'
WEATHERFORECASTURL = 'http://api.openweathermap.org/data/2.5/forecast/daily?q=%s&units=metric&cnt=3&APPID=%s'
SAVEDIR = '/run/shm'


### module imports

import mpd
import pickle
import time
import os
import textwrap
from json import load as jsonload
from urllib2 import urlopen
from subprocess import check_output
from pprint import pprint

### some functions

def timelist():
  """Reads cpu/process stats from /proc/stat and returns them
  """
  statfile = file("/proc/stat", "r")
  t = statfile.readline().split(" ")[2:6]
  statfile.close()
  for i in range(len(t))  :
      t[i] = int(t[i])
  return t

def deltatime():
  """Reads cpu/process stats from last run, shifts them, adds current stats from timelist().
  Returns currents and last stats
  """
  x = [0,0,0,0]
  try:
    f = open(SAVEDIR+'/cpuload', 'rd')
    x = pickle.load(f)
    f.close()
  except: pass
  y = timelist()
  try:
    f = open(SAVEDIR+'/cpuload', 'wb')
    pickle.dump(y, f)
    f.close()
  except:
    print("ERR: cannot save cpuload data in %s/cpuload" % SAVEDIR)
  for i in range(len(x))  :
      y[i] -= x[i]
  return y

def cpuload():
  """Calculates average cpu load since last run and returns it as percentage
  """
  dt = deltatime()
  return 100 - (dt[len(dt) - 1] * 100.00 / sum(dt))

def load():
  """Reads load average of last minute from /proc/loadavg and returns it as string
  """
  r = ""
  try:
    r = " ".join(file('/proc/loadavg').readline().split(" ")[0:1])
  except: pass
  return r
  
def meminfo():
  """Returns /proc/meminfo as dict
  """
  return dict([ [ b.strip(":") for b in a if len(b) > 0 and b != 'kB' ] for a in [ l.strip().split(" ") for l in file("/proc/meminfo").readlines() ] ])

def u(s):
  """Makes unicode from ascii string without conking out on error
  """
  return unicode(s, 'utf-8', errors='ignore')
  
def wday(offset_from_today=0):
  """Returns day of week as string, either the current day or with an offset (days) into the future
  Ex.: Return day of week of tomorrow: wday(1)
  """
  return ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'][(time.localtime().tm_wday + offset_from_today) % 7]

def numf(n):
  """Formats a number between -999 and 9999 to 2-4 characters. 
  Numbers < 10.0 are returned with one decimal after the point, other numbers as integers.
  Ex.: 0.2341 -> '0.2', 9.0223 -> '9.2', 11.234 -> '11', -5.23 -> '-5.2'
  """
  if abs(n) < 10.0: 
    return "%.1f" % n
  else:
    return "%.0f" % n
    
def carddir(deg):
  """Returns the cardinal direction string from degrees (0° = N, 90° = E, ...)
  """
  return ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'][int(((deg+11.25)%360)/22.5)]

def fetch_weather_data():
  """Fetches weather data from openweathermap.org.
  Data is cached in /run/shm, updates after 1000 seconds.
  Returns a dict/list data structure derived from the JSON data.
  """
  c = None
  try:
    f = open(SAVEDIR+'/weather', 'rd')
    c = pickle.load(f)
    f.close()
  except: pass
  if c is None or c['checktime'] < time.time() - 1000.0:
    try:
      weatherdata = urlopen(WEATHERDATAURL % (WEATHERCITY, WEATHERAPPID))
      forecastdata = urlopen(WEATHERFORECASTURL % (WEATHERCITY, WEATHERAPPID))
      c = jsonload(weatherdata)
      c['forecast'] = jsonload(forecastdata)
      c['checktime'] = time.time()
      try:
        f = open(SAVEDIR+'/weather', 'wb')
        pickle.dump(c, f)
        f.close()
      except Exception as e: 
        print('ERR: cannot save weather in %s/weather' % SAVEDIR)
    except Exception as e:
      print("ERR: cannot fetch weather: " + e.message)
  return c

def fetch_mpd_data():
  """Connects to an MPD instance and fetches the status and current song data.
  Cannot cope with authenticated connections (yet).
  """
  mpc = mpd.MPDClient()
  d = None
  try:
    mpc.connect(MPDHOST, MPDPORT)
    d = dict(mpc.status().items() + mpc.currentsong().items())
    mpc.disconnect()
  except:
    pass
  return d


### format weather data
def interpret_rain(c):
  if 'rain' in c:
    for k,v in c['rain'].iteritems():
      return "rain %.0fmm/%s" % (v,k)
  elif 'snow' in c:
    for k,v in c['snow'].iteritems():
      return "snow %.0fmm/%s" % (v,k)
  else:
    return "no rain"
    
def count_leading_whitespace(s):
  count = 0
  for c in s:
    if c == " ":
      count += 1
    elif c == "\t":
      count += 4
    else:
      break
  return count
    
def rewrap(p):
  #print repr(p)
  pars = p.splitlines()
  outpars = []
  outtext = ""
  indent = -2
  for par in pars:
    cur_indent = count_leading_whitespace(par)
    if ": " in par or ":\t" in par:
      indent = cur_indent
      outpars.append((indent,par.strip(),))
    elif indent-1 <= cur_indent <= indent+1:
      outpars[-1] = (indent, (str(outpars[-1][1]) + (par.strip() if len(outpars[-1][1]) < 1 else " " + par.strip())), )
    else:
      indent = cur_indent
      outpars.append((indent,par.strip(),))
  #print repr(outpars)
  for parindent,par in outpars:
    #print repr(parindent)
    #print repr(par)
    outtext += textwrap.fill(par, width=MAXLEN, replace_whitespace=True, initial_indent=" "*parindent, subsequent_indent=" "*parindent).replace("  ", " ") + "\n"
  return outtext
  
def fortune():
  text = check_output(['fortune'] + FORTUNEOPTS).rstrip()
  #print repr(text)
  paragraphs = text.split("\n\n")
  out = "\n".join([ p if all([len(l) < MAXLEN for l in p.splitlines()]) else rewrap(p) for p in paragraphs ])
  #print repr(out)
  return out.replace("\t", "  ").splitlines()

### main program

if __name__ == '__main__':
  # the output string list
  # this list actually will contain tuples: (separation priority, output string).
  # separation priority is used in the output postprocessing below to insert optional empty lines
  # to fill the screen as near as possible to MAXLINES. In output postprocessing, first the lines
  # with priority 1 will receive an empty line before and maybe after themselves, then the lines
  # with priority 2, and so on. Priority 0 will never be expanded with empty lines.
  out = []


  ### format MPD data
  if SHOWMPD:
    d = fetch_mpd_data()
    if d is not None and "state" in d and d["state"] == 'play':
      # mpd is playing? full data output!
      try:
        # trying to interpret the mpd data
        ct = int(float(d["elapsed"]))
        t = 1
        try:
          t = int(d["time"])
          out.append((1,u"[mpd playing #%s/%s  %02d:%02d/%02d:%02d %d%%]" % ( 
                  d["song"], 
                  d["playlistlength"], 
                  ct/60,
                  ct - ((ct/60)*60),
                  t/60,
                  t - ((t/60)*60),
                  int(ct*100/t)
                )))
        except:
          # an exception from the try block above most likely means that d['time'] does not 
          # contain a simple integer, which in turn most likely means that we are streaming
          out.append((1,u"[mpd playing #%s/%s  streaming %02d:%02d]" % ( 
            d["song"], 
            d["playlistlength"], 
            ct/60,
            ct - ((ct/60)*60),
          )))

        t = ''
        if (not 'title' in d) and ('file' in d):
          t = os.path.splitext(os.path.basename(d['file']))[0]
        else:
          t = d['title']
        if not 'artist' in d and ' - ' in t:
          # no artist, but a title -> streaming or bad tagging
          # anyway, if we have ' - ' in title, we repair that by splitting up the title string
          out += [ (2,u"  %s" % u(s)) for s in reversed(t.split(' - ')) ]
        else:
          out.append((2,u"  %s" % u(t)))
          if "artist" in d: out.append((2,u"  %s" % u(d["artist"])))
          if "album" in d: out.append((2,u"  %s" % u(d["album"])))
      except Exception as e:
        # something went very wrong in the program code above
        print("ERR b/c of mpd data: " + str(e))
    elif d is not None and "state" in d:
      # mpd found, but not playing
      out.append((1,u"[mpd status: %s]" % d["state"]))
    else:
      # the mpd is a lie
      out.append((1,u"[the mpd at %s:%d is a lie]" % (MPDHOST, MPDPORT)))


  if SHOWWEATHER:
    try:
      c = fetch_weather_data()
      out.append((1,u"[openweather  %d°C  %s]" % (c['main']['temp'],c['weather'][0]['description'])))
      if 'main' in c:
        out.append((2,u"  %d°C < T < %d°C  %s  hum %d%%" %
          (c['main']['temp_min'], c['main']['temp_max'], interpret_rain(c), c['main']['humidity'])))
      if 'deg' in c['wind']:
        out.append((2,u"  wind  %sm/s %s %d°" % 
          (numf(c['wind']['speed']), carddir(c['wind']['deg']), c['wind']['deg'])))
      else:
        out.append((2,u"  wind  %sm/s" % numf(c['wind']['speed'])))
      if 'gust' in c['wind']:
        out[-1][1] += "  gust %sm/s" % numf(c['wind']['gust'])
      if 'list' in c['forecast']:
        fore = u''
        for dn,d in enumerate(c['forecast']['list'][1:]):
          fore += u'  %s %.0f/%.0f°C %s' % (wday(dn+1), d['temp']['min'], d['temp']['max'], d['weather'][0]['main'])
        out.append((2,fore))
    except: 
      #pprint(c)
      pass

  emptyline = (0,u'')
  if SHOWFORTUNE:
    try:
      out.append(emptyline)
      for l in fortune():
        out.append((0, l ))
    except Exception as e:
      out.append((1, u"Sorry, no fortune %s" % e.message))

  ### output postprocessing and system info
  
  if len(out) < MAXLINES - int(SHOWCPUTIME) - int(SHOWTIME) - int(SHOWMEM):
    # if we don't fill the screen, we add another empty line in front of the system stats
    out.append(emptyline)
    
  # append time, date, cpu load, load average
  if SHOWCPUTIME:
    out.append((0,u"[%02d:%02d %02d.%02d.%02d  cpu %.1f%%  load %s]" % 
      (time.localtime().tm_hour, time.localtime().tm_min, time.localtime().tm_mday, time.localtime().tm_mon, time.localtime().tm_year % 100, cpuload(), load())))

  # append time, date
  if SHOWTIME:
    out.append((0,u"[%02d:%02d %02d.%02d.%04d]" % 
      (time.localtime().tm_hour, time.localtime().tm_min, time.localtime().tm_mday, time.localtime().tm_mon, time.localtime().tm_year)))

  # append memory information
  if SHOWMEM:
    try:
      mi = meminfo()
      out.append((0,u"[mem %s  free %s  cache %s]" % (mi['MemTotal'], mi['MemFree'], mi['Cached']) ))
    except: pass
    
  # insert empty lines according to "separation priority"

  highestpriority = max([ p for p,s in out])
  # we do a loop for each existing priority, once with insertafter disabled, once with insertafter enabled
  for prio,insertafter in [ (p,b) for p in xrange(1, highestpriority+1) for b in (False, True) ]:
    # we create a new list to take the elements ("new out")
    nout = []
    for e in out:
      # in the following blocks, we always maintain the condition that no two empty lines may follow each other
      if e[0] == prio:
        # if the current list element has the separation priority we're currently checking,
        # we add a new empty line to the new list
        if len(nout) > 0 and nout[-1] is not emptyline:
          nout.append(emptyline)
        # then we add the element itself
        nout.append(e)
        # on second run with the same prio, insertafter is True, so we append an empty line afterwards
        if insertafter: 
          nout.append(emptyline)
      else:
        # if the current element has not the priority we're checking, it's just added to the new list
        # after checking that it's not an empty line following another empty line
        if not ( e is emptyline and len(nout) > 0 and nout[-1] is emptyline ):
          nout.append(e)
    if len(nout) < MAXLINES:
      # okay, did we exceed the limit? if not, we set 'out' to our new list and let the process repeat itself
      out = nout
    else:
      # else we break out of the for loop and let the garbage collector pick up the new list that got too long
      break
  
  
  ### output printing

  # print all output lines in latin-1 encoding, because xscreensaver is not UTF8-aware   m(
  for p,l in out:
    print( l[0:MAXLEN].encode("latin-1", 'ignore') )

  # print separator line
  print(u"_" * MAXLEN)

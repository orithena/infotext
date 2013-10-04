#!/usr/bin/python
# -*- coding: utf-8 -*-

""" infotext.py v0.1

Simply prints data and stats from various sources. Most useful as input
program to xscreensavers that simply takes some text and displays it.

Currently implemented:
  * MPD playing status
  * OpenWeatherMap weather data and forecast
  * System stats: Local time, date, cpuload, load average, memory info

Written specifically for RaspberryPi, but useable on other systems too.

Usage: Edit the configuration variables below to suit your needs. 
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

import mpd
import pickle
import time
from json import load as jsonload
from urllib2 import urlopen


### configuration variables

MAXLINES = 16
MAXLEN = 40
MPDHOST = 'localhost'
MPDPORT = 6600
WEATHERCITY = 'dortmund'
WEATHERAPPID = ''
WEATHERDATAURL = 'http://api.openweathermap.org/data/2.5/weather?q=%s&units=metric&APPID=%s'
WEATHERFORECASTURL = 'http://api.openweathermap.org/data/2.5/forecast/daily?q=%s&units=metric&cnt=3&APPID=%s'
SAVEDIR = '/run/shm'


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


### main program

if __name__ == '__main__':
  # the output string list
  out = []


  ### format MPD data

  d = fetch_mpd_data()
  if d is not None and "state" in d and d["state"] == 'play':
    # mpd is playing? full data output!
    try:
      # trying to interpret the mpd data
      ct = int(float(d["elapsed"]))
      t = 1
      try:
        t = int(d["time"])
        out.append(u"[mpd playing #%s/%s  %02d:%02d/%02d:%02d %d%%]" % ( 
                d["song"], 
                d["playlistlength"], 
                ct/60,
                ct - ((ct/60)*60),
                t/60,
                t - ((t/60)*60),
                int(ct*100/t)
              ))
      except:
        # an exception from the try block above most likely means that d['time'] does not 
        # contain a simple integer, which in turn most likely means that we are streaming
        out.append(u"[mpd playing #%s/%s  streaming %02d:%02d]" % ( 
          d["song"], 
          d["playlistlength"], 
          ct/60,
          ct - ((ct/60)*60),
        ))

      if 'title' in d and not 'artist' in d and ' - ' in d['title']:
        # no artist, but a title -> streaming or bad tagging
        # anyway, if we have ' - ' in title, we repair that by splitting up the title string
        out += [ u"  %s" % u(s) for s in reversed(d['title'].split(' - ')) ]
      else:
        if "title" in d: out.append(u"  %s" % u(d["title"]))
        if "artist" in d: out.append(u"  %s" % u(d["artist"]))
        if "album" in d: out.append(u"  %s" % u(d["album"]))
    except Exception as e:
      # something went very wrong in the program code above
      print("ERR while interpreting mpd data: " + e.message)
  elif d is not None and "state" in d:
    # mpd found, but not playing
    out.append(u"[mpd status: %s]" % d["state"])
  else:
    # the mpd is a lie
    out.append(u"[the mpd at %s:%d is a lie]" % (MPDHOST, MPDPORT))


  ### format weather data

  c = fetch_weather_data()
  out.append(u"[openweather  %d°C  %s]" % (c['main']['temp'],c['weather'][0]['description']))
  out.append(u"  %d°C < T < %d°C  rain %.0fmm  hum %d%%" %
    (c['main']['temp_min'], c['main']['temp_max'], c['rain']['3h'] , c['main']['humidity']))
  out.append(u"  wind  %sm/s %s %d°" % 
    (numf(c['wind']['speed']), carddir(c['wind']['deg']), c['wind']['deg']))
  if 'gust' in c['wind']:
    out[-1] += "  gust %sm/s" % numf(c['wind']['gust'])
  fore = u''
  for dn,d in enumerate(c['forecast']['list'][1:]):
    fore += u'  %s %.0f/%.0f°C %s' % (wday(dn+1), d['temp']['min'], d['temp']['max'], d['weather'][0]['main'])
  out.append(fore);


  ### output postprocessing
  
  if len(out) < (MAXLINES - 3) / 2:
    # if the text only fills half of the screen, we add some empty lines
    out = [ i for s in [ (a,b) for a,b in zip(out, [ u"" for j in xrange(len(out)) ]) ] for i in s ]

  if len(out) < MAXLINES - 3:
    # if we still don't fill the screen, we add another empty line in front of the system stats
    out.append(u"")


  ### output printing

  # print all output lines in latin-1 encoding, because xscreensaver is not UTF8-aware   m(
  for l in out:
    print( l[0:MAXLEN].encode("latin-1", 'ignore') )

  # system stats are printed directly to 
  # print time, date, cpu load, load average
  print(u"[%02d:%02d %02d.%02d.%02d  cpu %.1f%%  load %s]" % 
    (time.localtime().tm_hour, time.localtime().tm_min, time.localtime().tm_mday, time.localtime().tm_mon, time.localtime().tm_year % 100, cpuload(), load()))

  # print memory information
  try:
    mi = meminfo()
    print(u"[mem %s  free %s  cache %s]" % (mi['MemTotal'], mi['MemFree'], mi['Cached']) )
  except: pass

  # print separator line
  print(u"_" * MAXLEN)

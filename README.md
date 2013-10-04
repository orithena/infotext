infotext.py
===========

Simply prints data and stats from various sources. Most useful as input
program to xscreensavers that simply takes some text and displays it.

Currently implemented:
  * MPD playing status
  * OpenWeatherMap weather data and forecast
  * System stats: Local time, date, cpuload, load average, memory info

Written specifically for RaspberryPi, but useable on other systems too.


Usage: 
------

Edit the configuration variables below to suit your needs. 

You may want to apply for an app key (APPID) at http://openweathermap.org.

Then configure xscreensaver to use any text-displaying screensaver
(e.g. Phosphor, Apple2, StarWars, ...). Then, in the xscreensavers
configuration dialog's advanced tab, configure this program as text source.


Raspbian package dependencies:
------------------------------

python python-mpd xscreensaver xscreensaver-data xscreensaver-data-extra


Optional GL screensavers (slow on a raspi!):
--------------------------------------------

xscreensaver-gl xscreensaver-gl-extra libgl1-mesa-swx11


Example output:
---------------

[mpd playing #75/102  00:05/04:03 2%]
  rock'n'roll hall of fame
  pornophonique
  8-bit lagerfeuer
[openweather  12°C  broken clouds]
  11°C < T < 15°C  rain 0mm  hum 54%
  wind  6.3m/s SSE 164°
  sat 14/21°C Rain  sun 14/18°C Clouds

[03:54 04.10.13  cpu 71.5%  load 1.06]
[mem 448776  free 10944  cache 302504]


Photos of the screensaver in action:
------------------------------------

  * StarWars: http://pic.twitter.com/QrB1CSWRoc
  * Phosphor: http://pic.twitter.com/m5BqTuy69B


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

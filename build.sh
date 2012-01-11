#!/bin/bash
fakeroot dpkg-deb --build dynr-web dynr-web_`grep Version dynr-web/DEBIAN/control |sed -e 's/.* //'`_`grep Architecture dynr-web/DEBIAN/control |sed -e 's/.* //'`.deb

#!/usr/bin/env python

from django.conf.urls.defaults import *
import gatewayconf
import gatewayadmin


urlpatterns = patterns('',
    # Static and media files
    (r'^ecmascript/(?P<path>.*)$',  'django.views.static.serve', {'document_root': '/usr/share/pyshared/dynr-web/ecmascript'}),
    (r'^images/(?P<path>.*)$',  'django.views.static.serve', {'document_root': '/usr/share/pyshared/dynr-web/images'}),
    (r'^(favicon.ico)$', 'django.views.static.serve', {'document_root': '/usr/share/pyshared/dynr-web/images'}),
    (r'^$', gatewayconf.configlist),
    (r'^status\?.*$', gatewayadmin.getstatus),
    (r'^update\?.*$', gatewayadmin.setgateway),
)

#!/usr/bin/env python

from django.conf.urls.defaults import *
import gatewayconf_view
import gatewayadmin_view


urlpatterns = patterns('',
    # Static and media files
    (r'^ecmascript/(?P<path>.*)$',  'django.views.static.serve', {'document_root': '/usr/share/pyshared/dynr-web/ecmascript'}),
    (r'^images/(?P<path>.*)$',  'django.views.static.serve', {'document_root': '/usr/share/pyshared/dynr-web/images'}),
    (r'^(favicon.ico)$', 'django.views.static.serve', {'document_root': '/usr/share/pyshared/dynr-web/images'}),
    (r'^$', gatewayconf_view.configlist),
    (r'^status\?.*$', gatewayadmin_view.getstatus),
    (r'^update\?.*$', gatewayadmin_view.setgateway),
)

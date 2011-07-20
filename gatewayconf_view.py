from django.shortcuts import render_to_response
import dynrconfig

def configlist(request):
    gateway_lists = dynrconfig.getGwList() 
    return render_to_response('index.html', {'gateway_list': gateway_list})


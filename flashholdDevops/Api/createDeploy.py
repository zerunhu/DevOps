# coding=utf-8
from django.contrib.auth.models import User, Group
from app.models import *
from django.http import JsonResponse, HttpResponse
from helper import helper
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
from Api.k8sApi import K8sApi
from Api.monitorApi import MonitorApi
from Api.gitlabApi import Api
import datetime
import re
import  sys

import harborApi
import os
import time


def CreateDeploy(request):
    apps = request.POST['apps']
    return JsonResponse(apps, safe=False)
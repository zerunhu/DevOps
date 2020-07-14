#coding=utf-8
import os
import argparse
import sys

if __name__=="__main__":
    parse=argparse.ArgumentParser(prog='value program')
    parse.add_argument('--name',type=str,help='specify chart name',required="true")
    parse.add_argument('--version',type=str,help='specify chart version',default="0.0.1")
    parse.add_argument('--appVersion',type=str,help='specify app version',default="0.0.1")
    parse.add_argument('--repository',type=str,help='specify repository',required="true")
    parse.add_argument('--tag',type=str,help='specify tag',required="true")
    parse.add_argument('--ingress',type=str,default='true',help='specify ingress flag')
    parse.add_argument('--domain',type=str,default='k8s.flashhold.com',help='specify domain')
    parse.add_argument('--containerPort',type=str,default='80',help='specify container port')
    parse.add_argument('--company',type=str,default='company',help='specify company')
    parse.add_argument('--project',type=str,default='project',help='specify project')
    args=parse.parse_args()
    #set chart name
    f = open("Chart.template.yaml","r")
    w = open("Chart.yaml","w")
    text = f.read()
    text = text.replace("{{chart-name}}",args.name). \
            replace("{{chart-version}}",args.version). \
            replace("{{app-version}}",args.appVersion)
    f.close()
    w.write(text)
    w.close()
    #set value 
    f = open("values.template.yaml","r")
    w = open("values.yaml","w")
    text = f.read()
    text = text.replace("{{repository}}",args.repository). \
            replace("{{tag}}",args.tag). \
            replace("{{ingress}}",args.ingress). \
            replace("{{company}}",args.company). \
            replace("{{project}}",args.project)

    containerPorts = args.containerPort.split(",")
    for i,port in enumerate(containerPorts):
        i = i+1
        text = text.replace("{{port%s}}"%i,port.strip())

    f.close()
    w.write(text)
    w.close()


# -*- coding:utf-8 -*-
import argparse
import smtplib, sys
from email.MIMEText import MIMEText

def sendmail(usr_to, subject, msg, subtype='html'):
    usr_from = 'frylion@163.com'
    msg = MIMEText(msg, subtype, _charset='utf-8')
    msg['Subject'] = subject
    msg['To'] = usr_to
    msg['From'] = usr_from
    try:
        server = smtplib.SMTP()
        #server.connect('smtp.flashhold.com', 587)
        server.connect('smtp.163.com', 25)
        # ONLY for debug
        server.set_debuglevel(1)
         #if exchange use STARTTLS auth, you need to uncomment next line
        server.starttls()
        server.login('frylion@163.com','Woshinibin')
        server.sendmail(usr_from, usr_to, msg.as_string())
        server.close()
        return True
    except:
        return False

if __name__  == "__main__":
    parse=argparse.ArgumentParser(prog='sendmail program')
    parse.add_argument('--user',type=str,help='user',required="true")
    parse.add_argument('--mail_to',type=str,help='mail_to',required="true")
    parse.add_argument('--project',type=str,help='specify project')
    parse.add_argument('--app',type=str,help='specify app',required="true")
    parse.add_argument('--branch',type=str,help='specify branch',required="true")
    parse.add_argument('--port',type=str,help='specify port')
    parse.add_argument('--domain',type=str,help='specify domain',required="true")
    args=parse.parse_args()
    f = open('scripts/mail_msg.txt','r')
    txt = f.read().replace("{{user}}",args.user). \
          replace("{{project}}",args.project). \
          replace("{{app}}",args.app). \
          replace("{{branch}}",args.branch). \
          replace("{{port}}",args.port). \
          replace("{{domain}}",args.domain)
    f.close()
    print sendmail(args.mail_to,'构建通知',txt)
    sys.exit(0)

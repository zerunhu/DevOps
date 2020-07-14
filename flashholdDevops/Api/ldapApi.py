#-*-coding = utf-8 -*-
import sys
sys.path.append("/opt/flashhold-devops/flashholdDevops")
import random
import ldap
import ldap.modlist as modlist
import os
import logging
from django.conf import settings

#logger = logging.get#logger("")


class Uldap(object):

    def __init__(self):
        # ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, "/etc/openldap/cacerts/cacert.pem")
        try:
            l = ldap.initialize(settings.LDAP_URL)
            l.set_option(ldap.OPT_TIMEOUT, 10.0)
            l.set_option(ldap.OPT_NETWORK_TIMEOUT, 10.0)
            l.simple_bind_s("cn=admin,dc=flashhold,dc=com","M2Y3Y2JjNWI2NjUxY2ZlM2JmOWVlODQ1")
            self.conn = l
        #except ldap.TIMEOUT,ldap.SERVER_DOWN:
        except Exception,e:
            #logger.error("ldap timeout %s"%settings.LDAP_URL)
            try:
                l = ldap.initialize(settings.LDAP_URL)
                l.set_option(ldap.OPT_TIMEOUT, 10.0)
                l.set_option(ldap.OPT_NETWORK_TIMEOUT, 10.0)
                l.simple_bind_s("cn=admin,dc=flashhold,dc=com","M2Y3Y2JjNWI2NjUxY2ZlM2JmOWVlODQ1")
                self.conn = l
            except Exception,e:
                #logger.error(str(e))
                del self

    def create_ldapuser(self,username,password):
        username,password = str(username),str(password)
        dn = "cn=%s,ou=People,dc=flashhold,dc=com"%(username)
        attrs = {}
        attrs['objectclass'] = ['top', 'account', 'posixAccount', 'shadowAccount']
        attrs['cn'] = username
        attrs['uid'] = username

        # uid = self.get_user_uid(username)
        # if uid:
        #     attrs['uidNumber'] = str(uid)
        # else:
        attrs['uidNumber'] = str(self.get_unique_uidNumber())

        attrs['gidNumber'] = '55555'
        attrs['homeDirectory'] = "/home/users/%s"%username
        attrs['loginShell'] = '/bin/bash'
        attrs['description'] = 'system create user automatically'
        attrs['userPassword'] = password
        attrs['shadowLastChange'] = '0'
        attrs['shadowMax'] = '99999'
        attrs['shadowWarning'] = '99999'

        try:
            ldif = modlist.addModlist(attrs)
            self.conn.add_s(dn,ldif)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    def create_ldapgroup(self,group_name):
        group_name = str(group_name)
        group_name = group_name.encode("utf8")
        group_name = str(group_name)
        dn = "cn=%s,ou=Group,dc=flashhold,dc=com"%(group_name)
        attrs = {}
        attrs['objectclass'] = ['top', 'posixGroup']
        attrs['cn'] = group_name
        attrs['gidNumber'] = str(self.get_unique_gidNumber())
        attrs['description'] = 'system create group %s automatically'%(group_name)
        try:
            ldif = modlist.addModlist(attrs)
            self.conn.add_s(dn,ldif)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    def create_ldapgroup2(self, group_name):
        group_name = str(group_name)
        group_name = group_name.encode("utf8")
        group_name = str(group_name)
        dn = "cn=%s,ou=Group2,dc=flashhold,dc=com" % (group_name)
        attrs = {}
        attrs['objectclass'] = ['top', 'groupOfNames']
        attrs['cn'] = group_name
        attrs['member'] = ['']
        try:
            ldif = modlist.addModlist(attrs)
            self.conn.add_s(dn, ldif)
            return True, ""
        except Exception, e:
            # logger.error(str(e))
            return False, str(e)

    def delete_group_member(self,group_name,memberuids):
        group_name = group_name.encode("utf8")
        group_name,memberuids = str(group_name),str(memberuids)
        dn = "cn=%s,ou=Group,dc=flashhold,dc=com"%(group_name)
        memberuids = memberuids.split(",")
        mod_attrs = []
        for uid in memberuids:
            mod_attrs.append((ldap.MOD_DELETE, 'memberUid',uid))
        try:
            self.conn.modify_s(dn, mod_attrs)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    #arg members seperated by ||
    def delete_group2_member(self,group_name,members):
        group_name = group_name.encode("utf8")
        group_name,members = str(group_name),str(members)
        dn = "cn=%s,ou=Group2,dc=flashhold,dc=com"%(group_name)
        members = members.split("||")
        mod_attrs = []
        for member in members:
            mod_attrs.append((ldap.MOD_DELETE, 'member',member))
        try:
            self.conn.modify_s(dn, mod_attrs)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    # def disable_ldapuser(self,user_name):
    #     user_name = str(user_name)
    #     dn = "cn=%s,ou=People,dc=flashhold,dc=com"%(user_name)
    #     mod_attrs = (
    #                     # (ldap.MOD_DELETE, 'userAccountControl',512),
    #                     (ldap.MOD_ADD,'userAccountControl',str(514)),
    #                 )
    #     try:
    #         self.conn.modify_s(dn, mod_attrs)
    #         print "modify success"
    #         return True,""
    #     except Exception,e:
    #         print str(e)
    #         # #logger.error(str(e))
    #         return False,str(e)

    def delete_group_all_member(self,group_name):
        group_name = group_name.encode("utf8")
        group_name = str(group_name)
        dn = "cn=%s,ou=Group,dc=flashhold,dc=com"%(group_name)
        mod_attrs = []
        try:
            #memberUid attr not exist ,return
            rsn = self.conn.search_s(dn,ldap.SCOPE_BASE, '(objectClass=*)',["memberUid"])
            if not rsn[0][1]: return True,""
            mod_attrs.append((ldap.MOD_DELETE, 'memberUid',None))
            self.conn.modify_s(dn, mod_attrs)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    def delete_group2_all_member(self,group_name):
        group_name = group_name.encode("utf8")
        group_name = str(group_name)
        dn = "cn=%s,ou=Group2,dc=flashhold,dc=com"%(group_name)
        mod_attrs = []
        try:
            #memberUid attr not exist ,return
            rsn = self.conn.search_s(dn,ldap.SCOPE_BASE, '(objectClass=*)',["member"])
            if not rsn[0][1]: return True,""
            mod_attrs.append((ldap.MOD_DELETE, 'member',None))
            mod_attrs.append((ldap.MOD_ADD, 'member', ''))
            self.conn.modify_s(dn, mod_attrs)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    def search_user(self,user_name):
        dn ="ou=People,dc=flashhold,dc=com"
        searchScope = ldap.SCOPE_SUBTREE
        ## retrieve all attributes - again adjust to your needs - see documentation for more options
        retrieveAttributes = None
        searchFilter = "cn=%s"%user_name

        try:
            ldap_result_id = self.conn.search(dn, searchScope, searchFilter, retrieveAttributes)
            result_set = []
            while 1:
                result_type, result_data = self.conn.result(ldap_result_id, 0)
                if (result_data == []):
                    break
                else:
                    ## here you don't have to append to a list
                    ## you could do whatever you want with the individual entry
                    ## The appending to list is just for illustration.
                    if result_type == ldap.RES_SEARCH_ENTRY:
                        result_set.append(result_data)

            if result_set:
                return True,""
            else:
                return False,"not found"
        except ldap.LDAPError, e:
            return False,str(e)

    #user delete ,all group including user must delete user
    def delete_group_memberuid(self,memberuid):
        memberuid = str(memberuid)
        dn = "ou=Group,dc=flashhold,dc=com"
        rsn = self.conn.search_s(dn,ldap.SCOPE_SUBTREE, '(memberUid=%s)'%memberuid,['memberUid'])
        for item in rsn:
            mod_attrs = []
            try:
                dn = item[0]
                mod_attrs.append((ldap.MOD_DELETE, 'memberUid',memberuid))
                self.conn.modify_s(dn, mod_attrs)
            except Exception,e:

                #logger.error(str(e))
                pass
        return True,""

    def delete_group2_memberuid(self,member):
        member = str(member)
        dn = "ou=Group2,dc=flashhold,dc=com"
        member = "%s,ou=People,dc=flashhold,dc=com"%(member,)
        rsn = self.conn.search_s(dn,ldap.SCOPE_SUBTREE, '(member=%s)'%member,['member'])
        for item in rsn:
            mod_attrs = []
            try:
                dn = item[0]
                mod_attrs.append((ldap.MOD_DELETE, 'member',member))
                self.conn.modify_s(dn, mod_attrs)
            except Exception,e:

                #logger.error(str(e))
                pass
        return True,""
            
        

    def add_group_member(self,group_name,memberuids):
        group_name = group_name.encode("utf8")
        group_name,memberuids = str(group_name),str(memberuids)
        dn = "cn=%s,ou=Group,dc=flashhold,dc=com"%(group_name)
        memberuids = memberuids.split(",")
        mod_attrs = []
        for uid in memberuids:
            mod_attrs.append((ldap.MOD_ADD, 'memberUid',uid))
        try:
            self.conn.modify_s(dn, mod_attrs)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    def add_group2_member(self,group_name,members):
        group_name = group_name.encode("utf8")
        group_name,members = str(group_name),str(members)
        dn = "cn=%s,ou=Group2,dc=flashhold,dc=com"%(group_name)
        members = members.split(",")
        members = ["cn=%s,ou=People,dc=flashhold,dc=com"%member for member in members]
        mod_attrs = []
        for member in members:
            mod_attrs.append((ldap.MOD_ADD, 'member',member))
        try:
            self.conn.modify_s(dn, mod_attrs)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)


    def delete_user(self,user_name):
        user_name = str(user_name)
        dn = "cn=%s,ou=People,dc=flashhold,dc=com"%(user_name)
        try:
            self.conn.delete_s(dn)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    def delete_group(self,group_name):
        group_name = group_name.encode("utf8")
        group_name = str(group_name)
        dn = "cn=%s,ou=Group,dc=flashhold,dc=com"%(group_name)
        try:
            self.conn.delete_s(dn)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    def delete_group2(self,group_name):
        group_name = group_name.encode("utf8")
        group_name = str(group_name)
        dn = "cn=%s,ou=Group2,dc=flashhold,dc=com"%(group_name)
        try:
            self.conn.delete_s(dn)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    def get_unique_uidNumber(self):
        uidNumbers = []
        baseDN = "ou=People,dc=flashhold,dc=com"
        searchScope = ldap.SCOPE_SUBTREE
        retrieveAttributes = ["uidNumber"]
        searchFilter = "objectClass=posixAccount"
        try:
            ldap_results = self.conn.search_s(baseDN, searchScope, searchFilter, retrieveAttributes)
            for item in ldap_results:
                uidNumbers.append(item[1]["uidNumber"][0])
        except Exception,e:
            #logger.error(str(e))
            return False
        while True:
            uidNumber = random.choice(range(500, 100000))
            if uidNumber not in uidNumbers:
                break
        return uidNumber

    def get_unique_gidNumber(self):
        gidNumbers = []
        baseDN = "ou=Group,dc=flashhold,dc=com"
        searchScope = ldap.SCOPE_SUBTREE
        retrieveAttributes = ["gidNumber"]
        searchFilter = "objectClass=posixGroup"
        try:
            ldap_results = self.conn.search_s(baseDN, searchScope, searchFilter, retrieveAttributes)
            for item in ldap_results:
                gidNumbers.append(item[1]["gidNumber"][0])
        except Exception,e:
            #logger.error(str(e))
            return False
        while True:
            gidNumber = random.choice(range(1001, 100000))
            if gidNumber not in gidNumbers:
                break
        return gidNumber

    def reset_password(self,user,password,ori_password=None):
        user,password = str(user),str(password)
        dn = "cn=%s,ou=People,dc=flashhold,dc=com" %user
        try:
            if ori_password:
                self.conn.passwd_s(dn,str(ori_password),password)
            else:
                self.conn.passwd_s(dn,None,password)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    # def keep_user_uid(self,user_name):
    #     dn = "ou=People,dc=flashhold,dc=com"
    #     rsn = self.conn.search_s(dn,ldap.SCOPE_SUBTREE, '(cn=%s)'%user_name,["uidNumber"])
    #     if not rsn:return False
    #     path = os.path.join(settings.BASE_STORAGE_DIR,"%s.uid"%user_name)
    #     if os.path.exists(path):
    #         os.remove(path)
    #     with open(path,"w") as f:
    #         f.write("%s\n"%(rsn[0][1]["uidNumber"][0]))
    #     return True
    #
    # def get_user_uid(self,user_name):
    #     path = os.path.join(app_config.UID_KEEP_DIR,"%s.uid"%user_name)
    #     if not os.path.exists(path):
    #         return None
    #     with open(path,"r") as f:
    #         uid = f.readline().strip()
    #     return uid

    #user prefix % represent sudo_group
    def create_sudo_rule(self,User,Host=[],Command=[],option="!authenticate",runAsUser="root"):
        User = str(User.encode("utf8"))
        runAsUser = str(runAsUser.encode("utf8"))
        # Host = str(Host.encode("utf8"))
        # Command = str(Command.encode("utf8"))
        #
        # Command = Command.split(",")
        # Host = Host.split(",")

        commands = self.search_sudo_command_byuser(User)
        hosts = self.search_sudo_host_byuser(User)
        if not (commands and hosts):
            dn = "cn=%s,ou=Sudoers,dc=flashhold,dc=com"%(User)
            print "dn:",dn
            attrs = {}
            attrs['objectclass'] = ['top', 'sudoRole']
            attrs['sudoCommand'] = Command
            attrs['sudoHost'] = Host
            attrs['sudoOption'] = option
            attrs['sudoRunAsUser'] = runAsUser
            attrs['sudoUser'] = User
            try:
                ldif = modlist.addModlist(attrs)
                self.conn.add_s(dn,ldif)
                return True,""
            except Exception,e:
                #logger.error(str(e))
                pass
            return False,str(e)
        else:
            rsn1,rsn2,msg1,msg2 = False,False,"",""
            if Command:
                rsn1,msg1 = self.add_sudo_command_byuser(User,Command)
            if Host:
                rsn2,msg2 = self.add_sudo_host_byuser(User,Host)
            return rsn1 and rsn2,msg1+msg2


    def delete_sudo_rule_byuser(self,user_name):
        user_name = str(user_name)
        dn = "cn=%s,ou=Sudoers,dc=flashhold,dc=com"%(user_name)
        try:
            self.conn.delete_s(dn)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    def add_sudo_host_byuser(self,user_name,hosts=[]):
        mod_attrs = []
        user_name = user_name.encode("utf8")
        user_name = str(user_name)
        dn = "cn=%s,ou=Sudoers,dc=flashhold,dc=com"%(user_name)
        current_hosts = self.search_sudo_host_byuser(user_name)
        for host in hosts:
            if host not in current_hosts:
                mod_attrs.append((ldap.MOD_ADD, 'sudoHost',host))
        try:
            self.conn.modify_s(dn, mod_attrs)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    def add_sudo_command_byuser(self,user_name,commands=[]):
        mod_attrs = []
        user_name = user_name.encode("utf8")
        user_name = str(user_name)
        dn = "cn=%s,ou=Sudoers,dc=flashhold,dc=com"%(user_name)
        current_commands = self.search_sudo_command_byuser(user_name)
        for command in commands:
            if command not in current_commands:
                mod_attrs.append((ldap.MOD_ADD, 'sudoCommand',command))
        try:
            self.conn.modify_s(dn, mod_attrs)
            return True,""
        except Exception,e:
            #logger.error(str(e))
            return False,str(e)

    def del_sudo_command_byuser(self,user_name,command):
        mod_attrs = []
        user_name = user_name.encode("utf8")
        user_name,command = str(user_name),str(command)
        dn = "cn=%s,ou=Sudoers,dc=flashhold,dc=com"%(user_name)
        current_commands = self.search_sudo_command_byuser(user_name)
        if command in current_commands:
            mod_attrs.append((ldap.MOD_DELETE, 'sudoCommand',command))
            try:
                self.conn.modify_s(dn, mod_attrs)
                return True,""
            except Exception,e:
                #logger.error(str(e))
                return False,str(e)
        return False,""

    def del_sudo_host_byuser(self,user_name,host):
        mod_attrs = []
        user_name = user_name.encode("utf8")
        user_name,host = str(user_name),str(host)
        dn = "cn=%s,ou=Sudoers,dc=flashhold,dc=com"%(user_name)
        hosts = self.search_sudo_host_byuser(user_name)
        if host in hosts:
            mod_attrs.append((ldap.MOD_DELETE, 'sudoHost',host))
            try:
                self.conn.modify_s(dn, mod_attrs)
                return True,""
            except Exception,e:
                #logger.error(str(e))
                return False,str(e)
        return False,""

    def search_sudo_command_byuser(self,user_name):
        commands = []
        baseDN = "cn=%s,ou=Sudoers,dc=flashhold,dc=com"%(user_name)
        searchScope = ldap.SCOPE_SUBTREE
        retrieveAttributes = ["sudoCommand"]
        #searchFilter = "(&(objectClass=sudoRole)(sudoHost=%s))"%host
        searchFilter = "objectClass=sudoRole"
        try:
            ldap_results = self.conn.search_s(baseDN, searchScope, searchFilter, retrieveAttributes)
            for item in ldap_results:
                commands = item[1]["sudoCommand"]
        except Exception,e:
            #logger.error(str(e))
            return False
        return commands

    def search_userInfo(self,user_name):
        baseDN = "cn=%s,ou=People,dc=flashhold,dc=com"%(user_name)
        searchScope = ldap.SCOPE_SUBTREE
        #searchFilter = "(&(objectClass=sudoRole)(sudoHost=%s))"%host
        searchFilter = "objectClass=posixAccount"
        try:
            ldap_results = self.conn.search_s(baseDN, searchScope, searchFilter)
            for item in ldap_results:
                tmp = {}
                tmp['cn'] = item[1]["cn"][0]
                tmp['gidNumber'] = item[1]["gidNumber"][0]
                tmp['loginShell'] = item[1]["loginShell"][0]
                tmp['uid'] = item[1]["uid"][0]
                return tmp
        except Exception,e:
            #logger.error(str(e))
            return False
        return ""

    def search_sudo_host_byuser(self,user):
        hosts = []
        ldap_results = []
        baseDN = "cn=%s,ou=Sudoers,dc=flashhold,dc=com"%(user)
        searchScope = ldap.SCOPE_SUBTREE
        retrieveAttributes = ["sudoHost"]
        #searchFilter = "(&(objectClass=sudoRole)(sudoHost=%s))"%host
        searchFilter = "objectClass=sudoRole"
        try:
            ldap_results = self.conn.search_s(baseDN, searchScope, searchFilter, retrieveAttributes)
            for item in ldap_results:
                hosts=item[1]["sudoHost"]
        except:
            pass
        return hosts

if __name__ == "__main__":
    l = Uldap()
    # l.create_ldapuser("test4","123456")
    # l.create_ldapgroup("test_group")

    #add group members
    # l.delete_group_all_member("test_group")
    # l.add_group_member("test_group","test3,test2,test4")
    #
    # l.create_ldapgroup2("qa_test")
    # l.add_group2_member("qa_test","yuyilong")
    l.search_userInfo("nibin")
    # l.delete_group2_all_member("qa")
    # print l.search_user("liyong1")
    #print l.search_sudo_command_byuser("nib")
    # l.delete_sudo_rule_byuser("%"+"sudo-test")
    #l.create_sudo_rule("yangxd","10.3.5.32,10.3.5.31,10.3.5.33","vim /etc/passwd,vim /etc/shadow")
    #l.del_sudo_command_byuser("nib","vim /etc/shadow")
    #print l.delete_group("frylion")
    #print l.add_group_member("frylion","nib,test1")
    #l.create_ldapuser("nib","123456")
    #print l.search()
    # l.disable_ldapuser('nib')
    # print l.reset_password("nib","123456","12345")
    # l.conn.unbind_s()
    del l 

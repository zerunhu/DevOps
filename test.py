# -*- coding:utf8 -*-
import base64
import time
import gitlab
import logging
logging.basicConfig(level=logging.INFO,
                    format='%(message)s',
                    filename='./gitlab.log', filemode="a")
gl=gitlab.Gitlab(url="http://git.flashhold.com:10080", private_token="cznnk5B7eyjpBXbHPY7G",per_page=1000)
for i in range(1147,1148):
    try:
        project = gl.projects.get(i)
        logging.info("----------------\nproject_id ---> {}\nproject_name ---> {}".format(project.id, project.web_url))
        branches = project.branches.list(all=True)
        logging.info("branches ---> {}".format([i.name for i in branches]))
    except Exception as e:
        logging.error("error ---> gitlab_id:{} ---> error:{}".format(i, e))
        continue
    for branch in branches:
        try:
            f = project.files.get(file_path='.gitlab-ci.yml', ref=branch.name)
            content = f.decode().decode("utf-8")
            content = content.replace("192.168.22.30", "softoutfile.flashhold.com")
            f.content = base64.b64encode(bytes(content))
            f.save(branch=branch.name, commit_message='Update .gitlab-ci.yml file',
                   encoding='base64')
            time.sleep(10)
            logging.info("success ---> gitlab_id:{} ---> gitlab_name:{} ---> branch ---> {}"
                         .format(project.id, project.web_url, branch.name))
        except Exception as e:
            logging.error("error ---> gitlab_id:{} ---> gitlab_name:{} ---> branch:{} ---> error:{}"
                          .format(project.id, project.web_url, branch.name, e))

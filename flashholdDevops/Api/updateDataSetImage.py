# -*- coding:utf8 -*-
# coding=utf-8

'''

增量修改数据集：
1.基于原来的数据集镜像
2.将新的SQL文件拷贝到镜像里，然后使用cat命令，将新的sql文件追加到原有SQL文件里
3.build镜像，tag不变，提交push到harbor

'''


import os
import docker
import datetime
import sys
from django.conf import settings

auth_config = {
    "username": "admin",
    "password": "Harbor12345"
}


dockerfiletemp = (
    "FROM harbor2.flashhold.com/library/mysql-client:old-mysql-client-image-tag\n"
    "COPY new-sql-file /sql/new-sql-file\n"
    "RUN cat  /sql/new-sql-file >> /sql/old-mysql-client-image-tag.sql\n"
    "ENTRYPOINT [\"mysql\"]\n"
)


def IncreUpdateDataSet(newSqlFilePath, oldMysqlClientImageTag):
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="新的sql路径是: {}, 旧的数据集tag是: {}".format(newSqlFilePath,
                                                                                                        oldMysqlClientImageTag))
    if not os.path.isfile(newSqlFilePath):
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="newSqlFilePath {} 不是文件".format(newSqlFilePath))
        return False

    dockerfile = "Dockerfile"

    path = os.path.split(newSqlFilePath)[0]
    fileName = os.path.split(newSqlFilePath)[1]
    tag = "harbor2.flashhold.com/library/mysql-client:" + oldMysqlClientImageTag
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="新的sql path是: {}, 文件名称是: {}, 数据集tag是:{} ".format(path, fileName,
                                                                                                        tag))
    if os.path.isfile("{}/Dockerfile".format(path)):
        os.remove("{}/Dockerfile".format(path))

    f = open("{}/Dockerfile".format(path), "w+")
    f.write(dockerfiletemp.replace("new-sql-file", fileName).replace("old-mysql-client-image-tag", oldMysqlClientImageTag))
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="读取文件的内容是: {}".format(f.read()))
    f.close()
    #dockerAddr = settings.DOCKER_SERVER
    dockerAddr = "172.31.238.13:2375"
    if dockerAddr:
        client = docker.DockerClient(base_url='tcp://{}'.format(dockerAddr), timeout=30, version='auto')
    else:
        client = docker.DockerClient(base_url='unix://var/run/docker.sock', version='auto')
    try:
        result = client.images.build(path=path, tag=tag, dockerfile=dockerfile)
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args=" build 容器结果是: {}".format(result))

        push_result = client.images.push(tag, auth_config=auth_config)
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args=" push result: {}".format(push_result))

    except Exception as e:
        print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                              fileName=os.path.basename(__file__),
                                                              func=sys._getframe(
                                                              ).f_code.co_name,
                                                              num=sys._getframe().f_lineno,
                                                              args="Exception build & push image: %s\n" % e)
        return False

    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="Successfully built image: %s" % tag)
    return True

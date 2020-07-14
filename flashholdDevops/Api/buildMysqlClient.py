import os
import docker
import datetime
import sys
from django.conf import settings

template = (
    "FROM gliderlabs/alpine\n"
    "RUN apk update && apk-install mysql-client && mkdir /sql\n"
    "COPY template.sql  /sql/template.sql\n"
    "ENTRYPOINT [\"mysql\"]\n")

auth_config = {
    "username": "admin",
    "password": "Harbor12345"
}


def build_mysqlClient(dockerAddr, sqlFilePath):
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="dockerAddr: {}, sqlFilePath: {}".format(dockerAddr,
                                                                                                        sqlFilePath))
    if not sqlFilePath:
        return False

    if not os.path.isfile(sqlFilePath):
        return False

    dockerfile = "Dockerfile"

    path = os.path.split(sqlFilePath)[0]
    fileName = os.path.split(sqlFilePath)[1]
    tag = "{}:{}".format(settings.MYSQLCLIENT_IMAGE_BASE.split(":")[0], fileName.split(".sql")[0])
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="path: {}, fileName: {}, tag:{} ".format(path, fileName,
                                                                                                        tag))
    if os.path.isfile("{}/Dockerfile".format(path)):
        os.remove("{}/Dockerfile".format(path))

    f = open("{}/Dockerfile".format(path), "w+")
    f.write(template.replace("template.sql", fileName))
    print "{time} {fileName} {num} {func} {args} ".format(time=datetime.datetime.now(),
                                                          fileName=os.path.basename(__file__),
                                                          func=sys._getframe(
                                                          ).f_code.co_name,
                                                          num=sys._getframe().f_lineno,
                                                          args="f.read(): {}".format(f.read()))
    f.close()
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
                                                              args=" build result: {}".format(result))

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

# def push_mysqlClient(dockerAddr, sqlFilePath):


# if __name__ == "__main__":
#     build_mysqlClient(dockerAddr="172.31.238.14:2375", sqlFilePath="/opt/v2.3.0-charts/shentong-20190920-simple.sql")

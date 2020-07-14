From harbor2.flashhold.com/devops-hzr/devops:base
RUN mkdir -p /usr/src/
COPY ./flashholdDevops /usr/src/flashholdDevops
workdir /usr/src/flashholdDevops
COPY gunicorn.conf ./
COPY start.sh ./
CMD bash start.sh

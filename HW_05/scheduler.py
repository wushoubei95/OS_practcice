FROM ubuntu

RUN apt-get update
RUN apt-get install -y ssh

RUN apt update
RUN apt install -y --fix-missing apt-utils sudo python3-pip ssh

RUN pip3 install --upgrade pip
RUN pip3 install jupyter

RUN useradd -ms /bin/bash hw5
RUN adduser hw5 sudo
RUN echo 'hw5:hw5' | chpasswd
RUN mkdir /var/run/sshd
USER hw5
WORKDIR /home/hw5

CMD ["/usr/local/bin/jupyter", "notebook", "--NotebookApp.token=", "--ip=0.0.0.0", "--port=8888"]

9、在一台主机上使用scheldule.py，可以完成对于jupyter notebook 的访问。
#!/usr/bin/env python2.7
from __future__ import print_function

import sys
import uuid
import time
import socket
import signal
import getpass
from threading import Thread
from os.path import abspath, join, dirname

from pymesos import MesosSchedulerDriver, Scheduler, encode_data, decode_data
from addict import Dict

TASK_CPU = 1
TASK_MEM = 32


class MinimalScheduler(Scheduler):

    def __init__(self):
        self.count = 0;

    def resourceOffers(self, driver, offers):
        filters = {'refuse_seconds': 5}
        for offer in offers:
            if self.count>4:
                break
            cpus = self.getResource(offer.resources, 'cpus')
            mem = self.getResource(offer.resources, 'mem')
            if cpus < TASK_CPU or mem < TASK_MEM:
                continue


            #设置DockerInfo与Command
            if self.count==0:
             ip = Dict();
             ip.key = 'ip'
             ip.value = '192.168.0.100'
             NetworkInfo = Dict();
             NetworkInfo.name = 'calico_net'
             DockerInfo = Dict()
             DockerInfo.image = 'docker-jupyter'
             DockerInfo.network = 'USER'
             DockerInfo.parameters = [ip]
             ContainerInfo = Dict()
             ContainerInfo.type = 'DOCKER'
             ContainerInfo.docker = DockerInfo
             ContainerInfo.network_infos = [NetworkInfo]
             CommandInfo = Dict()
             CommandInfo.shell = False
             CommandInfo.value = 'jupyter'
             CommandInfo.arguments = ['notebook', '--ip=0.0.0.0', '--NotebookApp.token=zzw', '--port=8888']
            else:
              ip = Dict()
              ip.key = 'ip'
              ip.value = '192.168.0.10' + str(self.count)
              NetworkInfo = Dict()
              NetworkInfo.name = 'calico_net'
              DockerInfo = Dict()
              DockerInfo.image = 'docker-ssh'
              DockerInfo.network = 'USER'
              DockerInfo.parameters = [ip]
              ContainerInfo = Dict()
              ContainerInfo.type = 'DOCKER'
              ContainerInfo.docker = DockerInfo
              ContainerInfo.network_infos = [NetworkInfo]
              CommandInfo = Dict()
              CommandInfo.shell = False
              CommandInfo.value = '/usr/sbin/sshd'
              CommandInfo.arguments = ['-D']
            task = Dict()
            task_id = 'task_'+str(self.count);
            task.task_id.value = task_id
            task.agent_id.value = offer.agent_id.value
            task.name = 'hw5'

            task.container = ContainerInfo;
            task.command = CommandInfo;
            task.resources = [
                dict(name='cpus', type='SCALAR', scalar={'value': TASK_CPU}),
                dict(name='mem', type='SCALAR', scalar={'value': TASK_MEM}),
            ]

            self.count = self.count +1;
            driver.launchTasks(offer.id, [task], filters)

    def getResource(self, res, name):
        for r in res:
            if r.name == name:
                return r.scalar.value
        return 0.0

    def statusUpdate(self, driver, update):
        logging.debug('Status update TID %s %s',
                      update.task_id.value,
                      update.state)



def main(master):
    framework = Dict()
    framework.user = getpass.getuser()
    framework.name = "mynginx"
    framework.hostname = socket.gethostname()

    driver = MesosSchedulerDriver(
        MinimalScheduler(),
        framework,
        master,
        use_addict=True,
    )

    def signal_handler(signal, frame):
        driver.stop()

    def run_driver_thread():
        driver.run()

    driver_thread = Thread(target=run_driver_thread, args=())
    driver_thread.start()

    print('Scheduler running, Ctrl+C to quit.')
    signal.signal(signal.SIGINT, signal_handler)

    while driver_thread.is_alive():
        time.sleep(1)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) != 2:
        print("Usage: {} <mesos_master>".format(sys.argv[0]))
        sys.exit(1)
    else:
        main(sys.argv[1])

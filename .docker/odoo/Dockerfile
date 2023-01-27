FROM ubuntu:18.04

RUN apt update; \
    DEBIAN_FRONTEND=noninteractive apt -y --no-install-recommends install \
      ca-certificates curl gnupg lsb-release python3-pip python3-dev python3-lxml libsasl2-dev libldap2-dev ssh \
      libjpeg-dev libpq-dev libssl1.0-dev build-essential python3-matplotlib nodejs-dev node-gyp npm git locales;  \
    locale-gen en_US.UTF-8; \
    mkdir -p /etc/apt/keyrings; \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg; \
    echo  \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null; \
    apt update; \
    apt -y --no-install-recommends install docker-ce; \
    useradd -m runbot;

USER runbot
RUN mkdir -p ~/instance; \
    git clone -b 11.0 --depth=1  https://github.com/Vauxoo/runbot-addons.git ~/instance/dependencies/runbot-addons; \
    git clone -b 11.0-vauxoo --depth=1 https://github.com/Vauxoo/runbot.git ~/instance/dependencies/odoo-extra; \
    git clone -b 11.0 --depth=1 https://github.com/odoo/odoo.git ~/instance/odoo; \
    git config --global user.name runbot; \
    git config --global user.email runbot@vauxoo.com; \
    mkdir ${HOME}/.ssh; \
    ssh-keyscan github.com >> ${HOME}/.ssh/known_hosts; \
    ssh-keyscan launchpad.net >> ${HOME}/.ssh/known_hosts; \
    ssh-keyscan bitbucket.org >> ${HOME}/.ssh/known_hosts; \
    ssh-keyscan gitlab.com >> ${HOME}/.ssh/known_hosts; \
    ssh-keyscan git.vauxoo.com >> ${HOME}/.ssh/known_hosts;

USER root
RUN sed -i '/lxml/d' /home/runbot/instance/odoo/requirements.txt; \
    pip3 install setuptools==57.5.0 wheel; \
    pip3 install -r /home/runbot/instance/odoo/requirements.txt; \
    pip3 install -U travis2docker simplejson; \
    npm install -g less@3.0.4 less-plugin-clean-css;

ENV LANG=en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

USER runbot
COPY ./entrypoint.sh /
COPY ./wait-for-sql /usr/local/bin/
COPY --chown=runbot:runbot ./.openerp_serverrc $HOME/

ENV ODOO_RC=$HOME/.openerp_serverrc

ENTRYPOINT ["/entrypoint.sh"]
CMD ["runbot"]

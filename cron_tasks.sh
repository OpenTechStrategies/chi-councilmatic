#! /bin/bash

cd /home/datamade/chi-councilmatic 
/home/datamade/.virtualenvs/chi-councilmatic/bin/python manage.py loaddata --fullhistory >> /tmp/chicago-loaddata.log 2>&1 
/home/datamade/.virtualenvs/chi-councilmatic/bin/python manage.py fixdata >> /tmp/chicago-loaddata.log 2>&1 
/home/datamade/.virtualenvs/chi-councilmatic/bin/python manage.py update_index --noinput

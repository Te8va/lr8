FROM python:3
RUN pip3 install flask
RUN pip3 install requests
RUN pip3 install python-dateutil
RUN pip3 install geopy
RUN pip3 install grpcio
RUN pip3 install grpcio-tools
RUN pip3 install redis
RUN pip3 install prometheus-flask-exporter
COPY . /task/
CMD [ "python3", "/task/cmd/client.py"]
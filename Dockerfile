FROM python:3-alpine3.8

RUN mkdir -p /sruput
WORKDIR /sruput

COPY sruput /sruput

ENTRYPOINT [ "python" ]
CMD [ "sruput" ]
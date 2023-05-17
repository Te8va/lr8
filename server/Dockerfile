FROM golang
COPY . /task/
WORKDIR /task/
RUN go get google.golang.org/grpc
RUN go build -o cmd/server.bin cmd/server.go
CMD [ "bash", "-c" ,"/task/cmd/server.bin"]
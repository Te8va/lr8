package main

import (
	"context"
	"fmt"
	"grpc/pkg/api"
	"log"
	"net"
	"os"

	"google.golang.org/grpc"
)

const (
	port = "9000"
	TYPE = "tcp"
)

type GRPCServer struct {
	api.AuthServer
	gusers map[string]struct{}
}

func (s *GRPCServer) CheckAuth(ctx context.Context, req *api.AuthRequest) (*api.AuthResponse, error) {
	username := req.GetUsername()
	fmt.Println(username)
	_, ok := s.gusers[username]
	if !ok {
		return &api.AuthResponse{Exists: false}, nil
	}

	return &api.AuthResponse{Exists: true}, nil
}

func (s GRPCServer) mustEmbedUnimplementedAuthServer(ctx context.Context, req *api.AuthRequest) {}

func main() {

	listener, err := net.Listen(TYPE, ":"+os.Getenv("GRPC_PORT"))

	if err != nil {
		log.Fatal("Server startup error:", err)
	}

	fmt.Println("Сервер запущен")

	s := grpc.NewServer()

	users := make(map[string]struct{})
	users["Auth"] = struct{}{}
	users["Username"] = struct{}{}
	users["Te"] = struct{}{}

	// fmt.Println(srv.users)

	api.RegisterAuthServer(s, &GRPCServer{gusers: users})

	if err := s.Serve(listener); err != nil {
		log.Fatal("Server startup error:", err)
	}
}

// pkg/store/userdetailstore_test.go

package store

import (
    "context"
    "net/http"
    "net/http/httptest"
    "testing"

    "github.com/go-chi/chi"
    "go.mongodb.org/mongo-driver/bson"
)

type MockUserDetailStore struct {
    GetUsersByIDFunc func(ctx context.Context, id string) ([]bson.M, error)
    // Add other methods as needed
}

func (m *MockUserDetailStore) GetUsersByID(ctx context.Context, id string) ([]bson.M, error) {
    return m.GetUsersByIDFunc(ctx, id)
}

// Implement other methods as needed

func TestUserDetailStore_GetUsersByID(t *testing.T) {
    mockStore := &MockUserDetailStore{
        GetUsersByIDFunc: func(ctx context.Context, id string) ([]bson.M, error) {
            return []bson.M{{"id": "123", "name": "Test User"}}, nil
        },
    }

    userService := NewUserDetailService(mockStore)

    r := chi.NewRouter()
    r.Get("/{id}", userService.GetUserByID)

    req := httptest.NewRequest("GET", "/123", nil)
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)

    if w.Code != http.StatusOK {
        t.Fatalf("expected status OK, got %v", w.Code)
    }

    // Add more assertions as needed
}


// service/userdetail_test.go

package service

import (
    "context"
    "net/http"
    "net/http/httptest"
    "testing"

    "github.com/go-chi/chi"
    "github.com/yourusername/yourproject/pkg/store"
    "go.mongodb.org/mongo-driver/bson"
)

type MockUserDetailStore struct {
    GetUsersByIDFunc func(ctx context.Context, id string) ([]bson.M, error)
    // Add other methods as needed
}

func (m *MockUserDetailStore) GetUsersByID(ctx context.Context, id string) ([]bson.M, error) {
    return m.GetUsersByIDFunc(ctx, id)
}

// Implement other methods as needed

func TestUserDetailService_GetUserByID(t *testing.T) {
    mockStore := &MockUserDetailStore{
        GetUsersByIDFunc: func(ctx context.Context, id string) ([]bson.M, error) {
            return []bson.M{{"id": "123", "name": "Test User"}}, nil
        },
    }

    userService := NewUserDetailService(mockStore)

    r := chi.NewRouter()
    r.Get("/{id}", userService.GetUserByID)

    req := httptest.NewRequest("GET", "/123", nil)
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)

    if w.Code != http.StatusOK {
        t.Fatalf("expected status OK, got %v", w.Code)
    }

    // Add more assertions as needed
}

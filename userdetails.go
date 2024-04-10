// pkg/store/mongodb_test.go

package store

import (
    "context"
    "testing"
    "go.mongodb.org/mongo-driver/bson"
)

func TestMongoDBStore_FindOne(t *testing.T) {
    mockCollection := &MockCollection{
        FindOneFunc: func(ctx context.Context, filter interface{}) SingleResult {
            return MockSingleResult{DecodeFunc: func(val interface{}) error {
                return nil // Mock the decode function to do nothing
            }}
        },
    }

    mongoStore := NewMongoStore(mockCollection)

    err := mongoStore.FindOne(context.Background(), bson.M{"id": "123"})
    if err != nil {
        t.Fatalf("expected nil error, got %v", err)
    }
}

// Add tests for FindAll, InsertOne, UpdateOne, and DeleteOne


// pkg/store/userdetailstore_test.go

package store

import (
    "context"
    "testing"
    "go.mongodb.org/mongo-driver/bson"
)

func TestUserDetailStore_GetUsersByID(t *testing.T) {
    mockMongoStore := &MockMongoStore{
        FindOneFunc: func(ctx context.Context, filter interface{}) SingleResult {
            return MockSingleResult{DecodeFunc: func(val interface{}) error {
                return nil // Mock the decode function to do nothing
            }}
        },
    }

    userDetailStore := NewUserDetailStore(mockMongoStore)

    err := userDetailStore.GetUsersByID(context.Background(), "123")
    if err != nil {
        t.Fatalf("expected nil error, got %v", err)
    }
}

// Add tests for other methods

// pkg/services/userdetail_test.go

package services

import (
    "context"
    "net/http"
    "net/http/httptest"
    "testing"
    "github.com/go-chi/chi"
    "github.com/yourusername/yourproject/pkg/store"
    "go.mongodb.org/mongo-driver/bson"
)

func TestUserDetailService_GetUserByID(t *testing.T) {
    mockUserDetailStore := &store.MockUserDetailStore{
        GetUsersByIDFunc: func(ctx context.Context, id string) error {
            return nil
        },
    }

    userService := NewUserDetailService(mockUserDetailStore)

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

// Add tests for other methods



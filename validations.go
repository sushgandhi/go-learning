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
    mockStore := &store.MockUserDetailStore{
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

// Add tests for GetUser and AddUser


// pkg/store/userdetailstore_test.go

package store

import (
    "context"
    "testing"
    "go.mongodb.org/mongo-driver/bson"
)

func TestUserDetailStore_GetUsersByID(t *testing.T) {
    mockMongoStore := &MockMongoStore{
        FindFunc: func(ctx context.Context, filter bson.M) ([]bson.M, error) {
            return []bson.M{{"id": "123", "name": "Test User"}}, nil
        },
    }

    userDetailStore := NewUserDetailStore(mockMongoStore)

    users, err := userDetailStore.GetUsersByID(context.Background(), "123")
    if err != nil {
        t.Fatalf("expected nil error, got %v", err)
    }

    expectedUsers := []bson.M{{"id": "123", "name": "Test User"}}
    if !reflect.DeepEqual(users, expectedUsers) {
        t.Fatalf("expected %v, got %v", expectedUsers, users)
    }
}

// Add tests for other methods

// pkg/store/mongostore_test.go

package store

import (
    "context"
    "go.mongodb.org/mongo-driver/bson"
    "go.mongodb.org/mongo-driver/mongo"
)

type MockMongoStore struct {
    FindFunc func(ctx context.Context, filter bson.M) ([]bson.M, error)
    // Add other methods as needed
}

func (m *MockMongoStore) Find(ctx context.Context, filter bson.M) ([]bson.M, error) {
    return m.FindFunc(ctx, filter)
}

// Implement other methods as needed
